import uuid
import json
import pytest
from awesome_stock.runtime.owner_connections import Connections,ConnectionFailure
from awesome_stock.storage import owner_market_history as h,owner_business as b
from awesome_stock.storage.owner import OwnerStore,restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_api import app,login,request

KEY='synthetic-history-test-key'
def uid():return str(uuid.uuid4())
def raw():return {'Meta Data':{'2. Symbol':'TEST'},'Time Series (Daily)':{'2026-01-02':{'1. open':'10','2. high':'12','3. low':'9','4. close':'11','5. volume':'1000'}}}
def configured(send=None):
    c=Connections(send or (lambda *a,**k:raw()));c.configure(dict(kind='data',provider='alphavantage',model='',key=KEY,enabled=True));return c

def test_fetch_preview_save_restore_and_immutability(app,tmp_path):
    calls=[]
    def send(*args,**kwargs):calls.append(args);return raw()
    c=configured(send);s=app.store;ledger_before=s.ledger();before=s.path.read_bytes();preview=c.market_history({'symbol':'TEST'})
    assert s.path.read_bytes()==before and not preview['stored']
    assert len(calls)==1 and 'outputsize=compact' in calls[0][1]
    packet=preview['packet'];assert packet['price_basis']=='raw_unadjusted' and packet['candles'][0]['close']=='11'
    body={'id':uid(),'operation_id':uid(),'token':preview['token']};saved=h.save(s,body,c)
    c.clear();assert h.save(s,body,c)==saved
    assert KEY not in s.path.read_bytes().decode('latin1')
    assert len(h.history(s)['snapshots'])==1
    with pytest.raises(Conflict):b.save(s,{'id':saved['id'],'revision':1,'operation_id':uid()},archive=True)
    backup=s.backup();target=tmp_path.resolve()/'history-restored';restore_owner(s.directory/'backups'/backup['name'],target)
    assert h.history(OwnerStore(target))==h.history(s)
    assert s.ledger()==ledger_before

@pytest.mark.parametrize('mode',['quota','symbol','missing','range','future','too_many'])
def test_bad_history_never_becomes_receipt(mode):
    data=raw();series=data['Time Series (Daily)']
    if mode=='quota':data={'Information':KEY}
    elif mode=='symbol':data['Meta Data']['2. Symbol']='OTHER'
    elif mode=='missing':del series['2026-01-02']['5. volume']
    elif mode=='range':series['2026-01-02']['2. high']='1'
    elif mode=='future':series['2999-01-01']=series.pop('2026-01-02')
    else:data['Time Series (Daily)']={str(i):{} for i in range(101)}
    c=configured(lambda *a,**k:data)
    with pytest.raises(ConnectionFailure) as e:c.market_history({'symbol':'TEST'})
    assert str(e.value)=='history_unavailable_or_quota' and not c.histories
    assert not c.status()['data']['tested']

def test_expiry_and_config_change_invalidate():
    c=configured();p=c.market_history({'symbol':'TEST'});created,packet=c.histories[p['token']];c.histories[p['token']]=(created-301,packet)
    with pytest.raises(ConnectionFailure):c.history_receipt(p['token'])
    c.last_call.clear();p=c.market_history({'symbol':'TEST'});c.configure(dict(kind='data',provider='',model='',key='',enabled=False))
    with pytest.raises(ConnectionFailure):c.history_receipt(p['token'])

def test_api_auth_csrf_and_no_implicit_write(app):
    assert request(app,'/api/v1/owner/market-history')['status']==401
    auth=login(app);app.connections.send=lambda *a,**k:raw()
    config=dict(kind='data',provider='alphavantage',model='',key=KEY,enabled=True)
    assert request(app,'/api/v1/owner/connections','POST',config,**auth)['status']==200
    assert request(app,'/api/v1/owner/market-history-fetch','POST',{'symbol':'TEST'},cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/market-history','GET',**auth)['body']['snapshots']==[]

    preview=request(app,'/api/v1/owner/market-history-fetch','POST',{'symbol':'TEST'},**auth)
    assert preview['status']==200
    body={'id':uid(),'operation_id':uid(),'token':preview['body']['token']}
    assert request(app,'/api/v1/owner/market-history','POST',body,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/market-history','POST',{**body,'candles':[]},**auth)['status']==400
    assert request(app,'/api/v1/owner/market-history','POST',body,**auth)['status']==200


def test_full_history_retains_latest_260_with_source_digest(app):
    from datetime import datetime,timezone,timedelta
    from awesome_stock.storage import owner_research_technical as technical,owner_research_reports as reports
    end=datetime.now(timezone.utc).date();series={}
    for i in range(300):
        v=100+i;series[(end-timedelta(days=299-i)).isoformat()]={'1. open':str(v),'2. high':str(v+2),'3. low':str(v-2),'4. close':str(v+1),'5. volume':'1000'}
    calls=[]
    def send(*args,**kw):calls.append(args);return {'Meta Data':{'2. Symbol':'TEST'},'Time Series (Daily)':series}
    c=configured(send);p=c.market_history({'symbol':'TEST','outputsize':'full'})
    assert 'outputsize=full' in calls[0][1]
    packet=p['packet'];assert len(packet['candles'])==260 and packet['received_points']==300
    assert packet['candles'][0]['date']==(end-timedelta(days=259)).isoformat()
    assert len(packet['received_digest'])==64
    h.save(app.store,{'id':uid(),'operation_id':uid(),'token':p['token']},c)
    result=technical.read(app.store,{'symbol':'TEST'});assert result['technical']['moving_averages']['ma250'] is not None
    context=result['assistant_context'];assert 'candles' not in context['source'] and context['source']['candle_count']==260
    assert context['source']['candles_digest']==b.digest(packet['candles']) and len(json.dumps(context))<20000
    inp={'symbol':'TEST','lenses':['momentum']};p=reports.preview(app.store,inp);fixed=p['packet']
    source={'symbols':['TEST'],'evaluated_on':fixed['evaluated_on'],'research_questions':[{'id':'momentum'}],'records':[],'price_snapshots':[],'position_context':[],'market_technical':context,'research_memory':fixed['research_memory']}
    receipt={'provider':'synthetic','model':'synthetic','generated_at':'synthetic','draft':'synthetic','synthesis':{'status':'structured'},'context':{'task':'research_synthesis','context':json.dumps(source)}}
    reports.bound_synthesis(fixed,'receipt',{'receipt':receipt})
    source['market_technical']['source']['candles_digest']='0'*64;receipt['context']['context']=json.dumps(source)
    with pytest.raises(Conflict):reports.bound_synthesis(fixed,'receipt',{'receipt':receipt})
    saved=reports.save(app.store,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']})
    assert len(saved['packet']['market_technical']['source']['candles'])==260


def test_invalid_history_mode_does_not_send():
    calls=[];c=configured(lambda *a,**k:calls.append(a))
    for mode in ['all',[],None]:
        with pytest.raises(ValueError):c.market_history({'symbol':'TEST','outputsize':mode})
    assert not calls
