"""Immutable, explicitly confirmed supplier company snapshots."""
from . import owner_business as b
from .owner import identifier
from .local import Conflict


def save(store,body,connections):
    b.fields(body,'id operation_id token');identifier(body['id'])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'company_snapshot_save')
        if old is not None:return old
        if db.execute('SELECT 1 FROM documents WHERE id=?',(body['id'],)).fetchone():raise Conflict('company snapshot immutable')
        packet=connections.company_receipt(body['token'])
        result=b._put(store,db,{'id':body['id'],'revision':0},{'kind':'company_snapshot','title':packet['symbol']+' · 公司资料来源快照',**packet})
        return store._result(db,body,fp,result)


def latest(db,symbol):
    rows=sorted([r for r in b.records(db,'company_snapshot') if r['symbol']==symbol],key=lambda r:(r['updated_at'],r['id']),reverse=True)
    return rows[0] if rows else None


def read(store,body):
    b.fields(body,'symbol');symbol=b.symbol(body['symbol'])
    with store.connection() as db:
        return {'snapshot':latest(db,symbol)}
