import uuid
import pytest
from awesome_stock.storage import owner_trade_context as c
from awesome_stock.storage.local import Conflict
from test_owner_store import store,account,trade
from test_owner_evolve import seed
from test_owner_api import app,request,login


def body(t,**changes):
    return {'operation_id':str(uuid.uuid4()),'trade_id':t['id'],'trade_revision':1,'revision':0,'decision_required':True,'reason':''}|changes


def test_explicit_qualification_versions_and_no_ledger_rewrite(store):
    store.add_account(account());t=trade();store.trade(t);before=store.ledger()
    assert c.history(store,{'trade_id':t['id']})['qualification']=='ordinary'
    b=body(t);one=c.save(store,b);assert c.save(store,b)==one
    h=c.history(store,{'trade_id':t['id']});assert h['qualification']=='required_without_context'
    two=c.save(store,body(t,revision=1,decision_required=False,reason='Synthetic ordinary fact'))
    h=c.history(store,{'trade_id':t['id']});assert h['qualification']=='ordinary' and h['versions']==[two,one]
    assert store.ledger()==before
    with pytest.raises(Conflict):c.save(store,body(t))


def test_trade_edit_requires_reconfirmation_and_link_has_priority(store):
    d,t=seed(store);c.save(store,body(t,decision_required=False))
    assert c.history(store,{'trade_id':t['id']})['qualification']=='linked_decision'
    # A separate unlinked trade must not silently carry a qualification to changed facts.
    other=trade();store.trade(other);c.save(store,body(other))
    store.trade(other|{'revision':1,'price':'11','operation_id':str(uuid.uuid4())})
    h=c.history(store,{'trade_id':other['id']});assert h['qualification']=='needs_reconfirmation'
    with pytest.raises(Conflict):c.save(store,body(other,revision=1))
    c.save(store,body(other,trade_revision=2,revision=1))
    assert c.history(store,{'trade_id':other['id']})['qualification']=='required_without_context'


def test_validation_and_auth(app):
    auth=login(app);b=body({'id':str(uuid.uuid4())})
    assert request(app,'/api/v1/owner/trade-context','POST',b)['status']==401
    assert request(app,'/api/v1/owner/trade-context','POST',b,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/trade-context','POST',b,**auth)['status']==400
    assert request(app,'/api/v1/owner/trade-context','POST',b|{'decision_required':'true'},**auth)['status']==400
