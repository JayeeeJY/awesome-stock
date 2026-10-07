from datetime import datetime,timezone,timedelta
import pytest
from awesome_stock.runtime import owner_connections as connections
from awesome_stock.storage import owner_business as b, owner_market_history as h, owner_research_technical as technical
from awesome_stock.storage import owner_research_reports as reports
from awesome_stock.research.market_identity import identity
from test_owner_api import app,login,request
from test_owner_market_history import configured,uid


def raw(symbol='600104.SHH',today=None):
    today=today or b.now().date()
    return {'Meta Data':{'2. Symbol':symbol},'Time Series (Daily)':{(today-timedelta(days=29-i)).isoformat():{'1. open':str(10+i),'2. high':str(12+i),'3. low':str(9+i),'4. close':str(11+i),'5. volume':'1000'} for i in range(30)}}


@pytest.mark.parametrize('symbol',['600104.SHH','688001.SHH','000002.SHZ','300001.SHZ'])
def test_a_share_identity_saved_technical_and_fixed_report(app,symbol):
    c=configured(lambda *a:raw(symbol));p=c.market_history({'symbol':symbol,'market':'CN'})
    assert p['packet']['currency']=='CNY' and p['packet']['date_basis']=='Asia/Shanghai'
    saved=h.save(app.store,{'id':uid(),'operation_id':uid(),'token':p['token']},c)
    t=technical.read(app.store,{'symbol':symbol.split('.')[0]})
    assert t['status']=='ready' and t['source']['id']==saved['id'] and t['technical']['moving_averages']['ma20']==30.5
    fixed=reports.preview(app.store,{'symbol':symbol.split('.')[0],'lenses':['momentum']})
    assert fixed['packet']['market_technical']['source']['currency']=='CNY'


@pytest.mark.parametrize('symbol,market',[('123456','CN'),('600104.SHH','US'),('TEST','CN'),('900001.SHH','CN'),('200001.SHZ','CN'),('0700.HK','CN'),('510300.SHH','CN'),('600104.SHH','HK')])
def test_unsupported_market_or_security_never_requests(symbol,market):
    calls=[];c=configured(lambda *a:calls.append(a))
    for method in [c.quote,c.market_history]:
        with pytest.raises(ValueError):method({'symbol':symbol,'market':market})
    assert not calls


def test_china_date_boundary_quote_history_and_valuation(app,monkeypatch):
    instant=datetime(2026,9,27,20,tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return instant
    monkeypatch.setattr(connections,'datetime',Clock);monkeypatch.setattr(b,'now',lambda:instant)
    symbol='600104';provider_symbol='600104.SHH';local_day=(instant+timedelta(hours=8)).date()
    c=configured(lambda *a:{'Global Quote':{'01. symbol':provider_symbol,'05. price':'20','08. previous close':'18','07. latest trading day':local_day.isoformat()}})
    q=c.quote({'symbol':symbol,'market':'CN'});assert q['currency']=='CNY'
    aid=uid();app.store.add_account({'id':aid,'operation_id':uid(),'name':'Synthetic CNY','currency':'CNY','opening_cash':'1000'})
    app.store.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':aid,'symbol':symbol,'side':'buy','quantity':'2','price':'10','fee':'0','executed_at':'2026-01-01T00:00:00Z'})
    b.save(app.store,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{k:q[k] for k in ['symbol','currency','price','previous_close','as_of','source']}})
    position=b.workspace(app.store)['accounts'][0]['positions'][0]
    assert position['market_value']=='40' and position['day_price_effect']=='4'
    c=configured(lambda *a:raw(provider_symbol,local_day));p=c.market_history({'symbol':symbol,'market':'CN'})
    h.save(app.store,{'id':uid(),'operation_id':uid(),'token':p['token']},c)
    assert technical.read(app.store,{'symbol':symbol})['status']=='ready'
    c=configured(lambda *a:raw(provider_symbol,local_day+timedelta(days=1)))
    with pytest.raises(connections.ConnectionFailure):c.market_history({'symbol':symbol,'market':'CN'})


def test_auth_and_csrf_and_currency_response(app):
    app.connections.send=lambda *a:raw()
    payload={'symbol':'600104.SHH','market':'CN'};path='/api/v1/owner/market-history-fetch'
    assert request(app,path,'POST',payload)['status']==401
    auth=login(app);assert request(app,path,'POST',payload,cookie=auth['cookie'])['status']==403
    app.connections.configure({'kind':'data','provider':'alphavantage','key':'synthetic-key','model':'','enabled':True})
    assert request(app,path,'POST',payload,**auth)['body']['packet']['currency']=='CNY'


def test_china_midnight_invalidates_diagnostic_preview_without_utc_change(app,monkeypatch):
    from awesome_stock.storage import owner_diagnosis as diagnosis
    from awesome_stock.storage.local import Conflict
    from test_owner_diagnosis import body
    before=datetime(2026,9,27,15,59,tzinfo=timezone.utc)
    monkeypatch.setattr(b,'now',lambda:before)
    aid=uid();app.store.add_account({'id':aid,'operation_id':uid(),'name':'Synthetic China','currency':'CNY','opening_cash':'1000'})
    app.store.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':aid,'symbol':'600104.SHH','side':'buy','quantity':'2','price':'10','fee':'0','executed_at':'2026-01-01T00:00:00Z'})
    b.save(app.store,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{'symbol':'600104.SHH','currency':'CNY','price':'20','as_of':'2026-09-24','source':'Synthetic'}})
    inp={**body(),'account_id':aid,'holding_context':{}};p=diagnosis.preview(app.store,inp)
    assert p['report']['status']=='partial'
    monkeypatch.setattr(b,'now',lambda:before+timedelta(minutes=2))
    assert diagnosis.preview(app.store,inp)['report']['status']=='unavailable'
    with pytest.raises(Conflict):diagnosis.save(app.store,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']})
