import json
import sqlite3
import uuid
import pytest
from awesome_stock.storage.owner import OwnerStore, restore_owner, check_owner
from test_owner_store import account, trade, PASSWORD

@pytest.mark.parametrize('method,open_cost,realized',[('fifo','251.5','98.5'),('avg','226.5','73.5')])
def test_cost_choice_fees_backdated_recompute_restart_restore(tmp_path,method,open_cost,realized):
    store=OwnerStore(tmp_path.resolve()/'data');store.setup('tester',PASSWORD)
    payload=account(cost_method=method);assert store.add_account(payload)==store.add_account(payload)
    # Insert out of chronological order; projections must use execution order.
    store.trade(trade(quantity='10',price='20',executed_at='2026-01-02T12:00:00Z'))
    store.trade(trade())
    store.trade(trade(side='sell',quantity='5',price='30',executed_at='2026-01-03T12:00:00Z'))
    result=store.ledger();a=result['accounts'][0];h=a['holdings'][0]
    assert a['cost_method']==method and a['cash']=='847'
    assert h['open_cost']==open_cost and h['realized_pnl']==realized
    assert OwnerStore(store.directory).ledger()==result
    backup=store.backup();assert backup['schema_version']==5
    target=tmp_path.resolve()/'restored';restore_owner(store.directory/'backups'/backup['name'],target)
    assert OwnerStore(target).ledger()==result


def test_v3_migration_keeps_average_and_has_restorable_preupgrade_backup(tmp_path):
    store=OwnerStore(tmp_path.resolve()/'data');store.setup('tester',PASSWORD);store.add_account(account());store.trade(trade());before=store.ledger()
    with store.transaction() as db:
        db.execute('ALTER TABLE accounts DROP COLUMN broker');db.execute('ALTER TABLE accounts DROP COLUMN revision')
        db.execute('ALTER TABLE accounts DROP COLUMN cost_method');db.execute('PRAGMA user_version=3')
    upgraded=OwnerStore(store.directory);assert upgraded.ledger()==before
    backups=list((store.directory/'backups').iterdir());assert len(backups)==1
    assert json.loads((backups[0]/'manifest.json').read_text())['schema_version']==3
    target=tmp_path.resolve()/'restored';restore_owner(backups[0],target)
    with sqlite3.connect(target/'owner.sqlite3') as db:check_owner(db,3)
    assert OwnerStore(target).ledger()==before
    OwnerStore(store.directory);assert len(list((store.directory/'backups').iterdir()))==1

@pytest.mark.parametrize('method',['average','FIFO','',None,[],1])
def test_invalid_cost_choice_writes_nothing(tmp_path,method):
    store=OwnerStore(tmp_path.resolve()/'data')
    with pytest.raises(ValueError):store.add_account(account(cost_method=method))
    assert store.ledger()['accounts']==[]
