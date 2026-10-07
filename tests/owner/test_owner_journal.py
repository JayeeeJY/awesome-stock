"""Journal writes are owner-only, versioned, and distinct from fixed decision reviews."""
import uuid
from datetime import datetime, timezone

import pytest

from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import OwnerStore, restore_owner
from awesome_stock.storage.owner_journal import save, workspace
from test_owner_store import store, account, trade
from test_owner_api import app, request, login


def body(**changes):
    return dict(id=str(uuid.uuid4()), revision=0, operation_id=str(uuid.uuid4()),
                title='Synthetic weekly review', content='A manual process note',
                entry_date='2026-10-02', mood='neutral', tickers=['TEST'], tags=['复盘']) | changes


def test_journal_versions_archival_idempotency_and_restore(store, tmp_path):
    original = body()
    first = save(store, original)
    assert save(store, original) == first
    with pytest.raises(Conflict):save(store, original | {'content': 'Changed retry'})
    with pytest.raises(Conflict):save(store, original | {'operation_id': str(uuid.uuid4())})
    revised = save(store, original | {'revision': 1, 'operation_id': str(uuid.uuid4()), 'content': 'Revised note'})
    assert revised['revision'] == 2 and workspace(store)['entries'][0]['content'] == 'Revised note'
    assert len(store.documents()['documents']) == 0  # Journal is separate from research notes.
    with store.connection() as db:
        rows = db.execute('SELECT payload FROM document_versions WHERE id=?', (first['id'],)).fetchall()
    assert len(rows) == 2 and 'A manual process note' in rows[0][0]
    backup = store.backup()
    restored = tmp_path.resolve() / 'restored-journal'
    restore_owner(store.directory / 'backups' / backup['name'], restored)
    assert workspace(OwnerStore(restored))['entries'] == workspace(store)['entries']
    saved = save(store, {'id': first['id'], 'revision': 2, 'operation_id': str(uuid.uuid4())}, archive=True)
    assert saved['archived'] and workspace(store)['entries'] == []
    with pytest.raises(Conflict):save(store, original | {'revision': 3, 'operation_id': str(uuid.uuid4())})


@pytest.mark.parametrize('change', [
    {'title': ''}, {'content': ''}, {'entry_date': '2026-02-30'}, {'mood': 'winning'},
    {'tickers': ['BAD SYMBOL']}, {'tickers': ['TEST', 'TEST']}, {'tags': ['']},
    {'content': 'x' * 20001}, {'revision': True}, {'unknown': True},
])
def test_journal_rejects_invalid_input_without_write(store, change):
    with pytest.raises((ValueError, TypeError)):save(store, body(**change))
    assert workspace(store)['entries'] == []


def test_recent_trades_are_owner_ledger_facts(store):
    store.add_account(account())
    saved = trade(executed_at=datetime.now(timezone.utc).isoformat())
    store.trade(saved)
    current = workspace(store)
    assert current['recent_trades'][0]['symbol'] == saved['symbol']
    assert current['recent_trades'][0]['account_name'] == 'Synthetic'
    assert current['manual_only'] is True


def test_journal_endpoint_requires_owner_and_csrf(app):
    payload = body()
    assert request(app, '/api/v1/owner/journal')['status'] == 401
    auth = login(app)
    assert request(app, '/api/v1/owner/journal', 'POST', payload, cookie=auth['cookie'])['status'] == 403
    assert request(app, '/api/v1/owner/journal', 'POST', payload, **auth)['status'] == 200
    assert request(app, '/api/v1/owner/journal', **auth)['body']['entries'][0]['title'] == payload['title']
    assert request(app, '/api/v1/owner/journal', 'POST', payload | {'extra': 1}, **auth)['status'] == 400
