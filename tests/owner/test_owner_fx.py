import uuid
from datetime import timedelta
import pytest
from awesome_stock.storage import owner_fx as fx,owner_business as b
from awesome_stock.storage.owner import OwnerStore,restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_api import app,login,request

def uid():return str(uuid.uuid4())
def rate(**changes):
    day=b.now().date().isoformat()
    return {'operation_id':uid(),'revision':0,'currency':'HKD','rate':'0.125','as_of':day,'expires_on':day,'source':'Synthetic source',**changes}

def fund(store,currency):
    aid=uid();store.add_account({'id':aid,'operation_id':uid(),'name':currency,'currency':currency,'opening_cash':'1000'})
    store.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':aid,'symbol':'TEST','side':'buy','quantity':'2','price':'10','fee':'1','executed_at':'2026-01-01T00:00:00Z'})
    b.save(store,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{'symbol':'TEST','currency':currency,'price':'20','as_of':b.now().date().isoformat(),'source':'Synthetic price'}})
    return aid

def test_usd_identity_foreign_missing_exact_conversion_and_lead(app,tmp_path):
    usd=fund(app.store,'USD');hkd=fund(app.store,'HKD')
    before=fx.valuation(app.store);assert before['lead_account_id'] is None and before['total_holdings_usd'] is None
    req=rate();saved=fx.save(app.store,req);assert fx.save(app.store,req)==saved
    result=fx.valuation(app.store);assert result['total_holdings_usd']=='45.000'
    row=next(r for r in result['accounts'] if r['account_id']==hkd)
    assert row['holdings_value_usd']=='5.000' and row['assets_value_usd']=='127.375'
    assert row['total_return_at_current_fx_usd']=='2.375' and result['lead_account_id']==usd
    assert row['fx_evidence']['revision']==1
    backup=app.store.backup();destination=tmp_path.resolve()/'restored-fx';restore_owner(app.store.directory/'backups'/backup['name'],destination)
    assert fx.valuation(OwnerStore(destination))==result


def test_stale_rate_no_old_fallback_and_version_conflict(app,monkeypatch):
    fund(app.store,'HKD');fx.save(app.store,rate());now=b.now()
    monkeypatch.setattr(b,'now',lambda:now+timedelta(days=1))
    assert fx.valuation(app.store)['accounts'][0]['fx_status']=='stale'
    assert fx.valuation(app.store)['total_holdings_usd'] is None
    with pytest.raises(Conflict):fx.save(app.store,rate())
    fx.save(app.store,rate(revision=1,rate='0.13'))
    assert len(fx.history(app.store)['versions'])==2
    assert fx.valuation(app.store)['total_holdings_usd']=='5.20'

@pytest.mark.parametrize('changes',[{'rate':'0'},{'rate':'-1'},{'rate':'1e-2'},{'rate':0.12},{'currency':'USD'},{'currency':'XXX'},{'source':''},{'as_of':'9999-01-01'},{'expires_on':'2000-01-01'}])
def test_invalid_rate_rejected_without_write(app,changes):
    with pytest.raises(ValueError):fx.save(app.store,rate(**changes))
    assert fx.history(app.store)['rates']==[]


def test_api_auth_csrf_and_ledger_unchanged(app):
    assert request(app,'/api/v1/owner/base-valuation')['status']==401
    auth=login(app);before=app.store.ledger()
    assert request(app,'/api/v1/owner/fx-rates','POST',rate(),cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/fx-rates','POST',rate(),**auth)['status']==200
    assert app.store.ledger()==before


def test_cash_only_without_fx_does_not_hide_missing_asset_conversion(app):
    app.store.add_account({'id':uid(),'operation_id':uid(),'name':'Cash only','currency':'HKD','opening_cash':'1000'})
    result=fx.valuation(app.store)
    assert result['holdings_complete'] is True and result['total_holdings_usd']=='0'
    assert result['lead_account_id'] is None
    row=result['accounts'][0]
    assert row['holdings_value_usd']=='0' and row['assets_value_usd'] is None
    assert row['fx_status']=='missing'


def test_current_fx_cannot_make_stale_prices_complete(app,monkeypatch):
    fund(app.store,'HKD');now=b.now()
    fx.save(app.store,rate(expires_on=(now+timedelta(days=10)).date().isoformat()))
    monkeypatch.setattr(b,'now',lambda:now+timedelta(days=4))
    result=fx.valuation(app.store);row=result['accounts'][0]
    assert row['fx_status']=='current' and row['price_complete'] is False
    assert row['holdings_value_usd'] is None and row['assets_value_usd'] is None
    assert row['total_return_at_current_fx_usd'] is None
    assert result['holdings_complete'] is False and result['lead_account_id'] is None


def test_native_and_usd_values_share_one_snapshot(app,monkeypatch):
    fund(app.store,'HKD');fx.save(app.store,rate())
    original=b.valued_accounts;calls=[]
    def read_once(store,db):
        assert db.in_transaction
        calls.append(db)
        return original(store,db)
    monkeypatch.setattr(b,'valued_accounts',read_once)
    data=fx.valuation(app.store)
    assert len(calls)==1
    native=data['native_accounts'][0];converted=data['accounts'][0]
    assert native['id']==converted['account_id']
    assert native['positions'][0]['market_value']=='40'
    assert converted['holdings_value_usd']=='5.000'


def test_workspace_conversion_same_snapshot_and_position_values(app,monkeypatch):
    usd=fund(app.store,'USD');hkd=fund(app.store,'HKD');fx.save(app.store,rate())
    original=b.valued_accounts;calls=[]
    def one_read(store,db):
        assert db.in_transaction
        calls.append(True);return original(store,db)
    monkeypatch.setattr(b,'valued_accounts',one_read)
    data=b.workspace(app.store);assert len(calls)==1
    base=data['base_valuation'];assert 'native_accounts' not in base
    row=next(r for r in base['accounts'] if r['account_id']==hkd)
    assert row['cash_usd']=='122.375'
    assert row['unrealized_at_current_fx_usd']=='2.375'
    assert row['realized_at_current_fx_usd']=='0'
    assert row['positions']==[{'symbol':'TEST','market_value_usd':'5.000','total_return_at_current_fx_usd':'2.375'}]
    assert row['fx_evidence']['revision']==1


def test_workspace_missing_and_stale_fx_do_not_fabricate_conversion(app,monkeypatch):
    fund(app.store,'HKD')
    row=b.workspace(app.store)['base_valuation']['accounts'][0]
    assert row['positions'][0]['market_value_usd'] is None and row['cash_usd'] is None
    fx.save(app.store,rate());now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=1))
    row=b.workspace(app.store)['base_valuation']['accounts'][0]
    assert row['fx_status']=='stale' and row['positions'][0]['total_return_at_current_fx_usd'] is None


def test_previous_close_effect_is_current_quantity_not_actual_day_profit(app,monkeypatch,tmp_path):
    aid=fund(app.store,'HKD');fx.save(app.store,rate())
    today=b.now().date().isoformat()
    q=b.save(app.store,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{'symbol':'TEST','currency':'HKD','price':'20','previous_close':'18','as_of':today,'source':'Paired synthetic quote'}})
    result=b.workspace(app.store);position=result['accounts'][0]['positions'][0]
    assert position['day_price_effect']=='4' and position['quote']['previous_close']=='18'
    assert result['base_valuation']['accounts'][0]['day_price_effect_usd']=='0.500'
    # Today's added quantity changes this price-effect metric; it is not ledger daily P&L.
    app.store.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':aid,'symbol':'TEST','side':'buy','quantity':'1','price':'20','fee':'1','executed_at':b.now().isoformat().replace('+00:00','Z')})
    assert b.workspace(app.store)['accounts'][0]['positions'][0]['day_price_effect']=='6'
    backup=app.store.backup();dest=tmp_path.resolve()/'day-effect-restore';restore_owner(app.store.directory/'backups'/backup['name'],dest)
    assert b.workspace(OwnerStore(dest))['accounts'][0]['positions'][0]['quote']['previous_close']=='18'
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=1))
    after=b.workspace(app.store);assert after['accounts'][0]['positions'][0]['quote_status']=='current_snapshot'
    assert after['accounts'][0]['positions'][0]['day_price_effect'] is None
    assert after['base_valuation']['accounts'][0]['day_price_effect_usd'] is None

@pytest.mark.parametrize('value',['0','-1','NaN','1e2',True,{},[]])
def test_invalid_previous_close_rejected(app,value):
    with pytest.raises(ValueError):b.save(app.store,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{'symbol':'TEST','currency':'USD','price':'20','previous_close':value,'as_of':b.now().date().isoformat(),'source':'Synthetic'}})


def test_market_date_evidence_changes_at_asian_midnight(app,monkeypatch):
    from datetime import datetime,timezone
    monkeypatch.setattr(b,'now',lambda:datetime(2026,9,27,15,59,tzinfo=timezone.utc))
    for currency,symbol in [('HKD','00700'),('CNY','600104')]:
        aid=uid();app.store.add_account({'id':aid,'operation_id':uid(),'name':currency,'currency':currency,'opening_cash':'1000'})
        app.store.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':aid,'symbol':symbol,'side':'buy','quantity':'2','price':'10','fee':'0','executed_at':'2026-01-01T00:00:00Z'})
    before=fx.valuation(app.store)
    assert before['evaluated_market_dates']=={'UTC':'2026-09-27','Asia/Shanghai':'2026-09-27','Asia/Hong_Kong':'2026-09-27'}
    monkeypatch.setattr(b,'now',lambda:datetime(2026,9,27,16,0,tzinfo=timezone.utc))
    after=fx.valuation(app.store)
    assert before['evaluated_on']==after['evaluated_on']
    assert after['evaluated_market_dates']=={'UTC':'2026-09-27','Asia/Shanghai':'2026-09-28','Asia/Hong_Kong':'2026-09-28'}
