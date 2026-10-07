import json
import uuid
import pytest
from awesome_stock.storage.owner_transfer import preview,commit,export_data,COLUMNS
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import OwnerStore,restore_owner
from test_owner_store import account,trade,store
from test_owner_api import request,login,app

HEADER=','.join(COLUMNS)+'\n'
BUY='fill-1,TEST,buy,10,10,1,2026-01-01T00:00:00Z\n'
SELL='fill-2,TEST,sell,4,15,1,2026-01-02T00:00:00Z\n'

def body(csv=BUY,account_id='account-test'):
    return {'account_id':account_id,'csv':HEADER+csv}

def confirm(store,b,p=None,**changes):
    p=p or preview(store,b)
    return commit(store,{**b,'preview_token':p['preview_token'],'operation_id':str(uuid.uuid4()),**changes})


def test_preview_exact_cash_cost_no_write_and_atomic_import(store):
    store.add_account(account());before=store.path.read_bytes();b=body(BUY+SELL)
    p=preview(store,b)
    assert store.path.read_bytes()==before
    assert p['before']['cash']=='1000' and p['after']['cash']=='958'
    assert p['after']['holdings'][0]['open_cost']=='60.6'
    assert p['after']['holdings'][0]['realized_pnl']=='18.6'
    r=confirm(store,b,p)
    assert r['imported']==2 and r['account']==p['after']
    with store.connection() as db:assert db.execute("SELECT count(*) FROM audit WHERE action='trade_saved'").fetchone()[0]==2


def test_idempotent_retry_conflict_and_duplicate_import(store):
    store.add_account(account());b=body(BUY+BUY);p=preview(store,b)
    assert p['new_count']==1 and p['duplicate_count']==1
    op=str(uuid.uuid4());r=confirm(store,b,p,operation_id=op)
    assert confirm(store,b,p,operation_id=op)==r
    with pytest.raises(Conflict):confirm(store,body(SELL),p,operation_id=op)
    p=preview(store,body(BUY));assert p['new_count']==0 and p['duplicate_count']==1
    assert confirm(store,body(BUY),p)['imported']==0
    assert len(store.ledger()['accounts'][0]['trades'])==1


@pytest.mark.parametrize('csv',[BUY+BUY.replace(',10,10,',',11,10,'),BUY+'bad,row\n',SELL+BUY.replace('2026-01-01','2026-01-03'),BUY.replace(',10,10,',',1000,10,'),BUY.replace('T00:00:00Z','T00:00:00'),BUY.replace(',10,10,',',1e1,10,'),BUY.replace(',10,10,',',=10,10,'),'',BUY*201])
def test_invalid_rows_conflicts_and_chronological_failure_leave_no_writes(store,csv):
    store.add_account(account());before=store.path.read_bytes();b=body(csv);p=preview(store,b)
    assert p['can_import'] is False
    assert store.path.read_bytes()==before
    with pytest.raises(ValueError):confirm(store,b,p)
    assert store.path.read_bytes()==before


def test_stale_preview_rejected_but_new_preview_allowed(store):
    store.add_account(account());b=body();p=preview(store,b)
    store.trade(trade(quantity='1',fee='0'))
    before=store.ledger()
    with pytest.raises(Conflict):confirm(store,b,p)
    assert store.ledger()==before
    assert confirm(store,b)['imported']==1


def test_imported_trade_edit_and_delete_protected_from_old_csv(store):
    store.add_account(account());b=body();r=confirm(store,b);t=r['account']['trades'][0]
    store.trade({k:v for k,v in t.items() if k not in ('sequence','event_order')}|{'operation_id':str(uuid.uuid4()),'quantity':'11'})
    assert preview(store,b)['rows'][0]['status']=='conflict'
    store.trade({'id':t['id'],'revision':2,'operation_id':str(uuid.uuid4())},delete=True)
    assert preview(store,b)['rows'][0]['status']=='conflict'
    assert preview(store,b)['can_import'] is False


def test_cross_account_identity_decimal_timezone_and_possible_duplicate(store):
    store.add_account(account());store.add_account(account(id='account-two',currency='HKD'))
    r=confirm(store,body());assert confirm(store,body(account_id='account-two'))['imported']==1
    same=BUY.replace(',10,10,1,',',10.0,10.00,1.00,').replace('2026-01-01T00:00:00Z','2026-01-01T08:00:00+08:00')
    assert preview(store,body(same))['duplicate_count']==1
    p=preview(store,body(BUY.replace('fill-1','fill-new')))
    assert p['rows'][0]['possible_duplicate'] and p['can_import']


def test_same_timestamp_existing_then_csv_and_injected_commit_rollback(store,monkeypatch):
    store.add_account(account());b=body(BUY+SELL.replace('2026-01-02','2026-01-01'))
    p=preview(store,b);assert p['after']['cash']=='958'
    original=store._audit
    def fail(db,action,*args):
        if action=='csv_imported':raise OSError('simulated disk failure')
        return original(db,action,*args)
    monkeypatch.setattr(store,'_audit',fail)
    with pytest.raises(OSError):confirm(store,b,p)
    assert store.ledger()['accounts'][0]['trades']==[]
    monkeypatch.setattr(store,'_audit',original)
    assert confirm(store,b,p)['imported']==2


def test_restart_restore_and_export_no_credentials(store,tmp_path):
    store.add_account(account());confirm(store,body(BUY+SELL))
    data=export_data(store)
    assert set(data)=={'format','format_version','exported_at','accounts','documents','document_versions','trade_links','cash_flow_versions','restores_account'}
    assert data['accounts'][0]['cash']=='958' and data['restores_account'] is False
    assert store.owner().credential.digest_hex not in json.dumps(data)
    backup=store.backup();destination=tmp_path/'restored-owner'
    restore_owner(store.directory/'backups'/backup['name'],destination)
    restored=OwnerStore(destination)
    assert preview(restored,body(BUY+SELL))['duplicate_count']==2
    for item in (restored,OwnerStore(store.directory)):
        exported=export_data(item);exported.pop('exported_at');expected=dict(data);expected.pop('exported_at');assert exported==expected


def test_api_auth_csrf_and_exports(app):
    assert request(app,'/api/v1/owner/export')['status']==401
    auth=login(app);app.store.add_account(account());b=body()
    assert request(app,'/api/v1/owner/import-preview','POST',b,**(auth|{'csrf':'bad'}))['status']==403
    p=request(app,'/api/v1/owner/import-preview','POST',b,**auth)['body']
    c={**b,'preview_token':p['preview_token'],'operation_id':str(uuid.uuid4())}
    assert request(app,'/api/v1/owner/import-confirm','POST',c,**(auth|{'csrf':'bad'}))['status']==403
    assert app.store.ledger()['accounts'][0]['trades']==[]
    assert request(app,'/api/v1/owner/import-confirm','POST',c,**auth)['body']['imported']==1
    assert request(app,'/api/v1/owner/export',**auth)['body']['accounts'][0]['cash']=='899'


def test_bounds_unknown_fields_and_utf8_bom(store):
    store.add_account(account())
    assert preview(store,{'account_id':'account-test','csv':'\ufeff'+HEADER+BUY})['can_import']
    for b in [body()|{'extra':1},body(account_id='unknown-account'),body('a'*32769),body()|{'csv':None}]:
        with pytest.raises(ValueError):preview(store,b)


def test_competing_commits_only_one_batch_writes(store):
    from concurrent.futures import ThreadPoolExecutor
    store.add_account(account());b=body();p=preview(store,b)
    def attempt(_):
        try:return confirm(store,b,p)['imported']
        except Conflict:return 'stale'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    assert sorted(map(str,results))==['1','stale']
    assert len(store.ledger()['accounts'][0]['trades'])==1


def test_export_keeps_all_document_kinds_and_pinned_history(store):
    from test_research_store import document,link
    from test_owner_plan import plan
    from test_owner_evolve import review
    from awesome_stock.storage.owner_plan import save_plan
    from awesome_stock.storage.owner_evolve import save_review
    note=document();n=store.save_document(note)
    d=store.save_document(document('decision',research_ref={'id':n['id'],'revision':1}))
    store.add_account(account());t=confirm(store,body())['account']['trades'][0];store.link_trade(link(t,d))
    p=save_plan(store,plan(d));r=save_review(store,review(store))
    store.save_document(note|{'revision':1,'operation_id':str(uuid.uuid4()),'content':'Changed note'})
    out=export_data(store)
    assert {d['kind'] for d in out['documents']}=={'note','decision','plan','review'}
    assert len(out['document_versions'])==5
    assert out['trade_links'][0]['decision_revision']==1
    assert next(x for x in out['documents'] if x['id']==p['id'])['evidence']==p['evidence']
    assert next(x for x in out['documents'] if x['id']==r['id'])['evidence']==r['evidence']
    assert next(x for x in out['document_versions'] if x['id']==n['id'] and x['revision']==1)['content']=='Original reasoning'
