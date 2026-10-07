import uuid
import pytest
from awesome_stock.storage.owner_plan import save_plan,save_execution,workspace
from awesome_stock.storage.local import Conflict
from test_owner_store import store,account,trade
from test_research_store import document
from test_owner_plan import plan

def fixture(store):
    d=store.save_document(document('decision'));p=save_plan(store,plan(d));store.add_account(account());t=store.trade(trade());return p,t

def link(p,t,**changes):return dict(id=str(uuid.uuid4()),revision=0,operation_id=str(uuid.uuid4()),plan_id=p['id'],plan_revision=p['revision'],step_index=0,trade_id=t['id'],trade_revision=t['revision'],note='Synthetic execution explanation')|changes

def test_fixed_execution_changed_trade_archive_and_no_double_write(store):
    p,t=fixture(store);before=store.ledger();body=link(p,t);r=save_execution(store,body);assert save_execution(store,body)==r and store.ledger()==before
    with pytest.raises(Conflict):save_execution(store,link(p,t))
    store.trade(trade(id=t['id'],revision=1,price='11'))
    e=workspace(store)['executions'][0];assert e['trade_changed'] and e['trade']['price']=='10'
    save_execution(store,dict(id=r['id'],revision=1,operation_id=str(uuid.uuid4())),archive=True)
    assert len(workspace(store)['execution_versions'])==2

@pytest.mark.parametrize('change',[{'step_index':True},{'step_index':10},{'note':''}])
def test_invalid_link_no_evidence(store,change):
    p,t=fixture(store)
    with pytest.raises(ValueError):save_execution(store,link(p,t,**change))
    assert workspace(store)['executions']==[]

def test_stale_trade_or_plan_revision_rejected(store):
    p,t=fixture(store)
    for change in [{'plan_revision':2},{'trade_revision':2}]:
        with pytest.raises(Conflict):save_execution(store,link(p,t,**change))

def test_target_progress_exact_budget_stale_and_archive(store):
    p,t=fixture(store)
    body=plan(p['evidence']['decision'],id=p['id'],revision=1,target={'account_id':t['account_id'],'quantity':'20','budget':'99'})
    p=save_plan(store,body);before=store.ledger();e=save_execution(store,link(p,t))
    progress=workspace(store)['plans'][0]['progress']
    assert progress=={'needs_review':False,'quantity':'10','spent':'101','percent':'50.00','over_budget':True}
    assert store.ledger()==before
    store.trade(trade(id=t['id'],revision=1,price='11'))
    progress=workspace(store)['plans'][0]['progress']
    assert progress['needs_review'] and progress['percent'] is None and progress['spent'] is None
    save_execution(store,dict(id=e['id'],revision=1,operation_id=str(uuid.uuid4())),archive=True)
    assert workspace(store)['plans'][0]['progress']['quantity']=='0'
    # Old clients omitting the new optional field must preserve the saved target.
    updated=save_plan(store,plan(p['evidence']['decision'],id=p['id'],revision=2))
    assert updated['target']==p['target']

@pytest.mark.parametrize('target',[{'account_id':'missing-account','quantity':'1','budget':None},{'account_id':'account-test','quantity':'0','budget':None},{'account_id':'account-test','quantity':'1e3','budget':None}])
def test_invalid_targets_atomic(store,target):
    p,t=fixture(store)
    with pytest.raises(ValueError):save_plan(store,plan(p['evidence']['decision'],id=p['id'],revision=1,target=target))
    assert workspace(store)['plans'][0]['revision']==1

def test_target_cannot_adopt_other_account_execution(store):
    p,t=fixture(store);save_execution(store,link(p,t));other=store.add_account(account(id='other-account'))
    with pytest.raises(Conflict):save_plan(store,plan(p['evidence']['decision'],id=p['id'],revision=1,target={'account_id':other['id'],'quantity':'20','budget':None}))

def test_execution_timeline_orders_instants_and_preserves_exact_amount(store):
    p,t=fixture(store)
    first=store.trade(trade(id=t['id'],revision=1,executed_at='2026-09-20T11:00:00+08:00'))
    second=store.trade(trade(id='second-trade',executed_at='2026-09-20T02:00:00+00:00',quantity='0.1',price='0.2',fee='0.01'))
    save_execution(store,link(p,first));save_execution(store,link(p,second))
    rows=workspace(store)['executions']
    assert [e['trade']['id'] for e in rows]==['second-trade',t['id']]
    assert rows[0]['amount']=='0.03' and rows[1]['amount']=='101'
