import json
import time
import pytest
from awesome_stock.runtime.owner_connections import Connections,ConnectionFailure,transport
from test_owner_api import app,request,login

KEY='Synthetic-secret-not-real'

def configured(provider='openai',send=None):
    c=Connections(send);c.configure(dict(kind='ai',provider=provider,model='test-model',key='' if provider=='ollama' else KEY,enabled=True));return c

def preview(c):return c.preview(dict(task='explain',question='Summarize the synthetic data',context='Synthetic holding: TEST, 2 shares'))

def test_default_disabled_and_exact_preview_no_environment(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','never-read-me');calls=[];c=Connections(lambda *a,**kw:calls.append(a))
    with pytest.raises(ConnectionFailure):preview(c)
    assert not calls and c.status()['ai']['enabled'] is False
    c=configured(send=lambda *a,**kw:calls.append(a));p=preview(c)
    assert p['payload']['context']=='Synthetic holding: TEST, 2 shares' and not calls and KEY not in json.dumps(c.status())

def test_cloud_payload_receipt_no_automatic_retry_and_redaction():
    calls=[]
    def fake(*args,**kwargs):calls.append((args,kwargs));return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Draft '+KEY}]}]}
    c=configured(send=fake);p=preview(c)
    with pytest.raises(ValueError):c.generate(dict(token=p['token'],confirm=False))
    r=c.generate(dict(token=p['token'],confirm=True));assert KEY not in r['draft'] and r['stored'] is False and r['fallback'] is False
    assert c.generate(dict(token=p['token'],confirm=True))==r and len(calls)==1
    host,path,body,key=calls[0][0];assert host=='api.openai.com' and path=='/v1/responses' and body['store'] is False and body['max_output_tokens']==1800 and key==KEY
    assert 'tools' not in body and 'never-read-me' not in json.dumps(body)
    c.clear();assert c.status()['ai']['enabled'] is False

def test_local_response_and_expired_preview():
    calls=[]
    def fake(*args,**kw):calls.append((args,kw));return {'done':True,'message':{'content':'Local draft'}}
    c=configured('ollama',fake);p=preview(c);assert p['sends_to_cloud'] is False
    assert c.generate({'token':p['token'],'confirm':True})['draft']=='Local draft'
    assert calls[0][1]=={'local':True} and calls[0][0][2]['stream'] is False
    p=preview(c);created,payload,cfg=c.previews[p['token']];c.previews[p['token']]=(created-301,payload,cfg)
    with pytest.raises(ConnectionFailure):c.generate({'token':p['token'],'confirm':True})

@pytest.mark.parametrize('raw',[{}, {'status':'incomplete','output':[]},{'status':'completed','output':[]},{'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':''}]}]}])
def test_model_invalid_output_stops(raw):
    c=configured(send=lambda *a,**kw:raw);p=preview(c)
    with pytest.raises(ConnectionFailure):c.generate({'token':p['token'],'confirm':True})
    assert c.status()['ai']['tested'] is False
    with pytest.raises(ConnectionFailure):c.generate({'token':p['token'],'confirm':True})

def test_quote_date_symbol_and_currency_contract():
    calls=[]
    def fake(*args,**kw):calls.append(args);return {'Global Quote':{'01. symbol':'TEST','05. price':'20.25','07. latest trading day':'2026-01-01'}}
    c=Connections(fake);c.configure(dict(kind='data',provider='alphavantage',model='',key=KEY,enabled=True));r=c.quote({'symbol':'TEST'});assert r['price']=='20.25' and r['realtime'] is False and r['stored'] is False
    assert calls[0][0]=='www.alphavantage.co' and 'GLOBAL_QUOTE' in calls[0][1]
    c.last_call.clear()
    with pytest.raises(ConnectionFailure):c.quote({'symbol':'OTHER'})
    with pytest.raises(ValueError):c.quote({'symbol':'600000.SH'})
    c.send=lambda *a,**kw:{'Information':'quota '+KEY};c.last_call.clear()
    with pytest.raises(ConnectionFailure):c.quote({'symbol':'TEST'})

@pytest.mark.parametrize('patch',[{'provider':'evil'},{'model':'x\nAuthorization:bad'},{'key':'x\r\nHeader:bad'},{'enabled':'yes'},{'kind':'unknown'},{'key':''}])
def test_config_rejects_untrusted_destination_and_bad_values(patch):
    with pytest.raises(ValueError):Connections().configure(dict(kind='ai',provider='openai',model='test',key=KEY,enabled=True)|patch)

def test_api_never_persists_credentials_and_logout_clears(app):
    auth=login(app);before=app.store.path.read_bytes()
    config=dict(kind='ai',provider='openai',model='test',key=KEY,enabled=True)
    r=request(app,'/api/v1/owner/connections','POST',config,**auth);assert r['status']==200 and KEY not in json.dumps(r)
    assert app.store.path.read_bytes()==before
    assert KEY not in json.dumps(request(app,'/api/v1/owner/export',**auth))
    request(app,'/api/v1/auth/logout','POST',{},**auth);assert app.connections.status()['ai']['enabled'] is False

def test_api_failure_does_not_leak_provider_details(app):
    auth=login(app);app.connections=configured() # app closure intentionally retains own instance
    request(app,'/api/v1/owner/connections','POST',dict(kind='ai',provider='openai',model='test',key=KEY,enabled=True),**auth)
    # disabled quote returns only public wording
    r=request(app,'/api/v1/owner/quote-fetch','POST',{'symbol':'TEST'},**auth)
    assert r['status']==503 and KEY not in json.dumps(r)

@pytest.mark.parametrize('status,payload,ok',[(200,b'{"ok":true}',True),(302,b'{"redirect":true}',False),(401,b'{"error":"synthetic-secret"}',False),(429,b'{"error":"quota"}',False),(200,b'not json',False),(200,b'[]',False),(200,b'{'+b'x'*262145,False)])
def test_bounded_transport_real_local_http_no_redirect(monkeypatch,status,payload,ok):
    from http.server import HTTPServer,BaseHTTPRequestHandler
    import threading
    import http.client
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append((self.path,self.headers.get('Authorization'),self.rfile.read(int(self.headers.get('Content-Length','0')))))
            self.send_response(status);self.send_header('Content-Length',str(len(payload)));self.send_header('Location','https://untrusted.example');self.end_headers();self.wfile.write(payload)
        def log_message(self,*args):pass
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    original=http.client.HTTPConnection
    def local_https(host,port,timeout,context):
        assert host=='api.openai.com' and port==443 and timeout==30 and context.check_hostname
        return original('127.0.0.1',server.server_port,timeout=timeout)
    monkeypatch.setattr(http.client,'HTTPSConnection',local_https)
    try:
        if ok:assert transport('api.openai.com','/v1/responses',{'synthetic':True},KEY)=={'ok':True}
        else:
            with pytest.raises(ConnectionFailure):transport('api.openai.com','/v1/responses',{'synthetic':True},KEY)
        assert len(seen)==1 and seen[0][1]=='Bearer '+KEY
    finally:server.shutdown();thread.join();server.server_close()

def test_transport_timeout_public_failure(monkeypatch):
    import http.client
    class Timeout:
        def request(self,*a,**kw):raise TimeoutError('secret-bearing-internal-error')
        def close(self):pass
    monkeypatch.setattr(http.client,'HTTPSConnection',lambda *a,**kw:Timeout())
    with pytest.raises(ConnectionFailure) as ex:transport('api.openai.com','/v1/responses',{},KEY)
    assert KEY not in str(ex.value) and 'secret-bearing' not in str(ex.value)

@pytest.mark.parametrize('config',[
    dict(kind='ai',provider='openai',model='demo@awesome.local',key=KEY,enabled=True),
    dict(kind='ai',provider='openai',model='test-model',key='',enabled=True),
    dict(kind='ai',provider='ollama',model='test-model',key=KEY,enabled=True),
])
def test_config_errors_are_specific_and_do_not_echo_secrets(app,config):
    auth=login(app);r=request(app,'/api/v1/owner/connections','POST',config,**auth)
    assert r['status']==400 and r['body']['error']['code']=='connection_config_invalid'
    assert '成交' not in r['body']['error']['message'] and KEY not in json.dumps(r)
    assert not app.connections.status()['ai']['enabled']


def test_local_transport_fixed_container_host_and_no_arbitrary_destination(monkeypatch):
    import http.client
    calls=[]
    class Response:
        status=200
        def getheader(self,name,default=None):return default
        def read(self,*args):return b'{"done":true}'
    class Connection:
        def request(self,*args,**kwargs):pass
        def getresponse(self):return Response()
        def close(self):pass
    def connect(host,port,timeout):calls.append((host,port,timeout));return Connection()
    monkeypatch.setattr(http.client,'HTTPConnection',connect)
    assert transport('127.0.0.1','/api/chat',{},local=True,local_host='host.docker.internal')=={'done':True}
    assert calls==[('host.docker.internal',11434,30)]
    with pytest.raises(ValueError):transport('127.0.0.1','/api/chat',{},local=True,local_host='untrusted.example')
    assert len(calls)==1

def test_batch_previews_are_independent_bounded_and_expire(monkeypatch):
    calls=[]
    def fake(host,path,body,*args,**kwargs):
        calls.append(body)
        return {'done':True,'message':{'content':'Synthetic result'}}
    c=configured('ollama',fake)
    monkeypatch.setattr(c,'_rate',lambda kind:None)
    first=c.preview(dict(task='explain',question='First symbol',context='AAA only'))
    second=c.preview(dict(task='explain',question='Second symbol',context='BBB only'))
    one=c.generate({'token':first['token'],'confirm':True})
    two=c.generate({'token':second['token'],'confirm':True})
    assert one['context']['context']=='AAA only'
    assert two['context']['context']=='BBB only'
    assert len(calls)==2
    previews=[c.preview(dict(task='explain',question=str(i),context='bounded')) for i in range(11)]
    assert len(c.previews)==10
    with pytest.raises(ConnectionFailure):c.generate({'token':previews[0]['token'],'confirm':True})
    token=previews[-1]['token'];created,payload,cfg=c.previews[token]
    c.previews[token]=(created-301,payload,cfg)
    c.preview(dict(task='explain',question='Fresh',context='fresh'))
    assert token not in c.previews


def test_deepseek_exact_cloud_payload_completed_text_receipt_and_redaction():
    calls=[]
    def fake(*args,**kwargs):
        calls.append((args,kwargs))
        return {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'Draft '+KEY,'reasoning_content':'Do not expose internal reasoning'}}]}
    c=configured('deepseek',fake);p=preview(c)
    assert p['sends_to_cloud'] is True and p['provider']=='deepseek' and not calls
    result=c.generate({'token':p['token'],'confirm':True})
    assert result['draft']=='Draft [已隐藏凭据]' and 'reasoning' not in json.dumps(result)
    assert c.generate({'token':p['token'],'confirm':True})==result and len(calls)==1
    args,kwargs=calls[0];host,path,body,key=args
    assert (host,path,key)==('api.deepseek.com','/chat/completions',KEY) and kwargs=={}
    assert body['stream'] is False and body['max_tokens']==1800 and body['thinking']=={'type':'disabled'} and 'tools' not in body
    assert json.loads(body['messages'][1]['content'])==p['payload']
    assert body['messages'][0]['role']=='system' and c.status()['ai']['tested'] is True


@pytest.mark.parametrize('choice',[
    None,{}, {'finish_reason':'length','message':{'role':'assistant','content':'Truncated'}},
    {'finish_reason':'content_filter','message':{'role':'assistant','content':'Filtered'}},
    {'finish_reason':'stop','message':{'role':'tool','content':'Unexpected'}},
    {'finish_reason':'stop','message':{'role':'assistant','content':'Text','tool_calls':[{}]}},
    {'finish_reason':'stop','message':{'role':'assistant','content':'Text','function_call':{'name':'x'}}},
    {'finish_reason':'stop','message':{'role':'assistant','content':None,'reasoning_content':'Not a final answer'}},
])
def test_deepseek_invalid_or_partial_output_is_consumed_without_retry(choice):
    calls=[]
    def fake(*args,**kwargs):calls.append(args);return {'choices':[choice]}
    c=configured('deepseek',fake);p=preview(c)
    for _ in range(2):
        with pytest.raises(ConnectionFailure):c.generate({'token':p['token'],'confirm':True})
    assert len(calls)==1 and c.status()['ai']['tested'] is False


def test_deepseek_provider_change_invalidates_preview_without_secret_forwarding():
    calls=[];c=configured('deepseek',lambda *a,**kw:calls.append(a));p=preview(c)
    c.configure(dict(kind='ai',provider='openai',model='other-model',key='Different-synthetic-key',enabled=True))
    with pytest.raises(ConnectionFailure):c.generate({'token':p['token'],'confirm':True})
    assert not calls


def test_full_daily_transport_cap_is_scoped_and_bounded(monkeypatch):
    class Response:
        status=200
        def __init__(self,size):self.size=size
        def getheader(self,*a):return str(self.size)
        def read(self,n):return b'{"ok":true}'
    sizes=[300000,300000,4194305]
    class Conn:
        def __init__(self,*a,**kw):pass
        def request(self,*a,**kw):pass
        def getresponse(self):return Response(sizes.pop(0))
        def close(self):pass
    monkeypatch.setattr('http.client.HTTPSConnection',Conn)
    assert transport('www.alphavantage.co','/query?function=TIME_SERIES_DAILY&outputsize=full',None)=={'ok':True}
    with pytest.raises(ConnectionFailure):transport('api.openai.com','/v1/responses',{})
    with pytest.raises(ConnectionFailure):transport('www.alphavantage.co','/query?function=TIME_SERIES_DAILY&outputsize=full',None)


def test_quote_previous_close_optional_and_invalid_is_not_silently_dropped():
    payload={'Global Quote':{'01. symbol':'TEST','05. price':'20','07. latest trading day':'2026-01-01','08. previous close':'18'}}
    c=Connections(lambda *a,**k:payload);c.configure(dict(kind='data',provider='alphavantage',model='',key=KEY,enabled=True))
    assert c.quote({'symbol':'TEST'})['previous_close']=='18'
    for value in ['0','-1','NaN',True]:
        payload['Global Quote']['08. previous close']=value;c.last_call.clear()
        with pytest.raises(ConnectionFailure):c.quote({'symbol':'TEST'})
    del payload['Global Quote']['08. previous close'];c.last_call.clear()
    assert c.quote({'symbol':'TEST'})['previous_close'] is None


def test_connection_probe_exact_preview_confirmation_and_deepseek_non_thinking():
    calls=[]
    c=configured('deepseek',lambda *args,**kwargs:calls.append(args) or {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'连接成功。'}}]})
    for patch in ({'question':'other'}, {'context':'private holding'}):
        with pytest.raises(ValueError):c.preview(dict(question='请只回复：连接成功。',context='',task='connection_test')|patch)
    p=c.preview(dict(question='请只回复：连接成功。',context='',task='connection_test'))
    assert not calls and p['payload']==dict(question='请只回复：连接成功。',context='',task='connection_test')
    with pytest.raises(ValueError):c.generate({'token':p['token'],'confirm':False})
    assert not calls
    result=c.generate({'token':p['token'],'confirm':True})
    assert result['draft']=='连接成功。' and c.status()['ai']['tested']
    assert len(calls)==1 and calls[0][2]['thinking']=={'type':'disabled'} and calls[0][2]['max_tokens']==128
    assert 'private holding' not in json.dumps(calls[0][2])
    c.generate({'token':p['token'],'confirm':True});assert len(calls)==1

@pytest.mark.parametrize('http_status,expected',[(401,'provider_auth_failed'),(403,'provider_permission_denied'),(404,'provider_model_unavailable'),(429,'provider_rate_limited')])
def test_transport_safe_actionable_status(monkeypatch,http_status,expected):
    import http.client
    class Response:
        status=http_status
    class FakeConnection:
        def request(self,*a,**kw):pass
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(http.client,'HTTPSConnection',lambda *a,**kw:FakeConnection())
    with pytest.raises(ConnectionFailure,match=expected):transport('api.deepseek.com','/chat/completions',{},KEY)

@pytest.mark.parametrize('reason,phrase',[('provider_auth_failed','API Key'),('provider_permission_denied','模型权限'),('provider_model_unavailable','模型 ID'),('provider_rate_limited','额度或频率'),('connection_failed','检查网络'),('invalid_model_output','不完整'),('model_output_truncated','长度上限')])
def test_api_actionable_connection_errors_no_provider_body(app,reason,phrase):
    auth=login(app)
    request(app,'/api/v1/owner/connections','POST',dict(kind='ai',provider='deepseek',model='test-model',key=KEY,enabled=True),**auth)
    def fail(*args,**kwargs):raise ConnectionFailure(reason)
    app.connections.send=fail
    p=request(app,'/api/v1/owner/ai-preview','POST',dict(question='请只回复：连接成功。',context='',task='connection_test'),**auth)
    response=request(app,'/api/v1/owner/ai-generate','POST',dict(token=p['body']['token'],confirm=True),**auth)
    assert response['status']==503 and phrase in json.dumps(response,ensure_ascii=False) and KEY not in json.dumps(response)


def test_deepseek_work_uses_probe_mode_and_truncation_is_actionable_without_retry():
    calls=[]
    def fake(*args,**kwargs):
        body=args[2];calls.append(body)
        if body.get('thinking')!={'type':'disabled'}:return {'choices':[{'finish_reason':'length','message':{'role':'assistant','content':None,'reasoning_content':'Budget exhausted'}}]}
        return {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'通用概念回答'}}]}
    c=configured('deepseek',fake)
    p=c.preview(dict(task='explain',question='市盈率有什么局限？',context=''))
    result=c.generate(dict(token=p['token'],confirm=True));assert result['draft']=='通用概念回答'
    assert calls[0]['max_tokens']==1800 and calls[0]['thinking']=={'type':'disabled'}
    assert '没有材料时' in calls[0]['messages'][0]['content']
    c.last_call.clear();c.send=lambda *a,**kw:{'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'Incomplete final answer'}}]}
    p=preview(c)
    with pytest.raises(ConnectionFailure,match='model_output_truncated'):c.generate(dict(token=p['token'],confirm=True))
    with pytest.raises(ConnectionFailure):c.generate(dict(token=p['token'],confirm=True))
