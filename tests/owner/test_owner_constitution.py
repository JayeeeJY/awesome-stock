import uuid
import pytest
from awesome_stock.storage import owner_constitution as c
from awesome_stock.storage.local import Conflict
from test_owner_store import store
from test_owner_api import app,request,login

CONFIG={'policy':{'warning_percent':'20','max_percent':'30','shock_percent':'10','custom_rules':[]},
        'require_reason_before_trade':True,'prohibited_actions':['Synthetic manual restriction']}
def body(**changes):
    return {'operation_id':str(uuid.uuid4()),'revision':0,'config':CONFIG}|changes


def test_versioned_settings_idempotency_and_conflict(store):
    assert c.history(store)['current'] is None
    before=store.ledger();b=body();one=c.save(store,b)
    assert c.save(store,b)==one
    two=c.save(store,body(revision=1,config=CONFIG|{'require_reason_before_trade':False}))
    h=c.history(store)
    assert h['current']==two and h['versions']==[two,one]
    assert h['versions'][1]['config']['require_reason_before_trade'] is True
    assert store.ledger()==before
    with pytest.raises(Conflict):c.save(store,body())


def test_validates_rules_and_does_not_accept_legacy_inactive_flags(store):
    for cfg in [CONFIG|{'require_reason_before_trade':'true'},
                CONFIG|{'prohibited_actions':['same','same']},
                CONFIG|{'block_add_when_thesis_weakens':True},
                CONFIG|{'policy':CONFIG['policy']|{'max_percent':'10'}}]:
        with pytest.raises(ValueError):c.save(store,body(config=cfg))
    assert c.history(store)['versions']==[]


def test_auth_csrf_and_route(app):
    assert request(app,'/api/v1/owner/constitution')['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/constitution','POST',body(),cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/constitution','POST',body(),**auth)['status']==200
    assert request(app,'/api/v1/owner/constitution',**auth)['body']['current']['revision']==1
