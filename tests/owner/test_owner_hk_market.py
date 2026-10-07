from datetime import datetime,timezone,timedelta
from decimal import Decimal
import copy,json
import pytest
from awesome_stock.runtime import owner_connections as conn
from awesome_stock.runtime.owner_hk_data import fetch
from awesome_stock.storage import owner_business as b,owner_market_history as history,owner_research_technical as technical
from awesome_stock.storage import owner_research_reports as reports
from awesome_stock.storage.owner import OwnerStore,restore_owner
from test_owner_api import app,login,request
from test_owner_market_history import uid

KEY='synthetic-hk-key'


def listing():return [{'Code':'0700','Name':'Synthetic Hong Kong','Exchange':'HK','Currency':'HKD','Type':'Common Stock'}]
def candles(at=None,count=30):
    today=(at or b.now()).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Hong_Kong')).date()
    return [{'date':(today-timedelta(days=count-1-i)).isoformat(),'open':10+i,'high':12+i,'low':9+i,'close':Decimal('11.125')+i,'adjusted_close':1,'volume':1000+i} for i in range(count)]
def configured(metadata=None,rows=None):
    calls=[]
    def send(host,path,body):
        calls.append((host,path,body))
        return (listing() if metadata is None else metadata) if 'exchange-symbol-list' in path else (candles() if rows is None else rows)
    c=conn.Connections(send);c.configure({'kind':'data_hk','provider':'eodhd','model':'','key':KEY,'enabled':True})
    return c,calls


def test_hk_two_calls_exact_currency_raw_prices_fixed_history_restore(app,tmp_path):
    c,calls=configured();before=app.store.ledger();p=c.market_history({'symbol':'00700','market':'HK'})
    assert len(calls)==2 and all(call[0]=='eodhd.com' for call in calls)
    assert 'symbols=0700' in calls[0][1] and '/api/eod/0700.HK?' in calls[1][1]
    packet=p['packet'];assert packet['symbol']=='00700' and packet['currency']=='HKD'
    assert packet['price_basis']=='raw_unadjusted' and packet['volume_basis']=='split_adjusted'
    assert packet['candles'][0]['close']=='11.125' and packet['candles'][0]['volume']=='1000'
    saved=history.save(app.store,{'id':uid(),'operation_id':uid(),'token':p['token']},c)
    assert technical.read(app.store,{'symbol':'00700'})['status']=='ready'
    fixed=reports.preview(app.store,{'symbol':'00700','lenses':['momentum']})
    assert fixed['packet']['market_technical']['source']['listing_evidence']['Code']=='0700'
    assert '成交量' in fixed['packet']['market_technical']['notice']
    assert app.store.ledger()==before and KEY not in app.store.path.read_bytes().decode('latin1')
    backup=app.store.backup();dest=tmp_path.resolve()/'hk-restored';restore_owner(app.store.directory/'backups'/backup['name'],dest)
    assert history.history(OwnerStore(dest))==history.history(app.store)
    assert saved['listing_evidence']['Currency']=='HKD'


def test_quote_uses_last_two_raw_daily_closes_and_bounded_dates():
    c,calls=configured();q=c.quote({'symbol':'0700','market':'HK'})
    assert q['symbol']=='00700' and q['price']=='40.125' and q['previous_close']=='39.125'
    assert not q['stored'] and not q['realtime'] and len(calls)==2
    c,_=configured(rows=candles(count=1));assert c.quote({'symbol':'00700','market':'HK'})['previous_close'] is None


@pytest.mark.parametrize('change',[{'Currency':'CNY'},{'Exchange':'US'},{'Code':'0701'},{'Type':'Warrant'},{'Name':''}])
def test_listing_mismatch_stops_before_price_call(change):
    c,calls=configured(metadata=[{**listing()[0],**change}])
    with pytest.raises(conn.ConnectionFailure):c.market_history({'symbol':'00700','market':'HK'})
    assert len(calls)==1 and not c.histories


@pytest.mark.parametrize('bad',[[],{},[listing()[0],listing()[0]]])
def test_empty_ambiguous_or_error_listing_is_not_accepted(bad):
    c,calls=configured(metadata=bad)
    with pytest.raises(conn.ConnectionFailure):c.quote({'symbol':'00700','market':'HK'})
    assert len(calls)==1


@pytest.mark.parametrize('change',['missing','future','duplicate','nan','bool','range','too_many'])
def test_bad_ohlcv_never_creates_receipt(change):
    rows=candles()
    if change=='missing':del rows[0]['volume']
    elif change=='future':rows[-1]['date']='2999-01-01'
    elif change=='duplicate':rows[1]['date']=rows[0]['date']
    elif change=='nan':rows[0]['close']=float('nan')
    elif change=='bool':rows[0]['open']=True
    elif change=='range':rows[0]['high']=1
    else:rows=rows*10
    c,calls=configured(rows=rows)
    with pytest.raises(conn.ConnectionFailure):c.market_history({'symbol':'00700','market':'HK'})
    assert not c.histories and len(calls)==2


def test_connections_and_credentials_never_cross_provider_boundaries():
    c,calls=configured()
    with pytest.raises(conn.ConnectionFailure):c.market_history({'symbol':'TEST'})
    with pytest.raises(conn.ConnectionFailure):c.company_overview({'symbol':'TEST'})
    assert not calls
    c.configure({'kind':'data','provider':'alphavantage','key':'other-key','model':'','enabled':True})
    p=c.market_history({'symbol':'00700','market':'HK'})
    assert all(KEY in call[1] and 'other-key' not in call[1] for call in calls)
    assert KEY not in json.dumps(c.status()) and 'other-key' not in json.dumps(c.status())
    c.configure({'kind':'data_hk','provider':'','key':'','model':'','enabled':False})
    assert c.status()['data']['enabled'] and not c.status()['data_hk']['enabled']
    with pytest.raises(conn.ConnectionFailure):c.history_receipt(p['token'])
    with pytest.raises(conn.ConnectionFailure):c.quote({'symbol':'00700','market':'HK'})
    c.clear();assert not c.status()['data']['enabled']


def test_hong_kong_local_date_and_valuation(app,monkeypatch):
    instant=datetime(2026,9,27,20,tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return instant
    monkeypatch.setattr(conn,'datetime',Clock);monkeypatch.setattr(b,'now',lambda:instant)
    c,_=configured(rows=candles(instant));q=c.quote({'symbol':'00700','market':'HK'})
    assert q['as_of']=='2026-09-28'
    aid=uid();app.store.add_account({'id':aid,'operation_id':uid(),'name':'HK fixture','currency':'HKD','opening_cash':'1000'})
    app.store.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':aid,'symbol':'00700','side':'buy','quantity':'2','price':'10','fee':'0','executed_at':'2026-01-01T00:00:00Z'})
    b.save(app.store,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{k:q[k] for k in ['symbol','currency','price','as_of','source','previous_close']}})
    assert b.workspace(app.store)['accounts'][0]['positions'][0]['day_price_effect']=='2.000'


def test_hk_auth_csrf_and_invalid_inputs(app):
    payload={'symbol':'00700','market':'HK'};path='/api/v1/owner/market-history-fetch'
    assert request(app,path,'POST',payload)['status']==401
    auth=login(app);assert request(app,path,'POST',payload,cookie=auth['cookie'])['status']==403
    configured_connection,calls=configured();app.connections.send=configured_connection.send
    request(app,'/api/v1/owner/connections','POST',{'kind':'data_hk','provider':'eodhd','model':'','key':KEY,'enabled':True},**auth)
    assert request(app,path,'POST',payload,**auth)['body']['packet']['currency']=='HKD'
    for sy in ['00000','700','TEST','00700.HK','600104']:
        with pytest.raises(ValueError):app.connections.quote({'symbol':sy,'market':'HK'})


def test_eod_transport_array_only_on_bounded_provider_paths(monkeypatch):
    from io import BytesIO
    class Response(BytesIO):
        status=200
        def getheader(self,*args):return '0'
    class HTTP:
        def request(self,*args,**kwargs):pass
        def getresponse(self):return Response(b'[{"close":0.12345678}]')
        def close(self):pass
    monkeypatch.setattr(conn.http.client,'HTTPSConnection',lambda *a,**kw:HTTP())
    rows=conn.transport('eodhd.com','/api/eod/0700.HK?fmt=json',None)
    assert rows[0]['close']==Decimal('0.12345678')
    with pytest.raises(conn.ConnectionFailure):conn.transport('api.openai.com','/v1/responses',{})
    with pytest.raises(conn.ConnectionFailure):conn.transport('eodhd.com','/unknown',None)


def test_provider_cannot_echo_token_into_saved_listing(app):
    c,_=configured(metadata=[{**listing()[0],'Name':'Synthetic '+KEY}])
    p=c.market_history({'symbol':'00700','market':'HK'})
    assert KEY not in json.dumps(p)
    history.save(app.store,{'id':uid(),'operation_id':uid(),'token':p['token']},c)
    assert KEY not in app.store.path.read_bytes().decode('latin1')
