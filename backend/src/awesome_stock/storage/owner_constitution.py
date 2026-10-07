"""Versioned workspace discipline. Saving never rewrites fixed reports or schedules."""
import json
from uuid import uuid5, NAMESPACE_URL
from . import owner_business as b
from .owner import text
from .local import Conflict
from .owner_diagnosis import policy

ID = str(uuid5(NAMESPACE_URL, 'awesome-stock-owner-investment-constitution'))


def validate(raw):
    b.fields(raw, 'policy require_reason_before_trade prohibited_actions')
    if type(raw['require_reason_before_trade']) is not bool:
        raise ValueError('reason requirement must be boolean')
    actions = raw['prohibited_actions']
    if not isinstance(actions, list) or len(actions) > 20:
        raise ValueError('invalid prohibited actions')
    actions = [text(a, 500) for a in actions]
    if len(actions) != len(set(actions)):
        raise ValueError('duplicate prohibited action')
    return {'policy': policy(raw['policy']),
            'require_reason_before_trade': raw['require_reason_before_trade'],
            'prohibited_actions': actions}


def history(store):
    with store.connection() as db:
        db.execute('BEGIN')
        versions = [json.loads(row[0]) for row in db.execute(
            'SELECT payload FROM document_versions WHERE id=? ORDER BY revision DESC', (ID,))]
        return {'current': versions[0] if versions else None, 'versions': versions,
                'prohibited_actions_execution': 'record_only',
                'fixed_reports_and_schedules': 'unchanged'}


def save(store, body):
    b.fields(body, 'operation_id revision config')
    store._revision(body['revision'])
    config = validate(body['config'])
    with store.transaction() as db:
        fp, old = store._operation(db, body, 'constitution_save')
        if old is not None:
            return old
        current = db.execute('SELECT revision FROM documents WHERE id=?', (ID,)).fetchone()
        if (current[0] if current else 0) != body['revision']:
            raise Conflict('constitution changed')
        result = b._put(store, db, {'id': ID, 'revision': body['revision']},
                        {'kind': 'investment_constitution', 'title': '我的投资纪律', 'config': config})
        return store._result(db, body, fp, result)
