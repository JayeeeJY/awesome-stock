import uuid
import pytest
from awesome_stock.storage.owner_plan import save_plan,workspace
from test_owner_store import store,account
from test_research_store import document
from test_owner_plan import plan

def strategy():return {'anchor_price':'100','base_percent':'20','rules':[{'pullback_percent':'5','add_percent':'20','label':'Review evidence'}]}
def body(store):
    a=store.add_account(account());d=store.save_document(document('decision'))
    return plan(d,target={'account_id':a['id'],'quantity':'100','budget':'10000'},strategy=strategy())

def test_strategy_versions_legacy_preservation_and_no_execution(store):
    b=body(store);before=store.ledger();p=save_plan(store,b);assert save_plan(store,b)==p
    legacy={k:v for k,v in b.items() if k not in ('target','strategy')}
    edited=save_plan(store,legacy|{'revision':1,'operation_id':str(uuid.uuid4()),'title':'Changed'})
    assert edited['strategy']==p['strategy'] and edited['target']==p['target']
    cleared=save_plan(store,b|{'revision':2,'operation_id':str(uuid.uuid4()),'strategy':None})
    assert cleared['strategy'] is None and workspace(store)['versions'][0]['strategy']==strategy()
    assert store.ledger()==before

@pytest.mark.parametrize('change',[{'anchor_price':'0'},{'base_percent':'101'},{'rules':[]},{'rules':[{'pullback_percent':'100','add_percent':'20','label':'Invalid'}]},{'rules':[{'pullback_percent':'5','add_percent':'0','label':'Invalid'}]},{'rules':[strategy()['rules'][0],strategy()['rules'][0]]}])
def test_invalid_strategy_atomic(store,change):
    b=body(store)
    with pytest.raises(ValueError):save_plan(store,b|{'strategy':strategy()|change})
    assert workspace(store)['plans']==[]

def test_strategy_requires_target_account(store):
    b=body(store)
    with pytest.raises(ValueError):save_plan(store,b|{'target':None})
