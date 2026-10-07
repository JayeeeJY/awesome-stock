"""Explicit decision-required designation, separate from immutable trade history."""
import json
from uuid import uuid5, NAMESPACE_URL
from . import owner_business as b
from .owner import identifier
from .local import Conflict


def context_id(trade_id):
    return str(uuid5(NAMESPACE_URL, 'owner-trade-context:'+trade_id))


def snapshot(db, trade_id):
    row = db.execute('SELECT payload,revision,account_id FROM trades WHERE id=?', (trade_id,)).fetchone()
    if row is None:
        raise ValueError('trade missing')
    trade = {**json.loads(row[0]), 'id': trade_id, 'revision': row[1], 'account_id': row[2]}
    record = next((r for r in b.records(db, 'trade_context') if r['id']==context_id(trade_id)), None)
    link = db.execute('SELECT decision_id,decision_revision,revision FROM trade_links WHERE trade_id=?', (trade_id,)).fetchone()
    linked = bool(link and link[0])
    stale = bool(record and record['trade_revision'] != trade['revision'])
    required = bool(record and record['decision_required'] and not stale)
    return {'trade':trade,'context':record,'context_stale':stale,
            'decision_link':{'id':link[0],'revision':link[1],'link_revision':link[2]} if linked else None,
            'qualification':'linked_decision' if linked else 'needs_reconfirmation' if stale else 'required_without_context' if required else 'ordinary'}


def history(store, body):
    b.fields(body,'trade_id');identifier(body['trade_id'])
    with store.connection() as db:
        db.execute('BEGIN')
        result = snapshot(db,body['trade_id'])
        versions = [json.loads(r[0]) for r in db.execute('SELECT payload FROM document_versions WHERE id=? ORDER BY revision DESC',(context_id(body['trade_id']),))]
        return {**result,'versions':versions}


def save(store,body):
    b.fields(body,'operation_id trade_id trade_revision revision decision_required reason')
    identifier(body['trade_id']);store._revision(body['revision']);store._revision(body['trade_revision'])
    if type(body['decision_required']) is not bool:
        raise ValueError('decision requirement must be boolean')
    reason=b.optional(body['reason'],4000)
    with store.transaction() as db:
        fp,old=store._operation(db,body,'trade_context_save')
        if old is not None:return old
        current=snapshot(db,body['trade_id'])
        if current['trade']['revision']!=body['trade_revision']:
            raise Conflict('trade changed')
        record=current['context']
        if (record['revision'] if record else 0)!=body['revision']:
            raise Conflict('trade context changed')
        result=b._put(store,db,{'id':context_id(body['trade_id']),'revision':body['revision']},
                      {'kind':'trade_context','title':'成交决策资格','trade_id':body['trade_id'],
                       'trade_revision':body['trade_revision'],'trade_evidence':current['trade'],
                       'decision_required':body['decision_required'],'reason':reason})
        return store._result(db,body,fp,result)
