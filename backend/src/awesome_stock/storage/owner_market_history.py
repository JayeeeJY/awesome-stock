"""Explicitly saved provider history receipts, immutable and credential-free."""
from . import owner_business as b
from .owner import identifier
from .local import Conflict


def save(store,body,connections):
    b.fields(body,'id operation_id token');identifier(body['id'])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'market_history_save')
        if old is not None:return old
        if db.execute('SELECT 1 FROM documents WHERE id=?',(body['id'],)).fetchone():raise Conflict('history immutable')
        packet=connections.history_receipt(body['token'])
        result=b._put(store,db,{'id':body['id'],'revision':0},{'kind':'market_history','title':packet['symbol']+' · 日线来源快照',**packet})
        return store._result(db,body,fp,result)


def history(store):
    with store.connection() as db:
        return {'snapshots':b.records(db,'market_history'),'executes_trades':False}
