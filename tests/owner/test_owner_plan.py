import uuid
import pytest
from awesome_stock.storage.owner_plan import workspace,save_plan
from awesome_stock.storage.owner import OwnerStore,restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_store import store,account,trade
from test_research_store import document
from test_owner_api import app,request,login


def plan(d,**changes):
    return {'id':str(uuid.uuid4()),'revision':0,'operation_id':str(uuid.uuid4()),'title':'Synthetic plan','decision_ref':{'id':d['id'],'revision':d['revision']},'plan_type':'build_up','trigger':'Check evidence','steps':['First verify','Then manually decide'],'risk_limit':'Manual budget','stop_condition':'Premise invalid','review_on':'2026-10-01','status':'draft'}|changes


def test_save_edit_preserves_evidence_and_never_writes_ledger(store):
    body=document('decision');d=store.save_document(body);before=store.ledger();p=plan(d);r=save_plan(store,p)
    store.save_document(body|{'revision':1,'operation_id':str(uuid.uuid4()),'content':'new judgment'})
    updated=save_plan(store,p|{'revision':1,'operation_id':str(uuid.uuid4()),'status':'completed'})
    assert updated['evidence']==r['evidence'] and updated['evidence']['decision']['content']=='Original reasoning'
    assert store.ledger()==before and workspace(store)['plans'][0]['decision_changed'] is True
    assert all(d['kind']!='plan' for d in store.documents()['documents'])


def test_retries_conflicts_and_reference_fixed(store):
    d=store.save_document(document('decision'));p=plan(d);r=save_plan(store,p);assert save_plan(store,p)==r
    with pytest.raises(Conflict):save_plan(store,p|{'title':'different'})
    with pytest.raises(Conflict):save_plan(store,p|{'operation_id':str(uuid.uuid4())})
    with pytest.raises(Conflict):save_plan(store,p|{'revision':1,'operation_id':str(uuid.uuid4()),'decision_ref':{'id':d['id'],'revision':2}})

@pytest.mark.parametrize('change',[{'steps':[]},{'steps':['']},{'steps':['a']*13},{'steps':'text'},{'status':'executed_order'},{'plan_type':'automatic'},{'trigger':''},{'risk_limit':''},{'stop_condition':''},{'review_on':'2026-02-30'},{'revision':True},{'workspace':'other'}])
def test_invalid_input_no_write(store,change):
    d=store.save_document(document('decision'))
    with pytest.raises(ValueError):save_plan(store,plan(d,**change))
    assert workspace(store)['plans']==[]


def test_wrong_kind_archive_rejection_and_old_plan_remains_editable(store):
    n=store.save_document(document())
    with pytest.raises(ValueError):save_plan(store,plan(n))
    d=store.save_document(document('decision'));p=plan(d);r=save_plan(store,p)
    store.save_document({'id':d['id'],'revision':1,'operation_id':str(uuid.uuid4())},archive=True)
    with pytest.raises(ValueError):save_plan(store,plan(d))
    assert save_plan(store,p|{'revision':1,'operation_id':str(uuid.uuid4()),'status':'paused'})['status']=='paused'
    a={'id':r['id'],'revision':2,'operation_id':str(uuid.uuid4())};assert save_plan(store,a,archive=True)['archived']
    assert len(workspace(store)['versions'])==3
    with pytest.raises(Conflict):save_plan(store,p|{'revision':3,'operation_id':str(uuid.uuid4())})


def test_restart_and_backup_restore(store,tmp_path):
    d=store.save_document(document('decision'));save_plan(store,plan(d));expected=workspace(store)
    assert workspace(OwnerStore(store.directory))==expected
    b=store.backup();dest=tmp_path.resolve()/'plan-restore';restore_owner(store.directory/'backups'/b['name'],dest)
    assert workspace(OwnerStore(dest))==expected


def test_api_permissions(app):
    assert request(app,'/api/v1/owner/plans')['status']==401
    d=app.store.save_document(document('decision'));auth=login(app);body=plan(d)
    assert request(app,'/api/v1/owner/plans','POST',body,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/plans','POST',body,**auth)['status']==200
    assert request(app,'/api/v1/owner/plans',**auth)['body']['executes_trades'] is False
