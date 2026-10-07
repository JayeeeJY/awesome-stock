from io import BytesIO
import json
import uuid
import pytest
from awesome_stock.runtime.owner import application

PASSWORD='Synthetic-test-only-2026'
ORIGIN='http://127.0.0.1:4322'

def request(app,path,method='GET',body=None,cookie='',csrf='',origin=ORIGIN,host='127.0.0.1:4322',requested='awesome-owner',content_type='application/json'):
    raw=json.dumps(body).encode() if body is not None else b''
    env={'REQUEST_METHOD':method,'PATH_INFO':path,'CONTENT_LENGTH':str(len(raw)),'wsgi.input':BytesIO(raw),'HTTP_HOST':host,'HTTP_COOKIE':cookie,'HTTP_X_CSRF_TOKEN':csrf,'HTTP_X_REQUESTED_WITH':requested,'CONTENT_TYPE':content_type}
    if origin:env['HTTP_ORIGIN']=origin
    result={}
    def start(status,headers):result.update(status=int(status.split()[0]),headers=headers)
    result['body']=json.loads(b''.join(app(env,start)));return result

def login(app,password=PASSWORD,username='tester'):
    r=request(app,'/api/v1/auth/login','POST',{'username':username,'password':password})
    assert r['status']==200
    values=[v.split(';')[0] for k,v in r['headers'] if k.lower()=='set-cookie']
    assert len(values)==3 and all(v.startswith('__Host-awesome_owner_') for v in values)
    return {'cookie':'; '.join(values),'csrf':next(v.split('=',1)[1] for v in values if v.startswith('__Host-awesome_owner_csrf='))}

@pytest.fixture
def app(tmp_path):
    a=application(port=4322,data_dir=tmp_path.resolve()/'owner')
    assert request(a,'/api/v1/owner/setup','POST',{'username':'Tester','password':PASSWORD})['status']==200
    return a

def test_initialization_status_and_no_demo(tmp_path):
    a=application(port=4322,data_dir=tmp_path.resolve()/'owner')
    assert request(a,'/api/v1/owner/status')['body']=={'initialized':False,'authenticated':False,'mode':'owner_local'}
    assert request(a,'/api/v1/demo/bootstrap')['status']==404
    assert request(a,'/api/v1/owner/ledger')['status']==401
    assert request(a,'/api/v1/owner/setup','POST',{'username':'tester','password':PASSWORD},requested='')['status']==403
    assert request(a,'/api/v1/owner/setup','POST',{'username':'tester','password':PASSWORD})['status']==200
    assert request(a,'/api/v1/owner/setup','POST',{'username':'second','password':PASSWORD})['status']==409
    auth=login(a);r=request(a,'/api/v1/owner/ledger',**auth)
    assert r['body']['accounts']==[]
    assert PASSWORD not in json.dumps(r)

@pytest.mark.parametrize('change',[{'origin':'https://evil.example'},{'origin':None},{'host':'evil.example'},{'content_type':'text/plain'},{'csrf':'bad'}])
def test_mutation_csrf_and_host_protection(app,change):
    auth=login(app)
    r=request(app,'/api/v1/owner/backup','POST',{},**(auth|change))
    assert r['status']==403
    assert not (app.store.directory/'backups').exists()

def test_cookie_isolation_and_restart_reauthentication(app):
    auth=login(app)
    other=auth['cookie'].replace('awesome_owner_','awesome_')
    assert request(app,'/api/v1/owner/ledger',cookie=other)['status']==401
    assert request(app,'/api/v1/owner/status',**auth)['body']['authenticated'] is True
    restart=application(port=4322,data_dir=app.store.directory)
    assert request(restart,'/api/v1/owner/ledger',**auth)['status']==401
    assert request(restart,'/api/v1/owner/ledger',**login(restart))['status']==200

def test_refresh_rotation_and_logout(app):
    auth=login(app)
    r=request(app,'/api/v1/auth/refresh','POST',{},**auth)
    assert r['status']==200
    values=[v.split(';')[0] for k,v in r['headers'] if k.lower()=='set-cookie']
    newer={'cookie':'; '.join(values),'csrf':next(v.split('=',1)[1] for v in values if v.startswith('__Host-awesome_owner_csrf='))}
    assert request(app,'/api/v1/auth/logout','POST',{},**newer)['status']==200
    assert request(app,'/api/v1/owner/ledger',**newer)['status']==401

def test_login_throttle_cannot_bypass_with_username(app):
    responses=[request(app,'/api/v1/auth/login','POST',{'username':'tester' if i%2 else 'missing','password':'wrong'}) for i in range(5)]
    assert [r['status'] for r in responses]==[401,401,401,401,429]
    assert responses[0]['body']==responses[1]['body']
    r=request(app,'/api/v1/auth/login','POST',{'username':'new-name','password':PASSWORD})
    assert r['status']==429 and any(k=='Retry-After' for k,v in r['headers'])

def test_password_change_revokes_all_process_sessions(app):
    auth=login(app);second=application(port=4322,data_dir=app.store.directory);other=login(second)
    new='Synthetic-new-password-2026'
    assert request(app,'/api/v1/owner/password','POST',{'current_password':'wrong','new_password':new},**auth)['status']==401
    assert request(app,'/api/v1/owner/password','POST',{'current_password':PASSWORD,'new_password':new},**auth)['status']==200
    assert request(app,'/api/v1/owner/ledger',**auth)['status']==401
    assert request(second,'/api/v1/owner/ledger',**other)['status']==401
    assert request(app,'/api/v1/auth/login','POST',{'username':'tester','password':PASSWORD})['status']==401
    assert request(app,'/api/v1/owner/ledger',**login(app,password=new))['status']==200

def test_authenticated_ledger_api_rollback_backup_and_extra_fields(app):
    auth=login(app)
    account={'id':'account-test','operation_id':str(uuid.uuid4()),'name':'Test','currency':'USD','opening_cash':'1000'}
    assert request(app,'/api/v1/owner/accounts','POST',account|{'workspace':'spoof'},**auth)['status']==400
    assert request(app,'/api/v1/owner/accounts','POST',account,**auth)['status']==200
    trade={'id':'trade-test','operation_id':str(uuid.uuid4()),'revision':0,'account_id':'account-test','symbol':'TEST','side':'sell','quantity':'1','price':'10','fee':'0','executed_at':'2026-01-01T00:00:00Z'}
    assert request(app,'/api/v1/owner/trades','POST',trade,**auth)['status']==422
    assert request(app,'/api/v1/owner/ledger',**auth)['body']['accounts'][0]['trades']==[]
    assert request(app,'/api/v1/owner/trades','POST',trade|{'side':'buy'},**auth)['status']==200
    assert request(app,'/api/v1/owner/backup','POST',{},**auth)['status']==200
    assert request(app,'/api/v1/owner/accounts','POST',[],**auth)['status']==400
