"""Versioned manual deposits/withdrawals; no payment or brokerage execution."""
from datetime import datetime,timezone
import json
from .owner import identifier,number,text,OwnerStore
from .local import Conflict,_canonical


def history(store):
    with store.connection() as db:
        return {'versions':[json.loads(r[0]) for r in db.execute('SELECT payload FROM cash_flow_versions ORDER BY id,revision')],'executes_transfers':False}


def save(store,body,*,delete=False):
    common={'id','revision','operation_id'}
    if not isinstance(body,dict) or set(body)!=(common if delete else common|{'account_id','direction','amount','occurred_at','note'}):raise ValueError('invalid cash fields')
    identifier(body['id']);OwnerStore._revision(body['revision'])
    if not delete:
        identifier(body['account_id'])
        if body['direction'] not in ('deposit','withdrawal'):raise ValueError('invalid direction')
        amount=number(body['amount'],positive=True)
        when=datetime.fromisoformat(text(body['occurred_at'],40).replace('Z','+00:00'))
        if when.utcoffset() is None or not 1900<=when.year<=2200:raise ValueError('timezone required')
        if not isinstance(body['note'],str) or len(body['note'])>1000 or '\x00' in body['note']:raise ValueError('invalid note')
        payload={'id':body['id'],'account_id':body['account_id'],'direction':body['direction'],'amount':amount,'occurred_at':when.astimezone(timezone.utc).isoformat(timespec='microseconds'),'note':body['note'].strip()}
    with store.transaction() as db:
        fp,old=store._operation(db,body,'cash_delete' if delete else 'cash_save')
        if old is not None:return old
        row=db.execute('SELECT payload,revision,account_id FROM cash_flows WHERE id=?',(body['id'],)).fetchone()
        current=json.loads(row[0]) if row else None
        if (row[1] if row else 0)!=body['revision'] or (delete and not row):raise Conflict('cash version changed')
        if row and not delete and row[2]!=body['account_id']:raise ValueError('account cannot change')
        if delete:
            result={**current,'revision':body['revision']+1,'deleted':True,'updated_at':datetime.now(timezone.utc).isoformat()}
            db.execute('DELETE FROM cash_flows WHERE id=?',(body['id'],))
        else:
            if not db.execute('SELECT 1 FROM accounts WHERE id=?',(body['account_id'],)).fetchone():raise ValueError('unknown account')
            if row:order=current['event_order']
            else:
                if db.execute("SELECT 1 FROM ledger_events WHERE kind='cash' AND entity_id=?",(body['id'],)).fetchone():raise Conflict('deleted cash ID cannot be reused')
                order=db.execute("INSERT INTO ledger_events(kind,entity_id) VALUES ('cash',?)",(body['id'],)).lastrowid
            result={**payload,'revision':body['revision']+1,'event_order':order,'deleted':False,'updated_at':datetime.now(timezone.utc).isoformat()}
            db.execute('INSERT INTO cash_flows VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(body['id'],body['account_id'],_canonical(result),result['revision']))
        store._account_projection(db,result['account_id'])
        db.execute('INSERT INTO cash_flow_versions VALUES (?,?,?)',(body['id'],result['revision'],_canonical(result)))
        store._audit(db,'cash_deleted' if delete else 'cash_saved',body['id'],current,result)
        return store._result(db,body,fp,result)
