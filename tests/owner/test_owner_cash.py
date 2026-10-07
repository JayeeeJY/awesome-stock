from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import uuid
import pytest
from awesome_stock.storage.owner import OwnerStore,LedgerInvalid,check_owner,restore_owner
from awesome_stock.storage.owner_cash import save,history
from awesome_stock.storage.owner_transfer import preview,commit,export_data
from awesome_stock.storage.local import Conflict
from test_owner_store import store,account,trade
from test_owner_api import app,login,request
from test_owner_transfer import body as csv_body,BUY,confirm
from test_research_store import document


def cash(**changes):
    return {'id':str(uuid.uuid4()),'revision':0,'operation_id':str(uuid.uuid4()),'account_id':'account-test','direction':'deposit','amount':'1000','occurred_at':'2026-01-01T00:00:00Z','note':'Synthetic deposit'}|changes


def test_deposit_trade_withdrawal_reconciliation_and_no_profit_change(store):
    store.add_account(account(opening_cash='0'));save(store,cash());store.trade(trade());store.trade(trade(side='sell',quantity='4',price='15',executed_at='2026-01-02T00:00:00Z'))
    before=store.ledger()['accounts'][0]
    save(store,cash(direction='withdrawal',amount='100',occurred_at='2026-01-03T00:00:00Z'))
    a=store.ledger()['accounts'][0]
    assert a['cash']=='858' and a['deposits']=='1000' and a['withdrawals']=='100' and a['trade_cash_change']=='-42'
    assert a['holdings']==before['holdings'] and a['holdings'][0]['realized_pnl']=='18.6'
    assert a['cash_flow_net']=='900'


def test_cash_order_same_time_and_edit_preserves_first_order(store):
    store.add_account(account(opening_cash='100'));t=trade(quantity='1',price='100',fee='0');store.trade(t)
    with pytest.raises(LedgerInvalid):save(store,cash(direction='withdrawal',amount='1',occurred_at=t['executed_at']))
    b=cash(amount='20',occurred_at=t['executed_at']);r=save(store,b)
    out=save(store,cash(direction='withdrawal',amount='20',occurred_at=t['executed_at']))
    assert t['id']==store.ledger()['accounts'][0]['trades'][0]['id']
    assert r['event_order']<out['event_order']
    changed=save(store,b|{'revision':1,'operation_id':str(uuid.uuid4()),'note':'Edited'})
    assert changed['event_order']==r['event_order']
    assert store.ledger()['accounts'][0]['cash']=='0'


@pytest.mark.parametrize('change',[{'amount':'50'},{'occurred_at':'2026-01-03T00:00:00Z'},{'direction':'withdrawal'}])
def test_edit_funding_deposit_cannot_make_old_trade_insolvent(store,change):
    store.add_account(account(opening_cash='0'));b=cash();save(store,b);store.trade(trade())
    before=store.ledger();versions=history(store)
    with pytest.raises(LedgerInvalid):save(store,b|{'revision':1,'operation_id':str(uuid.uuid4())}|change)
    assert store.ledger()==before and history(store)==versions


def test_delete_funding_rejected_withdrawal_delete_keeps_history(store):
    store.add_account(account(opening_cash='0'));b=cash();save(store,b);store.trade(trade())
    with pytest.raises(LedgerInvalid):save(store,{'id':b['id'],'revision':1,'operation_id':str(uuid.uuid4())},delete=True)
    w=cash(direction='withdrawal',amount='100',occurred_at='2026-01-02T00:00:00Z');save(store,w)
    cmd={'id':w['id'],'revision':1,'operation_id':str(uuid.uuid4())};r=save(store,cmd,delete=True)
    assert save(store,cmd,delete=True)==r and r['deleted']
    assert store.ledger()['accounts'][0]['cash']=='899'
    assert len(history(store)['versions'])==3
    with pytest.raises(Conflict):save(store,w|{'operation_id':str(uuid.uuid4())})


def test_later_deposit_does_not_mask_historical_overspend(store):
    store.add_account(account(opening_cash='0'));save(store,cash(occurred_at='2026-01-03T00:00:00Z'))
    with pytest.raises(LedgerInvalid):store.trade(trade())
    assert store.ledger()['accounts'][0]['trades']==[]


def test_trade_delete_cannot_remove_sale_funding_withdrawal(store):
    store.add_account(account(opening_cash='101'));store.trade(trade());s=trade(side='sell',price='20',executed_at='2026-01-02T00:00:00Z');store.trade(s)
    save(store,cash(direction='withdrawal',amount='199',occurred_at='2026-01-03T00:00:00Z'))
    with pytest.raises(LedgerInvalid):store.trade({'id':s['id'],'revision':1,'operation_id':str(uuid.uuid4())},delete=True)
    assert store.ledger()['accounts'][0]['cash']=='0'


@pytest.mark.parametrize('change',[{'amount':'0'},{'amount':'-1'},{'amount':'1e3'},{'amount':'1.000000001'},{'direction':'transfer'},{'occurred_at':'2026-01-01T00:00:00'},{'note':'x'*1001},{'revision':True},{'account_id':'unknown-account'},{'workspace':'other'}])
def test_bad_cash_input_no_write(store,change):
    store.add_account(account());before=store.path.read_bytes()
    with pytest.raises(ValueError):save(store,cash(**change))
    assert store.path.read_bytes()==before


def test_cross_currency_account_isolation_and_fixed_account(store):
    store.add_account(account(opening_cash='0'));store.add_account(account(id='account-hkd',currency='HKD',opening_cash='0'))
    b=cash();r=save(store,b)
    with pytest.raises(LedgerInvalid):save(store,cash(account_id='account-hkd',direction='withdrawal',amount='1'))
    with pytest.raises(ValueError):save(store,b|{'account_id':'account-hkd','revision':1,'operation_id':str(uuid.uuid4())})
    balances={a['currency']:a['cash'] for a in store.ledger()['accounts']};assert balances=={'USD':'1000','HKD':'0'}


def test_idempotency_revision_and_competing_withdrawals(store):
    store.add_account(account());b=cash(direction='withdrawal',amount='600');r=save(store,b);assert save(store,b)==r
    with pytest.raises(Conflict):save(store,b|{'amount':'601'})
    with pytest.raises(Conflict):save(store,b|{'operation_id':str(uuid.uuid4())})
    def attempt(_):
        try:return save(store,cash(direction='withdrawal',amount='300'))['amount']
        except LedgerInvalid:return 'blocked'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    assert sorted(results)==['300','blocked'] and store.ledger()['accounts'][0]['cash']=='100'


def test_csv_includes_cash_and_invalidates_stale_preview(store):
    store.add_account(account(opening_cash='0'));save(store,cash(occurred_at='2025-12-31T00:00:00Z'))
    b=csv_body();p=preview(store,b);assert p['after']['cash']=='899'
    save(store,cash(amount='100',occurred_at='2025-12-31T00:00:00Z'))
    with pytest.raises(Conflict):confirm(store,b,p)
    r=confirm(store,b);assert r['account']['cash']=='999'
    assert r['account']['trades'][0]['event_order']==3


def make_v2(store):
    with store.transaction() as db:
        for name in ['cash_flows','cash_flow_versions','ledger_events']:db.execute('DROP TABLE '+name)
        db.execute('ALTER TABLE accounts DROP COLUMN broker');db.execute('ALTER TABLE accounts DROP COLUMN revision')
        db.execute('ALTER TABLE accounts DROP COLUMN cost_method')
        db.execute('PRAGMA user_version=2')


def test_v2_migration_backup_history_restore_and_export(store,tmp_path):
    store.add_account(account());store.trade(trade());n=store.save_document(document());before=store.ledger();creds=store.owner().credential
    make_v2(store);upgraded=OwnerStore(store.directory)
    assert upgraded.ledger()==before and upgraded.owner().credential==creds
    backups=list((store.directory/'backups').iterdir());assert len(backups)==1
    assert json.loads((backups[0]/'manifest.json').read_text())['schema_version']==2
    with sqlite3.connect(backups[0]/'owner.sqlite3') as db:
        check_owner(db,2);assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='cash_flows'").fetchone()
    save(upgraded,cash(amount='100',occurred_at='2026-01-02T00:00:00Z'))
    exported=export_data(upgraded);assert exported['format_version']==2 and len(exported['cash_flow_versions'])==1
    assert exported['documents'][0]['id']==n['id'] and exported['accounts'][0]['cash']=='999'
    b=upgraded.backup();target=tmp_path/'cash-restored';restore_owner(upgraded.directory/'backups'/b['name'],target)
    restored=OwnerStore(target);assert restored.ledger()==upgraded.ledger() and history(restored)==history(upgraded)
    rollback=tmp_path/'old-schema';restore_owner(backups[0],rollback)
    with sqlite3.connect(rollback/'owner.sqlite3') as db:check_owner(db,2)
    assert OwnerStore(rollback).ledger()==before
    assert OwnerStore(store.directory).ledger()==upgraded.ledger()


@pytest.mark.parametrize('stage',['backup','migration'])
def test_v2_upgrade_failure_is_recoverable(store,monkeypatch,stage):
    store.add_account(account());store.trade(trade());make_v2(store)
    def fail(*args):
        if stage=='migration':args[0].execute('CREATE TABLE cash_flows(temporary INTEGER)')
        raise OSError('synthetic upgrade failure')
    if stage=='backup':monkeypatch.setattr('awesome_stock.storage.local.LocalStore.backup',fail)
    else:monkeypatch.setattr('awesome_stock.storage.owner.add_cash_tables',fail)
    with pytest.raises(OSError):OwnerStore(store.directory)
    with store.connection() as db:
        check_owner(db,2);assert db.execute('SELECT count(*) FROM trades').fetchone()[0]==1
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='cash_flows'").fetchone()


def test_cash_api_requires_auth_csrf_and_returns_history(app):
    url='/api/v1/owner/cash-flows';assert request(app,url)['status']==401
    app.store.add_account(account());auth=login(app);b=cash()
    assert request(app,url,'POST',b,**(auth|{'csrf':'bad'}))['status']==403
    assert request(app,url,'POST',b,**auth)['status']==200
    assert request(app,url,**auth)['body']['executes_transfers'] is False
    assert len(request(app,url,**auth)['body']['versions'])==1


def test_concurrent_v2_upgrade_one_backup_and_order_preserved(store):
    store.add_account(account());store.trade(trade());store.trade(trade(quantity='1'))
    expected=store.ledger();make_v2(store)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:OwnerStore(store.directory).ledger(),range(2)))
    assert results==[expected,expected]
    assert len(list((store.directory/'backups').iterdir()))==1
