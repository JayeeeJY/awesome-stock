"""Versioned user quality feedback; never alters an insight or infers performance."""
import json
from uuid import uuid5, NAMESPACE_URL
from . import owner_business as b
from .owner import identifier,text
from .local import Conflict


def target(db, target_id, symbol):
    identifier(target_id)
    if not isinstance(symbol,str):raise ValueError('invalid symbol')
    record=next((r for r in b.records(db) if r['id']==target_id),None)
    if record is None or record['kind'] not in {'diagnosis','daily_brief'}:raise ValueError('unsupported feedback target')
    if symbol:
        if record['kind']!='diagnosis':raise ValueError('impact needs diagnostic report')
        impact=next((i for i in record['report'].get('intelligence',{}).get('top_impacts',[]) if i['symbol']==symbol),None)
        if impact is None:raise ValueError('impact missing')
        return record,'portfolio_impact',b.digest(impact)
    return record,record['kind'],b.digest(record)


def save(store,body):
    b.fields(body,'operation_id target_id target_symbol revision rating reason note action_taken action_type')
    store._revision(body['revision'])
    if body['rating'] not in {'useful','not_useful'} or type(body['action_taken']) is not bool:raise ValueError('invalid rating/action')
    reason=b.optional(body['reason'],500);note=b.optional(body['note'],4000);action=b.optional(body['action_type'],120)
    if body['action_taken'] and not action:raise ValueError('action description required')
    if not body['action_taken'] and action:raise ValueError('unexpected action description')
    with store.transaction() as db:
        fp,old=store._operation(db,body,'insight_feedback_save')
        if old is not None:return old
        record,kind,digest=target(db,body['target_id'],body['target_symbol'])
        fid=str(uuid5(NAMESPACE_URL,'owner-feedback:'+record['id']+':'+body['target_symbol']))
        current=next((r for r in b.records(db,'insight_feedback') if r['id']==fid),None)
        if (current['revision'] if current else 0)!=body['revision']:raise Conflict('feedback changed')
        result=b._put(store,db,{'id':fid,'revision':body['revision']},
            {'kind':'insight_feedback','title':'洞察反馈','target_id':record['id'],'target_revision':record['revision'],
             'target_symbol':body['target_symbol'],'insight_type':kind,'target_digest':digest,
             'rating':body['rating'],'reason':reason,'note':note,'action_taken':body['action_taken'],
             'action_type':action,'performance_inferred':False})
        return store._result(db,body,fp,result)


def history(store,body):
    b.fields(body,'target_id target_symbol')
    with store.connection() as db:
        db.execute('BEGIN');target(db,body['target_id'],body['target_symbol'])
        current=next((r for r in b.records(db,'insight_feedback') if r['target_id']==body['target_id'] and r['target_symbol']==body['target_symbol']),None)
        versions=[json.loads(r[0]) for r in db.execute('SELECT payload FROM document_versions WHERE id=? ORDER BY revision DESC',(current['id'],))] if current else []
        return {'current':current,'versions':versions}


def summary(store):
    with store.connection() as db:
        rows=b.records(db,'insight_feedback');counts={}
        for row in rows:
            bucket=counts.setdefault(row['insight_type'],{'useful':0,'not_useful':0})
            bucket[row['rating']]+=1
        return {'total':len(rows),'useful':sum(r['rating']=='useful' for r in rows),
                'not_useful':sum(r['rating']=='not_useful' for r in rows),'by_type':counts,
                'basis':'latest feedback per fixed insight; no performance inference'}
