from decimal import Decimal
from datetime import timedelta, datetime
import pytest
from awesome_stock.storage import owner_diagnosis as d, owner_diagnosis_scope as scopes
from awesome_stock.storage import owner_daily as daily, owner_schedule as schedule, owner_fx as fx
from awesome_stock.storage import owner_diagnosis_sources as sources, owner_business as b
from awesome_stock.storage.owner import identifier, OwnerStore, restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_api import app, login, request
from test_owner_fx import fund, rate, uid
from test_owner_diagnosis import body, save
from test_owner_company import saved as save_company


def data():
    return {**body(), 'account_id': scopes.ALL, 'holding_context': {}}


def test_currency_groups_exact_values_and_no_ledger_mutation(app):
    usd1=fund(app.store,'USD');usd2=fund(app.store,'USD');hkd=fund(app.store,'HKD')
    before=app.store.ledger()
    assert d.preview(app.store,data())['report']['status']=='unavailable'
    fx.save(app.store,rate());p=d.preview(app.store,data())['report']
    assert p['status']=='partial' and Decimal(p['total_value'])==85
    assert p['position_count']==2 and p['currency']=='USD'
    positions={p['symbol']:p for p in p['account_evidence']['positions']}
    assert Decimal(positions['USD:TEST']['market_value'])==80
    assert Decimal(positions['USD:TEST']['open_cost'])==42
    assert len(positions['USD:TEST']['components'])==2
    assert Decimal(positions['HKD:TEST']['market_value'])==5
    assert Decimal(positions['HKD:TEST']['unrealized_pnl'])==Decimal('2.375')
    assert positions['HKD:TEST']['components'][0]['fx_evidence']['revision']==1
    assert sum(Decimal(i['scenario_pnl']) for i in p['impacts'])==Decimal('-8.5')
    assert app.store.ledger()==before
    with pytest.raises(ValueError):identifier(scopes.ALL)
    assert not d.history(app.store,usd1)['reports']


def test_complete_context_history_daily_and_restore(app,tmp_path):
    aid=fund(app.store,'USD');fund(app.store,'HKD');fx.save(app.store,rate())
    inp=data();inp['holding_context']={key:{**body()['holding_context']['TEST'],'company':key} for key in ['USD:TEST','HKD:TEST']}
    fixed=save(app.store,inp);assert fixed['report']['status']=='complete'
    preview=d.preview(app.store,inp);payload={'operation_id':uid(),'input':inp,'expected_token':preview['token']}
    run=daily.capture(app.store,payload);assert daily.capture(app.store,payload)==run
    assert run['snapshot']['ledger']['scope_kind']=='all_accounts'
    assert len(run['snapshot']['ledger']['accounts'])==2
    assert len(d.history(app.store,scopes.ALL)['reports'])==2
    assert not daily.history(app.store,aid)['records']
    history=daily.history(app.store,scopes.ALL)
    fx.save(app.store,rate(revision=1,rate='0.25'))
    assert daily.history(app.store,scopes.ALL)==history
    assert d.history(app.store,scopes.ALL)['reports'][1]['report']==fixed['report']
    backup=app.store.backup();dest=tmp_path.resolve()/'portfolio-restore'
    restore_owner(app.store.directory/'backups'/backup['name'],dest)
    assert daily.history(OwnerStore(dest),scopes.ALL)==history


def test_missing_stale_fx_and_new_account_invalidate_preview(app,monkeypatch):
    fund(app.store,'HKD');fx.save(app.store,rate())
    preview=d.preview(app.store,data());fund(app.store,'USD')
    with pytest.raises(Conflict):d.save(app.store,{'id':uid(),'operation_id':uid(),'input':data(),'expected_token':preview['token']})
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=1))
    assert d.preview(app.store,data())['report']['status']=='unavailable'


def test_sources_only_bind_native_usd_tickers(app):
    fund(app.store,'USD');fund(app.store,'HKD');fx.save(app.store,rate());save_company(app.store)
    c=sources.read(app.store,{'account_id':scopes.ALL,'symbol':'USD:TEST'})['context']
    assert c is not None
    assert sources.read(app.store,{'account_id':scopes.ALL,'symbol':'HKD:TEST'})['context'] is None
    inp=data();inp['holding_context']={'USD:TEST':c};assert d.preview(app.store,inp)['report']['status']=='partial'
    inp['holding_context']={'HKD:TEST':c}
    with pytest.raises(Conflict):d.preview(app.store,inp)
    with pytest.raises(ValueError):sources.read(app.store,{'account_id':scopes.ALL,'symbol':'TEST'})


def test_schedule_scope_is_independent_and_tracks_new_positions(app):
    aid=fund(app.store,'USD')
    config={'enabled':True,'timezone':'UTC','time':'16:30','weekdays':list(range(7)),'input':data()}
    saved=schedule.save(app.store,{'operation_id':uid(),'revision':0,'config':config})
    assert schedule.status(app.store,aid)['schedule'] is None
    due=datetime.fromisoformat(saved['next_due'])
    # Scheduler observation uses current saved quotes; execution does not fetch sources.
    runs=schedule.tick(app.store,due);assert len(runs)==1 and runs[0]['status']=='completed'
    assert len(daily.history(app.store,scopes.ALL)['records'])==3
    assert not schedule.tick(app.store,due)


def test_scope_endpoint_requires_auth_csrf_and_valid_scope(app):
    fund(app.store,'USD');payload={'account_id':scopes.ALL}
    path='/api/v1/owner/diagnosis-scope'
    assert request(app,path,'POST',payload)['status']==401
    auth=login(app)
    assert request(app,path,'POST',payload,cookie=auth['cookie'])['status']==403
    assert request(app,path,'POST',payload,**auth)['body']['scope_kind']=='all_accounts'
    assert request(app,path,'POST',{'account_id':'portfolio:unknown'},**auth)['status']==400


def test_layer_caps_keep_account_denominator_and_memory_currency_boundary(app):
    from test_owner_allocation_layers import layer
    from test_owner_business import obj
    from awesome_stock.storage import owner_research_memory as memory
    usd=fund(app.store,'USD');hkd=fund(app.store,'HKD');fx.save(app.store,rate())
    obj(app.store,'allocation_layer',layer(account_id=usd,max_single_percent='3'))
    obj(app.store,'allocation_layer',layer(account_id=hkd,max_single_percent='5'))
    fixed=save(app.store,data())
    assert fixed['report']['position_size_alerts']==['USD · TEST 超过已保存单股上限']
    result=memory.read(app.store,{'symbol':'TEST'})
    assert any(e['source_id']==fixed['id'] for e in result['timeline'])
    with app.store.transaction() as db:
        # A portfolio record containing only a foreign same-name holding is
        # not a source for the current US research adapter.
        foreign={**fixed,'id':uid(),'report':{**fixed['report'],'impacts':[{'symbol':'HKD:TEST'}]}}
        b._put(app.store,db,{'id':foreign['id'],'revision':0},foreign)
    assert not any(e['source_id']==foreign['id'] for e in memory.read(app.store,{'symbol':'TEST'})['timeline'])


def test_empty_and_cash_only_foreign_accounts_do_not_require_holdings_fx(app):
    assert d.preview(app.store,data())['report']['status']=='unavailable'
    fund(app.store,'USD')
    app.store.add_account({'id':uid(),'operation_id':uid(),'name':'Foreign cash','currency':'HKD','opening_cash':'1000'})
    report=d.preview(app.store,data())['report']
    assert report['status']=='partial' and Decimal(report['total_value'])==40
    foreign=next(a for a in report['account_evidence']['conversion_evidence']['accounts'] if a['currency']=='HKD')
    assert foreign['assets_value_usd'] is None
