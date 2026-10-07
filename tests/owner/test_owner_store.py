from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
import stat
import uuid
import pytest
from awesome_stock.storage.owner import OwnerStore, LedgerInvalid, restore_owner
from awesome_stock.storage.local import LocalStore, Conflict, restore
from awesome_stock.security.auth import authenticate, AuthenticationError

PASSWORD='Synthetic-test-only-2026'

def account(**changes):
    return dict(id='account-test',operation_id=str(uuid.uuid4()),name='Synthetic',currency='USD',opening_cash='1000',**{}) | changes

def trade(**changes):
    return dict(id=str(uuid.uuid4()),operation_id=str(uuid.uuid4()),revision=0,account_id='account-test',symbol='TEST',side='buy',quantity='10',price='10',fee='1',executed_at='2026-01-01T12:00:00Z') | changes

@pytest.fixture
def store(tmp_path):
    obj=OwnerStore(tmp_path.resolve()/'owner');obj.setup('Tester',PASSWORD);return obj

def snapshot(store):
    with store.connection() as db:
        return {name:db.execute('SELECT * FROM '+name).fetchall() for name in ['accounts','trades','operations','audit']}

def test_empty_persistent_owner_and_no_password_plaintext(store):
    assert store.ledger()['accounts']==[]
    again=OwnerStore(store.directory)
    assert again.owner().username=='tester'
    authenticate(again.owner(),PASSWORD)
    with pytest.raises(AuthenticationError):authenticate(again.owner(),'wrong')
    assert PASSWORD.encode() not in store.path.read_bytes()
    with pytest.raises(Conflict):store.setup('other',PASSWORD)
    assert stat.S_IMODE(store.path.stat().st_mode)==0o600
    assert stat.S_IMODE(store.directory.stat().st_mode)==0o700

@pytest.mark.parametrize('username,password',[('a',PASSWORD),('中文',PASSWORD),(' a b ',PASSWORD),('tester','short'),('tester','x'*129)])
def test_setup_invalid(tmp_path,username,password):
    s=OwnerStore(tmp_path.resolve()/'data')
    with pytest.raises(ValueError):s.setup(username,password)
    assert s.owner() is None

def test_concurrent_setup_one_owner(tmp_path):
    s=OwnerStore(tmp_path.resolve()/'data')
    def setup(name):
        try:s.setup(name,PASSWORD);return True
        except Conflict:return False
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(setup,['owner-one','owner-two']))==[False,True]

def test_password_change_invalidates_expected_digest_and_no_audit_secret(store):
    old=store.owner().credential.digest_hex;new='Synthetic-new-password-2026'
    store.change_password(new,old);authenticate(OwnerStore(store.directory).owner(),new)
    with pytest.raises(Conflict):store.change_password(PASSWORD,old)
    with store.connection() as db:audit=str(db.execute('SELECT * FROM audit').fetchall())
    assert new not in audit and old not in audit

@pytest.mark.parametrize('value',['NaN','Infinity','1e3','-1','01','0.123456789','1000000000000',1,1.2,None,True])
def test_account_decimal_rejected_without_mutation(store,value):
    before=snapshot(store)
    with pytest.raises(ValueError):store.add_account(account(opening_cash=value))
    assert snapshot(store)==before

def test_account_idempotency_currency_and_strict_fields(store):
    a=account();assert store.add_account(a)==store.add_account(a)
    with pytest.raises(Conflict):store.add_account(a|{'name':'changed'})
    for b in [account(currency='BAD'),account(workspace='spoof'),account(name='\0'),account(id='../bad/path')]:
        with pytest.raises(ValueError):store.add_account(b)
    assert len(store.ledger()['accounts'])==1

def test_cash_holdings_sell_edit_and_delete(store):
    store.add_account(account());buy=trade();store.trade(buy)
    sell=trade(side='sell',quantity='4',price='15',executed_at='2026-01-02T12:00:00Z');result=store.trade(sell)
    a=store.ledger()['accounts'][0];h=a['holdings'][0]
    assert Decimal(a['cash'])==958
    assert [Decimal(h[k]) for k in ['quantity','open_cost','realized_pnl']]==[6,Decimal('60.6'),Decimal('18.6')]
    assert h['market_value'] is None and h['unrealized_pnl'] is None
    updated=sell|{'revision':result['revision'],'quantity':'2','operation_id':str(uuid.uuid4())};store.trade(updated)
    a=store.ledger()['accounts'][0];assert Decimal(a['cash'])==928
    assert Decimal(a['holdings'][0]['open_cost'])==Decimal('80.8')
    store.trade({'id':sell['id'],'revision':2,'operation_id':str(uuid.uuid4())},delete=True)
    assert Decimal(store.ledger()['accounts'][0]['cash'])==899
    with pytest.raises(Conflict):store.trade(sell|{'operation_id':str(uuid.uuid4())})

@pytest.mark.parametrize('change',[{'side':'sell'},{'quantity':'100'},{'price':'1000'},{'side':'sell','fee':'2000'}])
def test_invalid_trade_rolls_back_all_tables(store,change):
    store.add_account(account());before=snapshot(store)
    with pytest.raises(LedgerInvalid):store.trade(trade(**change))
    assert snapshot(store)==before

def test_backfill_edit_delete_and_stale_revision_rollback(store):
    store.add_account(account());buy=trade();store.trade(buy)
    sell=trade(side='sell',quantity='10',price='20',executed_at='2026-01-02T12:00:00Z');store.trade(sell)
    before=snapshot(store)
    for body,delete in [(buy|{'revision':1,'quantity':'9','operation_id':str(uuid.uuid4())},False),({'id':buy['id'],'revision':1,'operation_id':str(uuid.uuid4())},True),(trade(side='sell',quantity='1',executed_at='2025-12-31T00:00:00Z'),False)]:
        with pytest.raises(LedgerInvalid):store.trade(body,delete=delete)
        assert snapshot(store)==before
    with pytest.raises(Conflict):store.trade(buy|{'operation_id':str(uuid.uuid4())})
    assert snapshot(store)==before

def test_equal_time_order_and_idempotent_trade(store):
    store.add_account(account());buy=trade();assert store.trade(buy)==store.trade(buy)
    sell=trade(side='sell',quantity='10',price='20',executed_at='2026-01-01T20:00:00+08:00');store.trade(sell)
    store.trade(buy|{'revision':1,'fee':'2','operation_id':str(uuid.uuid4())})
    a=store.ledger()['accounts'][0];assert [t['id'] for t in a['trades']]==[buy['id'],sell['id']]
    assert Decimal(a['cash'])==1097 and Decimal(a['holdings'][0]['quantity'])==0
    assert Decimal(a['holdings'][0]['realized_pnl'])==97

@pytest.mark.parametrize('change',[{'revision':True},{'revision':-1},{'executed_at':'2026-01-01T12:00:00'},{'executed_at':'not-a-date'},{'quantity':'0'},{'fee':'-1'},{'price':1},{'symbol':'<img>'},{'account_id':'unknown-test'},{'side':[]}])
def test_trade_input_validation(store,change):
    store.add_account(account());before=snapshot(store)
    with pytest.raises(ValueError):store.trade(trade(**change))
    assert snapshot(store)==before

def test_account_isolation_and_fractional_precision(store):
    store.add_account(account());store.add_account(account(id='account-other',currency='CNY'))
    store.trade(trade(quantity='0.00000001',price='0.00000001',fee='0'))
    store.trade(trade(account_id='account-other',quantity='2',price='3',fee='0'))
    out=store.ledger();items={a['id']:a for a in out['accounts']}
    assert Decimal(items['account-test']['cash'])==Decimal('999.9999999999999999')
    assert Decimal(items['account-other']['cash'])==994
    assert out['cross_currency_total'] is None

def test_backup_restore_and_cross_mode_rejection(store,tmp_path):
    store.add_account(account());store.trade(trade());expected=store.ledger()
    backup=store.backup();source=store.directory/'backups'/backup['name']
    restored=tmp_path.resolve()/'restored';restore_owner(source,restored)
    assert OwnerStore(restored).ledger()==expected;authenticate(OwnerStore(restored).owner(),PASSWORD)
    with pytest.raises(ValueError):restore_owner(source,restored)
    with pytest.raises(ValueError):restore(source,tmp_path.resolve()/'wrong-mode')
    other=LocalStore(tmp_path.resolve()/'p1',[]);b=other.backup()
    with pytest.raises(ValueError):restore_owner(other.directory/'backups'/b['name'],tmp_path.resolve()/'wrong-owner')
    with (source/'owner.sqlite3').open('ab') as f:f.write(b'corrupted')
    with pytest.raises(ValueError):restore_owner(source,tmp_path.resolve()/'corrupt')

def test_future_database_rejected(store):
    with store.connection() as db:db.execute('PRAGMA user_version=99')
    with pytest.raises(ValueError):OwnerStore(store.directory)
