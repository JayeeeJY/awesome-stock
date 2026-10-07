import uuid
import pytest
from awesome_stock.storage.owner_plan import save_plan,record_trade,workspace
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import LedgerInvalid
from test_owner_store import store,account,snapshot
from test_research_store import document
from test_owner_plan import plan
from test_owner_api import app,request,login

def setup(store):
    a=store.add_account(account());d=store.save_document(document('decision'));p=save_plan(store,plan(d))
    return {'id':str(uuid.uuid4()),'trade_id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4()),'plan_id':p['id'],'plan_revision':p['revision'],'step_index':0,'account_id':a['id'],'side':'buy','quantity':'2','price':'10','fee':'1','executed_at':'2026-09-27T08:00:00Z','note':'Actual confirmed fill','confirmed':True}

def test_atomic_trade_link_idempotent(store):
    body=setup(store);r=record_trade(store,body);assert record_trade(store,body)==r
    assert len(store.ledger()['accounts'][0]['trades'])==1
    assert store.ledger()['accounts'][0]['cash']=='979'
    assert workspace(store)['executions'][0]['trade']['id']==r['trade']['id']
    with pytest.raises(Conflict):record_trade(store,body|{'price':'11'})

@pytest.mark.parametrize('change',[{'confirmed':False},{'confirmed':1},{'step_index':99},{'note':''},{'plan_revision':2},{'quantity':'10000'},{'side':'sell'}])
def test_failed_trade_link_rolls_back_everything(store,change):
    b=setup(store);before=snapshot(store);docs=workspace(store)
    with pytest.raises((ValueError,Conflict,LedgerInvalid)):record_trade(store,b|change)
    assert snapshot(store)==before and workspace(store)==docs

def test_api_requires_auth_and_csrf(app):
    b=setup(app.store)
    assert request(app,'/api/v1/owner/plan-trades','POST',b)['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/plan-trades','POST',b,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/plan-trades','POST',b,**auth)['status']==200
