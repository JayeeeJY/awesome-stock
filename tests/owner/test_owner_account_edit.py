import uuid
import pytest
from awesome_stock.storage.owner import OwnerStore,restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_store import account,trade,PASSWORD

def body(**changes):return {'id':'account-test','operation_id':str(uuid.uuid4()),'revision':1,'name':'Renamed','broker':'Synthetic broker'}|changes

def test_edit_idempotent_conflict_and_financial_facts_unchanged(tmp_path):
    s=OwnerStore(tmp_path.resolve()/'data');s.setup('tester',PASSWORD);s.add_account(account(cost_method='fifo',broker='Initial'));s.trade(trade())
    before=s.ledger()['accounts'][0];b=body();assert s.edit_account(b)==s.edit_account(b)
    with pytest.raises(Conflict):s.edit_account(body(name='Stale'))
    after=s.ledger()['accounts'][0];assert (after['name'],after['broker'],after['revision'])==('Renamed','Synthetic broker',2)
    for field in ['cash','holdings','trades','opening_cash','currency','cost_method']:assert before[field]==after[field]
    backup=s.backup();target=tmp_path.resolve()/'restored';restore_owner(s.directory/'backups'/backup['name'],target)
    assert OwnerStore(target).ledger()==s.ledger()

@pytest.mark.parametrize('changes',[{'revision':True},{'broker':None},{'broker':'x'*81},{'name':''},{'currency':'HKD'}])
def test_invalid_edit_unchanged(tmp_path,changes):
    s=OwnerStore(tmp_path.resolve()/'data');s.add_account(account());before=s.ledger()
    with pytest.raises(ValueError):s.edit_account(body(**changes))
    assert s.ledger()==before

def test_v4_migration_keeps_fifo_and_existing_financial_facts(tmp_path):
    s=OwnerStore(tmp_path.resolve()/'data');s.add_account(account(cost_method='fifo'));s.trade(trade());before=s.ledger()
    with s.transaction() as db:
        db.execute('ALTER TABLE accounts DROP COLUMN broker');db.execute('ALTER TABLE accounts DROP COLUMN revision');db.execute('PRAGMA user_version=4')
    assert OwnerStore(s.directory).ledger()==before
    backup=next((s.directory/'backups').iterdir());target=tmp_path.resolve()/'restored';restore_owner(backup,target)
    assert OwnerStore(target).ledger()==before
