from datetime import datetime, timezone
import copy
import json
import pytest
from awesome_stock.runtime.owner_public_market import fetch, instrument
from awesome_stock.runtime.owner_connections import Connections, ConnectionFailure
from test_owner_api import app,request,login

AT=datetime(2026,10,6,18,tzinfo=timezone.utc)

def packet(sy='AAPL',currency='USD'):
    return {'chart':{'error':None,'result':[{'meta':{'symbol':sy,'currency':currency,'instrumentType':'EQUITY','exchangeName':'Synthetic','currentTradingPeriod':{'regular':{'end':1791300000}}},'timestamp':[1790982000,1791241200], 'indicators':{'quote':[{'open':[10,12],'high':[12,14],'low':[9,11],'close':[11,13],'volume':[100,200]}]}}]}}

@pytest.mark.parametrize('market,sy,remote,currency',[('US','AAPL','AAPL','USD'),('CN','600104','600104.SS','CNY'),('CN','000002','000002.SZ','CNY'),('HK','0700','0700.HK','HKD'),('HK','00700','0700.HK','HKD')])
def test_public_identity_and_no_key_request(market,sy,remote,currency):
    calls=[]
    def send(*args):calls.append(args);return packet(remote,currency)
    result=fetch(send,sy,market,100,AT)
    assert result['currency']==currency and result['provider_symbol']==remote and len(result['candles'])==2
    assert calls[0][0]=='query1.finance.yahoo.com' and '/'+remote+'?' in calls[0][1] and len(calls[0])==3 and calls[0][2] is None
    assert result['realtime'] is False and result['price_basis']=='supplier_ohlcv_no_adjclose'

@pytest.mark.parametrize('patch',[{'currency':'EUR'},{'symbol':'OTHER'},{'instrumentType':'CRYPTOCURRENCY'}])
def test_wrong_identity_is_not_a_quote(patch):
    data=packet();data['chart']['result'][0]['meta'].update(patch)
    with pytest.raises(ValueError):fetch(lambda *a:data,'AAPL','US',2,AT)

@pytest.mark.parametrize('sy,market',[('00000','HK'),('evil/path','US'),('600000','US'),('200001','CN'),('AAPL','invalid')])
def test_unsupported_symbol_stops_before_network(sy,market):
    calls=[]
    with pytest.raises(ValueError):fetch(lambda *a:calls.append(a),sy,market,2,AT)
    assert calls==[]

def test_incomplete_current_day_and_missing_rows_not_synthesized():
    data=packet();row=data['chart']['result'][0];row['timestamp'][1]=int(datetime(2026,10,6,13,30,tzinfo=timezone.utc).timestamp());row['meta']['currentTradingPeriod']['regular']['end']=int(datetime(2026,10,6,20,tzinfo=timezone.utc).timestamp())
    result=fetch(lambda *a:data,'AAPL','US',100,AT)
    assert len(result['candles'])==1 and result['as_of']=='2026-10-02'
    row['indicators']['quote'][0]['volume'][0]=None
    with pytest.raises(ValueError):fetch(lambda *a:data,'AAPL','US',100,AT)

@pytest.mark.parametrize('bad',['future','duplicate','negative_volume','nan','misaligned','range'])
def test_public_malformed_bars_rejected(bad):
    data=packet();row=data['chart']['result'][0];q=row['indicators']['quote'][0]
    if bad=='future':row['timestamp'][0]=int(AT.timestamp())+60
    if bad=='duplicate':row['timestamp'][1]=row['timestamp'][0]
    if bad=='negative_volume':q['volume'][0]=-1
    if bad=='nan':q['close'][0]=float('nan')
    if bad=='misaligned':q['close'].pop()
    if bad=='range':q['high'][0]=1
    with pytest.raises(ValueError):fetch(lambda *a:data,'AAPL','US',100,AT)

def test_public_receipts_and_private_connection_separation():
    calls=[];c=Connections(lambda *a:calls.append(a) or packet());c.configure(dict(kind='data',provider='alphavantage',model='',key='Synthetic-own-key',enabled=True))
    q=c.public_market(dict(symbol='AAPL',market='US'));assert q['price']=='13.00000000' and q['previous_close']=='11.00000000' and not q['stored']
    c.last_call.clear();p=c.public_market(dict(symbol='AAPL',market='US',outputsize='full'),history=True);assert c.history_receipt(p['token'])==p['packet'] and len(calls)==2
    assert all(len(a)==3 and 'Synthetic-own-key' not in str(a) for a in calls)
    assert c.status()['data_public']['tested'] and not c.status()['data']['tested']
    c.last_call.clear();c.send=lambda *a: {'chart':{'error':{'description':'secret-bearing-provider-error'},'result':None}}
    with pytest.raises(ConnectionFailure,match='public_market_unavailable'):c.public_market(dict(symbol='AAPL',market='US'))
    assert len(calls)==2 # no alternate-provider fallback

def test_public_api_requires_auth_and_preserves_store_until_confirm(app):
    auth=login(app);before=app.store.path.read_bytes();calls=[];app.connections.send=lambda *a:calls.append(a) or packet()
    assert request(app,'/api/v1/owner/quote-fetch-public','POST',dict(symbol='AAPL',market='US'))['status']==401
    q=request(app,'/api/v1/owner/quote-fetch-public','POST',dict(symbol='AAPL',market='US'),**auth)
    assert q['status']==200 and q['body']['stored'] is False and app.store.path.read_bytes()==before and len(calls)==1


def test_public_transport_fixed_path_and_no_key():
    from awesome_stock.runtime.owner_public_market import public_transport
    from awesome_stock.runtime.owner_connections import transport
    for path in ('https://evil.example/','/v8/finance/chart/AAPL?range=1y&interval=1d&apikey=x','/v8/finance/chart/../private?range=1y&interval=1d'):
        with pytest.raises(ValueError):public_transport(path)
    with pytest.raises(ValueError):transport('query1.finance.yahoo.com','/v8/finance/chart/AAPL?range=1y&interval=1d',None,'Synthetic-never-forward')

def test_public_transport_no_redirect_and_response_bounds(monkeypatch):
    import urllib.request
    from urllib.error import HTTPError
    from awesome_stock.runtime.owner_public_market import public_transport
    seen=[]
    class Response:
        status=200
        headers={}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,size):return b'x'*size
    class Opener:
        def open(self,request,timeout):
            seen.append((request.full_url,request.header_items(),timeout));return Response()
    def opener(*handlers):
        redirects=[h for h in handlers if isinstance(h,urllib.request.HTTPRedirectHandler)]
        assert len(redirects)==1 and redirects[0].redirect_request(None,None,None,None,None,None) is None
        return Opener()
    monkeypatch.setattr(urllib.request,'build_opener',opener)
    with pytest.raises(ValueError):public_transport('/v8/finance/chart/AAPL?range=1y&interval=1d')
    assert len(seen)==1 and seen[0][0].startswith('https://query1.finance.yahoo.com/') and seen[0][2]==30
    assert all(k.lower()!='authorization' for k,v in seen[0][1])

@pytest.mark.parametrize('raw',[{}, {'chart':None}, {'chart':[]}, {'chart':{'result':[{}]}}])
def test_public_malformed_envelope_rejected(raw):
    with pytest.raises(ValueError):fetch(lambda *a:raw,'AAPL','US',2,AT)
