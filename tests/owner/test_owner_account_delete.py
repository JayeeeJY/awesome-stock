import uuid
import pytest
from awesome_stock.storage.owner import OwnerStore,AccountHasHistory,restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_store import account,trade,PASSWORD

def request(revision=1):return {'id':'account-test','revision':revision,'operation_id':str(uuid.uuid4())}

def test_empty_delete_idempotent_audit_restore_and_id_not_reusable(tmp_path):
    s=OwnerStore(tmp_path.resolve()/'data');s.setup('tester',PASSWORD);s.add_account(account(opening_cash='0'));b=request()
    assert s.delete_account(b)==s.delete_account(b);assert s.ledger()['accounts']==[]
    with pytest.raises(Conflict):s.add_account(account(opening_cash='0'))
    backup=s.backup();target=tmp_path.resolve()/'restored';restore_owner(s.directory/'backups'/backup['name'],target)
    recovered=OwnerStore(target);assert recovered.ledger()['accounts']==[]
    with pytest.raises(Conflict):recovered.add_account(account(opening_cash='0'))


def test_stale_revision_cannot_delete_edited_account(tmp_path):
    s=OwnerStore(tmp_path.resolve()/'data');s.add_account(account(opening_cash='0'))
    s.edit_account({'id':'account-test','revision':1,'operation_id':str(uuid.uuid4()),'name':'New','broker':''})
    with pytest.raises(Conflict):s.delete_account(request())
    assert len(s.ledger()['accounts'])==1
    assert s.delete_account(request(2))['deleted']


def test_cash_account_not_deleted(tmp_path):
    s=OwnerStore(tmp_path.resolve()/'data');s.add_account(account());before=s.ledger()
    with pytest.raises(AccountHasHistory):s.delete_account(request())
    assert s.ledger()==before


def test_removed_trade_history_still_prevents_deletion(tmp_path):
    s=OwnerStore(tmp_path.resolve()/'data');s.add_account(account(opening_cash='0'))
    # Synthetic historical record represents an already removed transaction.
    with s.transaction() as db:s._audit(db,'trade_deleted','old-trade',{'account_id':'account-test'}, {'deleted':True})
    with pytest.raises(AccountHasHistory):s.delete_account(request())
    assert len(s.ledger()['accounts'])==1
