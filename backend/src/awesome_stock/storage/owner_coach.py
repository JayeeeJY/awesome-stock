"""Deterministic decision-process checks, independent of outcome or model calls."""
import json
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

FORMULA = 'selfuse-coach-process-v1'


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:raise ValueError('timezone required')
    return result


def evaluate(trade, history, *, decision_context, reason='', require_reason=True, history_complete=True):
    if decision_context not in {'linked_decision', 'required_without_context', 'ordinary'}:
        raise ValueError('invalid decision context')
    if type(require_reason) is not bool or type(history_complete) is not bool:
        raise ValueError('boolean required')
    at = instant(trade['executed_at'])
    previous = [t for t in history if t['id'] != trade['id']
                and t['account_id'] == trade['account_id'] and t['symbol'] == trade['symbol']
                and instant(t['executed_at']) < at]
    previous.sort(key=lambda t:(instant(t['executed_at']),t['id']))
    patterns=[]
    def add(code,penalty,refs):
        patterns.append({'code':code,'penalty':penalty,'severity':'critical' if code=='missing_reason' else 'watch','trade_ids':refs})
    eligible = decision_context != 'ordinary'
    if eligible:
        if require_reason and decision_context=='required_without_context' and not reason.strip():add('missing_reason',20,[trade['id']])
        recent=[t for t in previous if at-instant(t['executed_at'])<=timedelta(days=14)]
        if len(recent)>=2:add('overtrading',10,[t['id'] for t in recent]+[trade['id']])
        reverse=[t for t in recent if t['side']!=trade['side'] and at-instant(t['executed_at'])<=timedelta(days=7)]
        if reverse:add('rapid_reversal',15,[t['id'] for t in reverse]+[trade['id']])
        buys=[t for t in previous if t['side']=='buy' and Decimal(t['price'])>0]
        if trade['side']=='buy' and buys:
            # Equal latest timestamps do not establish which buy was last.
            last=buys[-1];tied=sum(instant(t['executed_at'])==instant(last['executed_at']) for t in buys)>1
            if tied:history_complete=False
            else:
                with localcontext() as ctx:
                    ctx.prec=60
                    price=Decimal(trade['price']);old=Decimal(last['price'])
                    if price>old*Decimal('1.08'):add('chasing',10,[last['id'],trade['id']])
                    if price<old*Decimal('.92') and not reason.strip():add('averaged_down_unreviewed',10,[last['id'],trade['id']])
    return {'formula':FORMULA,'decision_context':decision_context,'process_scored':eligible,
            'status':'unscored' if not eligible else 'complete' if history_complete else 'partial',
            'process_score':max(0,100-sum(p['penalty'] for p in patterns)) if eligible and history_complete else None,
            'patterns':patterns,'history_trade_ids':[t['id'] for t in previous],
            'outcome_score':None,'executes_trades':False}


def evidence(store, db, body):
    from . import owner_business as business, owner_evolve
    if not isinstance(body,dict):raise ValueError('invalid coach input')
    direct='trade_id' in body
    business.fields(body, 'trade_id history_complete constitution_revision' if direct else 'decision_ref history_complete')
    if type(body['history_complete']) is not bool:raise ValueError('history completeness required')
    qualification=None;constitution=None;reason='';require_reason=True
    if direct:
        from . import owner_trade_context
        from .owner_constitution import ID
        from .owner import identifier
        identifier(body['trade_id'])
        qualification=owner_trade_context.snapshot(db,body['trade_id'])
        if qualification['qualification']!='required_without_context':raise ValueError('trade is not an unlinked confirmed important trade')
        revision=body['constitution_revision']
        if type(revision) is not int or revision<1:raise ValueError('constitution revision required')
        row=db.execute('SELECT payload FROM document_versions WHERE id=? AND revision=?',(ID,revision)).fetchone()
        if row is None:raise ValueError('constitution version missing')
        constitution=json.loads(row[0]);require_reason=constitution['config']['require_reason_before_trade']
        trade=qualification['trade'];account=store._account_projection(db,trade['account_id'])
        trade={**trade,'account_name':account['name'],'currency':account['currency']}
        snapshot={'decision':None,'research':None,'trades':[trade]}
        reason=qualification['context']['reason']
    else:
        snapshot, _ = owner_evolve.evidence(store, db, body['decision_ref'])
        reason=snapshot['decision']['content']
    accounts = {t['account_id'] for t in snapshot['trades']}
    ledger = [store._account_projection(db, aid) for aid in sorted(accounts)]
    trades = [t for a in ledger for t in a['trades'] if t['symbol']==(snapshot['trades'][0]['symbol'] if direct else snapshot['decision']['symbol'])]
    latest = max((instant(t['executed_at']) for t in snapshot['trades']), default=None)
    history = [t for t in trades if latest is not None and instant(t['executed_at'])<=latest]
    facts = {'decision_evidence': snapshot, 'history': history,
             'history_complete_confirmed': body['history_complete'], 'formula': FORMULA}
    if direct:facts.update(qualification=qualification,constitution=constitution)
    checks = [{'trade_id': t['id'], **evaluate(t, history, decision_context='required_without_context' if direct else 'linked_decision',
               reason=reason,require_reason=require_reason, history_complete=body['history_complete'])} for t in snapshot['trades']]
    from .owner_coach_outcome import evaluate as outcome
    quotes = business.quote_map(db)
    currencies = {a['id']: a['currency'] for a in ledger}
    outcomes = [outcome(t, quotes.get((t['symbol'], currencies[t['account_id']])),
                       currency=currencies[t['account_id']], observed_on=business.now().date().isoformat())
                for t in snapshot['trades']]
    for check, result in zip(checks, outcomes):
        check['outcome'] = result
        check['outcome_score'] = result['outcome_score']
    report = {'process_evidence_token': business.digest(facts), 'formula': FORMULA, 'status': 'unexecuted' if not checks else 'partial' if any(c['status']=='partial' for c in checks) else 'complete',
              'checks': checks, 'evidence': facts, 'outcome_score': None,
              'scope': 'linked decisions or explicitly designated important trades; user confirms recorded history completeness; not investment quality'}
    return report, business.digest({'process': facts, 'outcomes': outcomes})


def preview(store, body):
    with store.connection() as db:
        db.execute('BEGIN');report, token = evidence(store, db, body)
        return {'report': report, 'token': token}


def save(store, body):
    from . import owner_business as business
    from .owner import identifier
    from .local import Conflict
    business.fields(body, 'id operation_id input expected_token');identifier(body['id'])
    with store.transaction() as db:
        fingerprint, old = store._operation(db, body, 'coach_save')
        if old is not None:return old
        if db.execute('SELECT 1 FROM documents WHERE id=?', (body['id'],)).fetchone():raise Conflict('coach report immutable')
        report, token = evidence(store, db, body['input'])
        if token != body['expected_token']:raise Conflict('coach evidence changed')
        result = business._put(store, db, {'id': body['id'], 'revision': 0},
            {'kind': 'coach_report', 'title': '决策教练 · '+(report['evidence']['decision_evidence']['decision'] or {'title':'重要成交 '+report['evidence']['decision_evidence']['trades'][0]['symbol']})['title'],
             'input': body['input'], 'report': report, 'evidence_token': token, 'review_status': 'unreviewed'})
        return store._result(db, body, fingerprint, result)


def history(store):
    from . import owner_business as business
    with store.connection() as db:
        db.execute('BEGIN');reports=[]
        annotations={r['report_id']:r for r in business.records(db,'coach_annotation')}
        for record in business.records(db, 'coach_report'):
            try:current, token = evidence(store, db, record['input'])
            except ValueError:current, token = {}, None
            annotation=annotations.get(record['id'])
            versions=[json.loads(row[0]) for row in db.execute('SELECT payload FROM document_versions WHERE id=? ORDER BY revision DESC',(annotation['id'],))] if annotation else []
            reports.append({**record, 'annotation':annotation, 'annotation_versions':versions, 'evidence_changed': current.get('process_evidence_token') != record['report'].get('process_evidence_token', record['evidence_token']),
                            'outcome_evidence_changed': token != record['evidence_token']})
        from . import owner_trade_context
        eligible=[]
        for row in db.execute('SELECT id FROM trades ORDER BY id').fetchall():
            item=owner_trade_context.snapshot(db,row[0])
            if item['qualification']=='required_without_context':eligible.append(item['trade'])
        return {'reports': sorted(reports, key=lambda r:(r['updated_at'],r['id']),reverse=True),
                'important_trades':eligible,'constitutions':business.records(db,'investment_constitution')}


def annotate(store, body):
    """Version human review separately; journal copies pin that exact revision."""
    from uuid import uuid5, NAMESPACE_URL
    from . import owner_business as business
    from .owner import identifier, text
    from .local import Conflict
    business.fields(body, 'operation_id report_id revision title content status')
    identifier(body['report_id']);store._revision(body['revision'])
    if body['status'] not in {'draft','reviewed','journaled','dismissed'}:raise ValueError('invalid review status')
    title=text(body['title'],120);content=text(body['content'],20000)
    aid=str(uuid5(NAMESPACE_URL,'owner-coach-review:'+body['report_id']))
    with store.transaction() as db:
        fp,old=store._operation(db,body,'coach_annotation')
        if old is not None:return old
        report=next((r for r in business.records(db,'coach_report') if r['id']==body['report_id']),None)
        if report is None:raise ValueError('unknown coach report')
        current=next((r for r in business.records(db,'coach_annotation') if r['id']==aid),None)
        if (current['revision'] if current else 0)!=body['revision']:raise Conflict('coach review changed')
        result=business._put(store,db,{'id':aid,'revision':body['revision']},
            {'kind':'coach_annotation','title':title,'content':content,'status':body['status'],
             'report_id':report['id'],'report_revision':report['revision'],'evidence_token':report['evidence_token']})
        if body['status']=='journaled':
            jid=str(uuid5(NAMESPACE_URL,'owner-coach-journal:'+aid+':'+str(result['revision'])))
            business._put(store,db,{'id':jid,'revision':0},
                {'kind':'coach_journal','title':title,'content':content,'report_id':report['id'],
                 'annotation_id':aid,'annotation_revision':result['revision'],
                 'report':report['report'],'evidence_token':report['evidence_token']})
        return store._result(db,body,fp,result)
