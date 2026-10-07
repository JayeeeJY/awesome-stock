"""Atomic, user-triggered factual daily capture. No provider or trading calls."""
from contextlib import nullcontext
from uuid import uuid5, NAMESPACE_URL
from . import owner_business as business, owner_diagnosis as diagnosis
from .owner import identifier
from . import owner_diagnosis_scope as scopes
from .local import Conflict


def capture(store, body, *, _db=None, _source="manual"):
    business.fields(body, 'operation_id input expected_token')
    with (store.transaction() if _db is None else nullcontext(_db)) as db:
        fingerprint, previous = store._operation(db, body, 'daily_capture')
        if previous is not None:
            return previous
        if body['expected_token'] != diagnosis.evidence_token(store, db):
            raise Conflict('daily evidence changed')
        report = diagnosis.calculate(store, db, body['input'])
        captured_at = report['generated_at']
        account_id = report['account_id']
        # IDs belong to the operation, not the date: an explicit later capture
        # is a new immutable observation, never an overwrite of closing prices.
        def put(part, payload):
            doc_id = str(uuid5(NAMESPACE_URL, 'owner-daily:' + body['operation_id'] + ':' + part))
            if db.execute('SELECT 1 FROM documents WHERE id=?', (doc_id,)).fetchone():
                raise Conflict('daily record already exists')
            return business._put(store, db, {'id': doc_id, 'revision': 0},
                                 {'account_id': account_id, **payload})
        ledger_accounts = business.ledger_snapshot(store, db)
        ledger = ({'scope_kind': 'all_accounts', 'accounts': ledger_accounts} if account_id == scopes.ALL
                  else next(a for a in ledger_accounts if a['id'] == account_id))
        snapshot = put('snapshot', {'kind': 'daily_snapshot', 'title': '当次账本快照',
                       'captured_at': captured_at, 'ledger': ledger,
                       'valuation': report['account_evidence'], 'evidence_token': body['expected_token']})
        diagnostic = put('diagnosis', {'kind': 'diagnosis', 'title': '日报组合诊断',
                         'report': report, 'input': body['input']})
        brief = put('brief', {'kind': 'daily_brief', 'title': '组合事实日报',
                    'captured_at': captured_at, 'snapshot_id': snapshot['id'],
                    'diagnosis_id': diagnostic['id'], 'currency': report['currency'],
                    'facts': {'position_count': report['position_count'],
                              'position_value': report['total_value'],
                              'score': report['score'], 'grade': report['grade'],
                              'missing': report['missing'], 'status': report['status'],
                              'intelligence': report['intelligence']},
                    'journal': {'entry_date': captured_at[:10], 'account_name': report['account_evidence']['name'],
                                'tickers': [p['symbol'] for p in report['account_evidence']['positions']],
                                'tags': ['daily-brief', 'portfolio', _source],
                                'content': '\n'.join([
                                    '组合事实日报 · '+captured_at,
                                    '账户：'+report['account_evidence']['name']+' · '+report['currency'],
                                    '持仓数量：'+str(report['position_count']),
                                    '持仓市值：'+(report['total_value'] or '资料不足')+' '+report['currency'],
                                    '规则评分：'+(report['score'] or '资料不足')+'；评级：'+(report['grade'] or '未评级'),
                                    *['待补：'+item for item in report['missing']],
                                    '依据为生成当时的账本与已保存价格；不代表交易所收盘价或投资建议。'])},
                    'method': 'local-facts-v1', 'provider_used': False,
                    'scope': 'Observation at capture time; not exchange closing prices or investment advice.'})
        run = put('run', {'kind': 'daily_run', 'title': '日报运行记录',
                  'captured_at': captured_at, 'status': 'completed',
                  'data_status': report['status'], 'source': _source,
                  'snapshot_id': snapshot['id'], 'diagnosis_id': diagnostic['id'],
                  'brief_id': brief['id']})
        return store._result(db, body, fingerprint, {'run': run, 'brief': brief,
                             'snapshot': snapshot, 'diagnosis': diagnostic})


def history(store, account_id):
    scopes.scope_id(account_id)
    with store.connection() as db:
        db.execute('BEGIN')
        kinds = {'daily_run', 'daily_brief', 'daily_snapshot', 'daily_ai_draft'}
        rows = [r for r in business.records(db) if r['kind'] in kinds and r['account_id'] == account_id]
        rows.sort(key=lambda r: (r['updated_at'], r['id']), reverse=True)
        return {'account_id': account_id, 'records': rows}


def save_ai_draft(store, body, receipts):
    """Persist a completed, explicitly requested generation beside immutable facts."""
    business.fields(body, 'id operation_id brief_id token')
    identifier(body['id']);identifier(body['brief_id'])
    if not isinstance(body['token'], str):raise ValueError('invalid receipt')
    with store.transaction() as db:
        fp, old = store._operation(db, body, 'daily_ai_draft')
        if old is not None:return old
        if db.execute('SELECT 1 FROM documents WHERE id=?', (body['id'],)).fetchone():
            raise Conflict('AI draft is immutable')
        brief = next((r for r in business.records(db, 'daily_brief') if r['id'] == body['brief_id']), None)
        if brief is None:raise ValueError('daily report missing')
        receipt = receipts.get(body['token'])
        if receipt is None:raise Conflict('generation receipt unavailable; no new request was sent')
        result = business._put(store, db, {'id': body['id'], 'revision': 0},
            {'kind': 'daily_ai_draft', 'title': '日报 AI 汇总 · 未核验',
             'account_id': brief['account_id'], 'brief_id': brief['id'],
             'brief_revision': brief['revision'], 'fact_hash': business.digest(brief),
             'draft': receipt['draft'], 'provider': receipt['provider'], 'model': receipt['model'],
             'generated_at': receipt['generated_at'], 'sent_context': receipt['context'],
             'review_status': 'unverified', 'replaces_facts': False})
        return store._result(db, body, fp, result)
