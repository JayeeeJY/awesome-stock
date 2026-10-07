import uuid
import pytest
from awesome_stock.storage.owner_evolve import workspace,save_review
from awesome_stock.storage.owner import OwnerStore,restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_store import store,account,trade
from test_research_store import document,link
from test_owner_api import app,request,login


def review(store,**changes):
    c=workspace(store)['candidates'][0]
    return {'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4()),'revision':0,'decision_ref':c['ref'],'expected_evidence':c['fingerprint'],'reviewed_on':'2026-09-19','process_status':'unclear','process_note':'Manual process evidence','outcome_status':'pending','outcome_note':'','next_step':'Check original premise'}|changes


def seed(store):
    n=store.save_document(document());d=store.save_document(document('decision',research_ref={'id':n['id'],'revision':1}));store.add_account(account());t=trade();store.trade(t);store.link_trade(link(t,d));return d,t


def test_empty_and_unlinked_trade_not_review_debt(store):
    store.add_account(account());store.trade(trade())
    data=workspace(store);assert data['candidates']==[] and data['reviews']==[] and data['performance_score'] is None


def test_review_without_trades_and_pending_result(store):
    store.save_document(document('decision'));r=save_review(store,review(store))
    assert r['evidence']['trades']==[] and r['outcome_note']=='' and r['outcome_status']=='pending'
    assert store.documents()['documents'][0]['kind']=='decision'
    assert all(v['kind']!='review' for v in store.documents()['versions'])


def test_frozen_snapshot_after_edit_unlink_delete_and_review_revision(store):
    d,t=seed(store);body=review(store);saved=save_review(store,body)
    assert saved['evidence']['trades'][0]['quantity']=='10'
    store.trade(t|{'revision':1,'quantity':'12','operation_id':str(uuid.uuid4())})
    view=workspace(store);assert view['reviews'][0]['evidence_changed'] is True
    newer=save_review(store,body|{'revision':1,'operation_id':str(uuid.uuid4()),'process_status':'deviated','outcome_status':'observed','outcome_note':'Positive outcome does not erase deviation'})
    assert newer['evidence']==saved['evidence'] and newer['process_status']=='deviated'
    store.link_trade(link(t,d,trade_revision=2,revision=1,decision_id=None,decision_revision=None))
    store.trade({'id':t['id'],'revision':2,'operation_id':str(uuid.uuid4())},delete=True)
    assert workspace(store)['reviews'][0]['evidence']['trades'][0]['quantity']=='10'
    assert len(workspace(store)['versions'])==2


def test_stale_evidence_rejected_atomically(store):
    d,t=seed(store);body=review(store)
    store.link_trade(link(t,d,revision=1,decision_id=None,decision_revision=None))
    with pytest.raises(Conflict):save_review(store,body)
    assert workspace(store)['reviews']==[]
    with store.connection() as db:assert db.execute('SELECT 1 FROM operations WHERE id=?',(body['operation_id'],)).fetchone() is None


def test_idempotency_conflicts_and_reference_cannot_change(store):
    seed(store);body=review(store);r=save_review(store,body);assert save_review(store,body)==r
    with pytest.raises(Conflict):save_review(store,body|{'next_step':'changed'})
    with pytest.raises(Conflict):save_review(store,body|{'operation_id':str(uuid.uuid4())})
    with pytest.raises(Conflict):save_review(store,body|{'revision':1,'operation_id':str(uuid.uuid4()),'expected_evidence':'0'*64})
    with pytest.raises(Conflict):save_review(store,body|{'revision':1,'operation_id':str(uuid.uuid4()),'decision_ref':{'id':'different-ref','revision':1}})

@pytest.mark.parametrize('change',[{'process_status':'scored'},{'outcome_status':'profit'},{'outcome_status':'observed','outcome_note':''},{'process_note':''},{'next_step':''},{'reviewed_on':'2026-02-30'},{'reviewed_on':'tomorrow'},{'revision':True},{'expected_evidence':'not-a-hash'},{'workspace':'other'},{'process_note':'x'*20001}])
def test_input_validation(store,change):
    seed(store)
    with pytest.raises(ValueError):save_review(store,review(store,**change))
    assert workspace(store)['reviews']==[]


def test_wrong_ref_and_review_id_collision(store):
    seed(store);note=store.documents()['documents'];n=next(d for d in note if d['kind']=='note')
    with pytest.raises(ValueError):save_review(store,review(store,decision_ref={'id':n['id'],'revision':1}))
    with pytest.raises(Conflict):save_review(store,review(store,id=n['id'],revision=1))


def test_archived_decision_can_be_reviewed_and_review_archive_preserves_versions(store):
    d,t=seed(store);store.save_document({'id':d['id'],'revision':1,'operation_id':str(uuid.uuid4())},archive=True)
    body=review(store);r=save_review(store,body)
    assert workspace(store)['candidates'][0]['decision_archived'] is True
    a={'id':r['id'],'revision':1,'operation_id':str(uuid.uuid4())};archived=save_review(store,a,archive=True)
    assert archived['archived'] and save_review(store,a,archive=True)==archived
    with pytest.raises(Conflict):save_review(store,body|{'revision':2,'operation_id':str(uuid.uuid4())})
    with pytest.raises(ValueError):store.save_document({'id':r['id'],'revision':2,'operation_id':str(uuid.uuid4())},archive=True)
    assert workspace(store)['versions'][0]['evidence']==r['evidence']


def test_restart_and_backup_include_review_history(store,tmp_path):
    seed(store);save_review(store,review(store));before=workspace(store)
    assert workspace(OwnerStore(store.directory))==before
    b=store.backup();dest=tmp_path.resolve()/'restore-review';restore_owner(store.directory/'backups'/b['name'],dest)
    assert workspace(OwnerStore(dest))==before


def test_evolve_auth_csrf_and_api(app):
    assert request(app,'/api/v1/owner/evolve')['status']==401
    seed(app.store);auth=login(app);body=review(app.store)
    assert request(app,'/api/v1/owner/evolve','POST',body,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/evolve','POST',body,**auth)['status']==200
    assert request(app,'/api/v1/owner/evolve',**auth)['body']['reviews'][0]['outcome_status']=='pending'
    assert request(app,'/api/v1/owner/evolve','POST',body|{'workspace':'other'},**auth)['status']==400
