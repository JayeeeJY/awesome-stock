"""Bounded CSV preview/atomic import and credential-free business export."""
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from io import StringIO
import json
import re
from .owner import identifier, trade_payload, LedgerInvalid
from .local import Conflict, _canonical

COLUMNS = ['record_id','symbol','side','quantity','price','fee','executed_at']


def _same(a,b):
    return all(Decimal(a[k])==Decimal(b[k]) if k in ('quantity','price','fee') else a[k]==b[k]
               for k in ('symbol','side','quantity','price','fee','executed_at'))


def _input(body,commit=False):
    fields={'account_id','csv'}|({'preview_token','operation_id'} if commit else set())
    if not isinstance(body,dict) or set(body)!=fields:raise ValueError('invalid fields')
    identifier(body['account_id'])
    content=body['csv']
    if not isinstance(content,str) or len(content.encode('utf-8'))>32768 or '\x00' in content:raise ValueError('invalid CSV')
    if commit and (not isinstance(body['preview_token'],str) or not re.fullmatch('[a-f0-9]{64}',body['preview_token'])):raise ValueError('invalid preview')


def _preview(store,db,body):
    account_id=body['account_id']
    if not db.execute('SELECT 1 FROM accounts WHERE id=?',(account_id,)).fetchone():raise ValueError('unknown account')
    before=store._account_projection(db,account_id)
    raw=list(db.execute('SELECT id,payload,revision,sequence FROM trades ORDER BY sequence'))
    existing={r[0]:json.loads(r[1]) for r in raw}
    deleted={r[0] for r in db.execute("SELECT entity_id FROM audit WHERE action='trade_deleted'")}
    snapshot={'data_epoch':db.execute("SELECT value FROM metadata WHERE key='data_epoch'").fetchone(),'accounts':list(db.execute('SELECT * FROM accounts ORDER BY id')),'trades':raw,'audit':db.execute('SELECT COALESCE(MAX(sequence),0) FROM audit').fetchone()[0]}
    token=hashlib.sha256(_canonical({'input':{'account_id':account_id,'csv':body['csv']},'snapshot':snapshot}).encode()).hexdigest()
    rows=[];new=[];seen={};errors=[]
    try:
        reader=csv.reader(StringIO(body['csv'].lstrip('\ufeff'),newline=''),strict=True)
        header=next(reader,None)
        if header!=COLUMNS:raise ValueError('header')
        sequence=db.execute("SELECT COALESCE((SELECT seq FROM sqlite_sequence WHERE name='trades'),0)").fetchone()[0]
        event_sequence=db.execute("SELECT COALESCE((SELECT seq FROM sqlite_sequence WHERE name='ledger_events'),0)").fetchone()[0]
        for index,values in enumerate(reader,1):
            if index>200:raise ValueError('too many rows')
            row={'row':index+1,'status':'invalid','message':'字段、编号、数值或含时区时间无效。'}
            rows.append(row)
            if len(values)!=len(COLUMNS):continue
            fields=dict(zip(COLUMNS,values));source=fields.pop('record_id')
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,79}',source):continue
            row['record_id']=source
            id='csv-'+hashlib.sha256(_canonical([account_id,source]).encode()).hexdigest()[:48]
            try:payload=trade_payload({'id':id,'account_id':account_id,**fields})
            except (ValueError,TypeError,KeyError):continue
            row['trade']=payload
            old=seen.get(id) or existing.get(id)
            if id in deleted and id not in existing:
                row.update(status='conflict',message='此编号曾被删除，请核对原记录，不会自动恢复。')
            elif old:
                row.update(status='duplicate' if _same(old,payload) else 'conflict',message='同编号同内容，跳过。' if _same(old,payload) else '同编号内容不同，请先核对或更正原交易。')
            else:
                possible=any(t['account_id']==account_id and _same(t,payload) for t in [*existing.values(),*seen.values()])
                row.update(status='new',message='不同编号存在相同成交事实，请核对是否重复。' if possible else '新增交易。',possible_duplicate=possible)
                new.append({**payload,'revision':1,'sequence':sequence+len(new)+1,'event_order':event_sequence+len(new)+1})
            seen.setdefault(id,payload)
        if not rows:errors.append('没有交易数据行。')
    except (csv.Error,ValueError):errors.append('CSV须使用固定七列表头、合法引号，且不超过200行。')
    after=None
    if not errors and all(r['status'] in ('new','duplicate') for r in rows):
        try:after=store._account_projection(db,account_id,new)
        except LedgerInvalid:errors.append('按成交时间重算后现金不足或超卖，请核对CSV及既有交易；整批不写入。')
    result={'rows':rows,'errors':errors,'before':before,'after':after,'can_import':after is not None,'preview_token':token,
            'new_count':sum(r['status']=='new' for r in rows),'duplicate_count':sum(r['status']=='duplicate' for r in rows),'account_id':account_id,'currency':before['currency']}
    return result,new


def preview(store,body):
    _input(body)
    with store.connection() as db:
        db.execute('BEGIN')
        return _preview(store,db,body)[0]


def commit(store,body):
    _input(body,True)
    with store.transaction() as db:
        fp,old=store._operation(db,body,'csv_import')
        if old is not None:return old
        result,new=_preview(store,db,body)
        if result['preview_token']!=body['preview_token']:raise Conflict('preview stale')
        if not result['can_import']:raise ValueError('preview invalid')
        for t in new:
            payload={k:v for k,v in t.items() if k not in ('sequence','revision','event_order')}
            db.execute('INSERT INTO trades(id,account_id,payload,revision) VALUES (?,?,?,1)',(t['id'],t['account_id'],_canonical(payload)))
            db.execute("INSERT INTO ledger_events(kind,entity_id) VALUES ('trade',?)",(t['id'],))
            store._audit(db,'trade_saved',t['id'],None,{**payload,'revision':1})
        after=store._account_projection(db,body['account_id'])
        receipt={'imported':len(new),'skipped':result['duplicate_count'],'account':after}
        store._audit(db,'csv_imported',body['account_id'],None,{'operation_id':body['operation_id'],'imported':len(new),'skipped':result['duplicate_count']})
        return store._result(db,body,fp,receipt)


def export_data(store):
    with store.connection() as db:
        db.execute('BEGIN')
        accounts=[store._account_projection(db,r[0]) for r in db.execute('SELECT id FROM accounts ORDER BY id')]
        documents=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents ORDER BY id')]
        versions=[json.loads(r[0]) for r in db.execute('SELECT payload FROM document_versions ORDER BY id,revision')]
        links=[dict(zip(('trade_id','decision_id','decision_revision','revision'),r)) for r in db.execute('SELECT trade_id,decision_id,decision_revision,revision FROM trade_links ORDER BY trade_id')]
        return {'format':'awesome-stock-owner-business','format_version':2,'exported_at':datetime.now(timezone.utc).isoformat(),
                'accounts':accounts,'documents':documents,'document_versions':versions,'trade_links':links,'cash_flow_versions':[json.loads(r[0]) for r in db.execute('SELECT payload FROM cash_flow_versions ORDER BY id,revision')],'restores_account':False}
