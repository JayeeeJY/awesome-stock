import json
import sqlite3
import uuid
import pytest
from awesome_stock.storage.owner import OwnerStore,restore_owner,check_owner
from awesome_stock.storage.local import Conflict
from test_owner_store import store,account,trade,PASSWORD


def document(kind='note',**changes):
    return {'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4()),'revision':0,'kind':kind,'title':'Synthetic note','symbol':'TEST','content':'Original reasoning','support':'Supporting evidence' if kind=='decision' else '', 'counter_case':'Counter evidence' if kind=='decision' else '', 'invalidation':'Invalid if premise breaks' if kind=='decision' else '', 'risk_limit':'Manual risk budget' if kind=='decision' else '', 'review_on':'2026-10-01' if kind=='decision' else '', 'research_ref':None}|changes


def link(t,d,**changes):
    return {'trade_id':t['id'],'trade_revision':1,'operation_id':str(uuid.uuid4()),'revision':0,'decision_id':d['id'],'decision_revision':d['revision']}|changes


def test_versioned_chain_survives_edits_archive_and_restart(store):
    note=document();n=store.save_document(note)
    decision=document('decision',research_ref={'id':n['id'],'revision':1});d=store.save_document(decision)
    store.add_account(account());t=trade();store.trade(t);l=link(t,d);store.link_trade(l)
    store.save_document(note|{'revision':1,'content':'New reasoning','operation_id':str(uuid.uuid4())})
    store.save_document(decision|{'revision':1,'content':'New decision','operation_id':str(uuid.uuid4())})
    out=OwnerStore(store.directory).documents();assert out['links'][0]['decision_revision']==1
    pinned=next(v for v in out['versions'] if v['id']==d['id'] and v['revision']==1)
    assert pinned['content']=='Original reasoning' and pinned['research_ref']=={'id':n['id'],'revision':1}
    store.save_document({'id':n['id'],'revision':2,'operation_id':str(uuid.uuid4())},archive=True)
    store.save_document({'id':d['id'],'revision':2,'operation_id':str(uuid.uuid4())},archive=True)
    assert store.documents()['links'][0]['decision_revision']==1
    with pytest.raises(ValueError):store.link_trade(l|{'operation_id':str(uuid.uuid4()),'revision':1})
    with pytest.raises(Conflict):store.save_document(note|{'revision':3,'operation_id':str(uuid.uuid4())})


def test_idempotency_conflict_and_immutable_kind(store):
    body=document();first=store.save_document(body);assert store.save_document(body)==first
    with pytest.raises(Conflict):store.save_document(body|{'content':'different'})
    with pytest.raises(Conflict):store.save_document(body|{'operation_id':str(uuid.uuid4())})
    with pytest.raises(ValueError):store.save_document(document('decision',id=body['id'],revision=1))
    assert len(store.documents()['versions'])==1

@pytest.mark.parametrize('changes',[{'support':''},{'counter_case':''},{'invalidation':''},{'risk_limit':''},{'review_on':'bad'},{'review_on':'2026-02-30'},{'revision':True},{'symbol':'<script>'},{'workspace':'other'},{'content':'x'*20001},{'research_ref':{'id':'missing-doc','revision':1}}])
def test_invalid_decision_does_not_write(store,changes):
    with pytest.raises(ValueError):store.save_document(document('decision',**changes))
    assert store.documents()['documents']==[]


def test_wrong_symbol_and_wrong_kind_references_rejected(store):
    n=store.save_document(document(symbol='OTHER'))
    with pytest.raises(ValueError):store.save_document(document('decision',research_ref={'id':n['id'],'revision':1}))
    d=store.save_document(document('decision'))
    with pytest.raises(ValueError):store.save_document(document('decision',research_ref={'id':d['id'],'revision':1}))
    store.add_account(account());t=trade(symbol='OTHER');store.trade(t)
    with pytest.raises(ValueError):store.link_trade(link(t,d))
    with pytest.raises(ValueError):store.link_trade(link(t,n))
    assert store.documents()['links']==[]


def test_link_conflicts_clear_relink_and_trade_guard(store):
    d=store.save_document(document('decision'));store.add_account(account());t=trade();store.trade(t)
    l=link(t,d);assert store.link_trade(l)==store.link_trade(l)
    with pytest.raises(Conflict):store.link_trade(l|{'operation_id':str(uuid.uuid4())})
    with pytest.raises(Conflict):store.link_trade(link(t,d,revision=1,trade_revision=2))
    with pytest.raises(ValueError):store.trade(t|{'symbol':'OTHER','revision':1,'operation_id':str(uuid.uuid4())})
    store.link_trade(link(t,d,revision=1,decision_id=None,decision_revision=None))
    with pytest.raises(Conflict):store.link_trade(link(t,d))
    store.link_trade(link(t,d,revision=2))
    store.trade({'id':t['id'],'revision':1,'operation_id':str(uuid.uuid4())},delete=True)
    assert store.documents()['links']==[] and len(store.documents()['documents'])==1


def test_failed_trade_delete_rolls_back_link(store):
    d=store.save_document(document('decision'));store.add_account(account());t=trade();store.trade(t);store.link_trade(link(t,d));store.trade(trade(side='sell',quantity='5',executed_at='2026-01-02T00:00:00Z'))
    before=store.documents()
    with pytest.raises(ValueError):store.trade({'id':t['id'],'revision':1,'operation_id':str(uuid.uuid4())},delete=True)
    assert store.documents()==before


def make_v1(store):
    with store.transaction() as db:
        for name in ['documents','document_versions','trade_links','cash_flows','cash_flow_versions','ledger_events']:db.execute('DROP TABLE '+name)
        db.execute('ALTER TABLE accounts DROP COLUMN broker');db.execute('ALTER TABLE accounts DROP COLUMN revision')
        db.execute('ALTER TABLE accounts DROP COLUMN cost_method')
        db.execute('PRAGMA user_version=1')


def test_upgrade_v1_with_prebackup_restore_and_credentials(store,tmp_path):
    store.add_account(account());store.trade(trade());before=store.ledger();make_v1(store)
    upgraded=OwnerStore(store.directory);assert upgraded.ledger()==before
    assert upgraded.owner().credential==store.owner().credential
    backups=list((store.directory/'backups').iterdir());assert len(backups)==1
    assert json.loads((backups[0]/'manifest.json').read_text())['schema_version']==1
    target=tmp_path.resolve()/'restored';restore_owner(backups[0],target)
    with sqlite3.connect(target/'owner.sqlite3') as db:check_owner(db,1)
    assert OwnerStore(target).ledger()==before
    OwnerStore(store.directory);assert len(list((store.directory/'backups').iterdir()))==1


def test_upgrade_failure_keeps_v1_and_backup(store,monkeypatch):
    make_v1(store)
    def fail(db):db.execute('CREATE TABLE temporary_upgrade(x)');raise RuntimeError('synthetic failure')
    monkeypatch.setattr('awesome_stock.storage.owner.add_research_tables',fail)
    with pytest.raises(RuntimeError):OwnerStore(store.directory)
    with store.connection() as db:
        check_owner(db,1)
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='temporary_upgrade'").fetchone()
    assert len(list((store.directory/'backups').iterdir()))==1


def test_backup_failure_prevents_upgrade(store,monkeypatch):
    make_v1(store)
    def fail(*args):raise OSError('synthetic backup failure')
    monkeypatch.setattr('awesome_stock.storage.local.LocalStore.backup',fail)
    with pytest.raises(OSError):OwnerStore(store.directory)
    with store.connection() as db:check_owner(db,1)


def test_current_backup_restores_history_and_links(store,tmp_path):
    n=store.save_document(document());d=store.save_document(document('decision',research_ref={'id':n['id'],'revision':1}))
    store.add_account(account());t=trade();store.trade(t);store.link_trade(link(t,d));before=store.documents()
    b=store.backup();assert b['schema_version']==5
    dest=tmp_path.resolve()/'restored';restore_owner(store.directory/'backups'/b['name'],dest)
    assert OwnerStore(dest).documents()==before
