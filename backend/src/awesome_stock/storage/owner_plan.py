"""Versioned manual plans, separate from transactions and automatic execution."""
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from contextlib import nullcontext
import uuid
import json
import re
from .local import Conflict, _canonical


def workspace(store):
    with store.connection() as db:
        db.execute('BEGIN')
        current=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents ORDER BY id')]
        versions=[json.loads(r[0]) for r in db.execute('SELECT payload FROM document_versions ORDER BY id,revision')]
        active={d['id'] for d in current if d['kind']=='decision' and not d['archived']}
        plans=[]
        for p in current:
            if p['kind']=='plan':
                decision=next(d for d in current if d['id']==p['decision_ref']['id'])
                plans.append({**p,'decision_changed':decision['revision']!=p['decision_ref']['revision'],'decision_archived':decision['archived']})
        executions=[e for e in current if e['kind']=='plan_execution']
        trades=[{**json.loads(r[0]),'revision':r[1],'account_name':r[2],'currency':r[3]} for r in db.execute('SELECT t.payload,t.revision,a.name,a.currency FROM trades t JOIN accounts a ON a.id=t.account_id ORDER BY t.sequence')]
        for execution in executions:
            trade=next((t for t in trades if t['id']==execution['trade']['id']),None)
            execution['trade_changed']=trade is None or trade['revision']!=execution['trade']['revision']
        executions.sort(key=lambda e:(datetime.fromisoformat(e['trade']['executed_at'].replace('Z','+00:00')),e['id']))
        with localcontext() as ctx:
            ctx.prec=60
            for e in executions:e['amount']=format(Decimal(e['trade']['quantity'])*Decimal(e['trade']['price'])+Decimal(e['trade']['fee']),'f')
        accounts=[dict(zip(('id','name','currency'),r)) for r in db.execute('SELECT id,name,currency FROM accounts ORDER BY id')]
        for plan in plans:
            target=plan.get('target')
            if not target:continue
            linked=[e for e in executions if e['plan_id']==plan['id'] and not e['archived']]
            stale=any(e['trade_changed'] for e in linked)
            with localcontext() as ctx:
                ctx.prec=60
                quantity=sum((Decimal(e['trade']['quantity']) for e in linked),Decimal(0))
                spent=sum((Decimal(e['trade']['quantity'])*Decimal(e['trade']['price'])+Decimal(e['trade']['fee']) for e in linked),Decimal(0))
                plan['progress']={'needs_review':stale,'quantity':None if stale else format(quantity,'f'),'spent':None if stale else format(spent,'f'),'percent':None if stale else format(quantity/Decimal(target['quantity'])*100,'.2f'),'over_budget':False if stale or target['budget'] is None else spent>Decimal(target['budget'])}
        return {'accounts':accounts,'executions':executions,'execution_versions':[v for v in versions if v['kind']=='plan_execution'],'trades':trades,'plans':plans,'versions':[v for v in versions if v['kind']=='plan'],'decisions':[v for v in versions if v['kind']=='decision' and not v['archived'] and v['id'] in active],'manual_only':True,'executes_trades':False}


def save_plan(store,body,*,archive=False):
    from .owner import identifier,text,number
    common={'id','revision','operation_id'}
    fields={'title','decision_ref','plan_type','trigger','steps','risk_limit','stop_condition','review_on','status'}
    if not isinstance(body,dict) or (set(body)!=common if archive else not (common|fields<=set(body)<=common|fields|{'target','strategy'})):raise ValueError('invalid plan fields')
    identifier(body['id']);store._revision(body['revision'])
    if not archive:
        if body['plan_type'] not in ('build_up','rebalance','reduce'):raise ValueError('invalid plan type')
        if body['status'] not in ('draft','ready','paused','completed'):raise ValueError('invalid manual status')
        if not isinstance(body['steps'],list) or not 1<=len(body['steps'])<=12:raise ValueError('invalid steps')
        payload={'title':text(body['title'],120),'plan_type':body['plan_type'],'trigger':text(body['trigger'],4000),'steps':[text(x,2000) for x in body['steps']],'risk_limit':text(body['risk_limit'],4000),'stop_condition':text(body['stop_condition'],4000),'review_on':text(body['review_on'],10),'status':body['status']}
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',payload['review_on']):raise ValueError('invalid review date')
        date.fromisoformat(payload['review_on'])
        if 'target' in body:
            target=body['target']
            if target is not None:
                if body['plan_type']!='build_up' or not isinstance(target,dict) or set(target)!={'account_id','quantity','budget'}:raise ValueError('invalid target')
                target={'account_id':identifier(target['account_id']),'quantity':number(target['quantity'],positive=True),'budget':None if target['budget'] is None else number(target['budget'],positive=True)}
            payload['target']=target
        if 'strategy' in body:
            strategy=body['strategy']
            if strategy is not None:
                if not isinstance(strategy,dict) or set(strategy)!={'anchor_price','base_percent','rules'}:raise ValueError('invalid strategy')
                anchor=number(strategy['anchor_price'],positive=True);base=number(strategy['base_percent'],positive=True)
                if Decimal(base)>100 or not isinstance(strategy['rules'],list) or not 1<=len(strategy['rules'])<=12:raise ValueError('invalid strategy rules')
                rules=[];seen=set()
                for rule in strategy['rules']:
                    if not isinstance(rule,dict) or set(rule)!={'pullback_percent','add_percent','label'}:raise ValueError('invalid rule')
                    pullback=number(rule['pullback_percent'],positive=True);add=number(rule['add_percent'],positive=True)
                    if Decimal(pullback)>=100 or Decimal(add)>100 or Decimal(pullback) in seen:raise ValueError('invalid rule percentages')
                    seen.add(Decimal(pullback));rules.append({'pullback_percent':pullback,'add_percent':add,'label':text(rule['label'],120)})
                strategy={'anchor_price':anchor,'base_percent':base,'rules':rules}
            payload['strategy']=strategy
    with store.transaction() as db:
        fp,old=store._operation(db,body,'plan_archive' if archive else 'plan_save')
        if old is not None:return old
        row=db.execute('SELECT payload,revision FROM documents WHERE id=?',(body['id'],)).fetchone()
        current=json.loads(row[0]) if row else None
        if (row[1] if row else 0)!=body['revision'] or (archive and not row):raise Conflict('plan changed')
        if current and (current['kind']!='plan' or current['archived']):raise Conflict('plan unavailable')
        if archive:result={**current,'archived':True}
        else:
            if 'target' not in body and current:payload['target']=current.get('target')
            if 'strategy' not in body and current:payload['strategy']=current.get('strategy')
            target=payload.get('target')
            if payload.get('strategy') and (not target or payload['plan_type']!='build_up'):raise ValueError('strategy requires build up target')
            if target:
                if payload['plan_type']!='build_up':raise ValueError('target requires build up')
                a=db.execute('SELECT currency FROM accounts WHERE id=?',(target['account_id'],)).fetchone()
                if a is None:raise ValueError('target account missing')
                payload['target']={**target,'currency':a[0]}
                for (raw,) in db.execute('SELECT payload FROM documents'):
                    e=json.loads(raw)
                    if e['kind']=='plan_execution' and e['plan_id']==body['id'] and not e['archived'] and (e['trade']['account_id']!=target['account_id'] or e['trade']['side']!='buy'):raise Conflict('existing execution does not match target')
            ref=body['decision_ref']
            if not isinstance(ref,dict) or set(ref)!={'id','revision'}:raise ValueError('invalid reference')
            if current:
                if ref!=current['decision_ref']:raise Conflict('plan reference is fixed')
                evidence=current['evidence']
            else:
                d=store._document_version(db,ref['id'],ref['revision'])
                active=json.loads(db.execute('SELECT payload FROM documents WHERE id=?',(ref['id'],)).fetchone()[0])
                if d['kind']!='decision' or d['archived'] or active['archived']:raise ValueError('invalid decision reference')
                research=store._document_version(db,**d['research_ref']) if d['research_ref'] else None
                evidence={'decision':d,'research':research}
            result={**payload,'id':body['id'],'kind':'plan','symbol':evidence['decision']['symbol'],'decision_ref':ref,'evidence':evidence,'archived':False}
        result['revision']=body['revision']+1;result['updated_at']=datetime.now(timezone.utc).isoformat()
        encoded=_canonical(result)
        db.execute('INSERT INTO documents VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(body['id'],encoded,result['revision']))
        db.execute('INSERT INTO document_versions VALUES (?,?,?)',(body['id'],result['revision'],encoded))
        store._audit(db,'plan_archived' if archive else 'plan_saved',body['id'],current,result)
        return store._result(db,body,fp,result)


def save_execution(store,body,archive=False,*,_db=None):
    from .owner import identifier,text
    common={'id','revision','operation_id'}
    fields={'plan_id','plan_revision','step_index','trade_id','trade_revision','note'}
    if not isinstance(body,dict) or set(body)!=(common if archive else common|fields):raise ValueError('invalid execution fields')
    identifier(body['id']);store._revision(body['revision'])
    with (store.transaction() if _db is None else nullcontext(_db)) as db:
        fp,old=store._operation(db,body,'execution_archive' if archive else 'execution_link')
        if old is not None:return old
        row=db.execute('SELECT payload,revision FROM documents WHERE id=?',(body['id'],)).fetchone()
        current=json.loads(row[0]) if row else None
        if (row[1] if row else 0)!=body['revision']:raise Conflict('execution changed')
        if archive:
            if not current or current['kind']!='plan_execution' or current['archived']:raise Conflict('execution unavailable')
            result={**current,'archived':True}
        else:
            if current:raise Conflict('execution is immutable; archive and relink')
            identifier(body['plan_id']);identifier(body['trade_id']);store._revision(body['plan_revision']);store._revision(body['trade_revision'])
            row=db.execute('SELECT payload,revision FROM documents WHERE id=?',(body['plan_id'],)).fetchone()
            if row is None or row[1]!=body['plan_revision']:raise Conflict('plan changed')
            plan=json.loads(row[0])
            if plan['kind']!='plan' or plan['archived']:raise ValueError('plan unavailable')
            step=body['step_index']
            if type(step) is not int or not 0<=step<len(plan['steps']):raise ValueError('invalid step')
            row=db.execute('SELECT t.payload,t.revision,a.name,a.currency FROM trades t JOIN accounts a ON a.id=t.account_id WHERE t.id=?',(body['trade_id'],)).fetchone()
            if row is None or row[1]!=body['trade_revision']:raise Conflict('trade changed')
            trade={**json.loads(row[0]),'revision':row[1],'account_name':row[2],'currency':row[3]}
            if plan.get('target') and trade['account_id']!=plan['target']['account_id']:raise ValueError('trade account does not match target')
            if trade['symbol']!=plan['symbol'] or (plan['plan_type']=='build_up' and trade['side']!='buy') or (plan['plan_type']=='reduce' and trade['side']!='sell'):raise ValueError('trade does not match plan')
            for (raw,) in db.execute('SELECT payload FROM documents'):
                record=json.loads(raw)
                if record['kind']=='plan_execution' and not record['archived'] and record['trade']['id']==trade['id']:raise Conflict('trade already linked to a plan')
            result={'id':body['id'],'kind':'plan_execution','title':plan['title'],'plan_id':plan['id'],'plan_revision':plan['revision'],'step_index':step,'step_text':plan['steps'][step],'symbol':plan['symbol'],'trade':trade,'note':text(body['note'],2000),'archived':False}
        result['revision']=body['revision']+1;result['updated_at']=datetime.now(timezone.utc).isoformat();encoded=_canonical(result)
        db.execute('INSERT INTO documents VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(body['id'],encoded,result['revision']))
        db.execute('INSERT INTO document_versions VALUES (?,?,?)',(body['id'],result['revision'],encoded))
        store._audit(db,'plan_execution_archived' if archive else 'plan_execution_linked',body['id'],current,result)
        return store._result(db,body,fp,result)


def record_trade(store,body):
    """Explicitly record an already executed fill and its fixed plan evidence atomically."""
    from .owner import identifier
    fields={'id','trade_id','operation_id','plan_id','plan_revision','step_index','account_id','side','quantity','price','fee','executed_at','note','confirmed'}
    if not isinstance(body,dict) or set(body)!=fields or body['confirmed'] is not True:raise ValueError('explicit confirmation required')
    for key in ('id','trade_id','plan_id'):identifier(body[key])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'plan_trade_record')
        if old is not None:return old
        row=db.execute('SELECT payload,revision FROM documents WHERE id=?',(body['plan_id'],)).fetchone()
        if row is None or row[1]!=body['plan_revision']:raise Conflict('plan changed')
        plan=json.loads(row[0])
        if plan['kind']!='plan' or plan['archived']:raise ValueError('plan unavailable')
        trade={key:body[key] for key in ('account_id','side','quantity','price','fee','executed_at')}
        trade.update(id=body['trade_id'],revision=0,symbol=plan['symbol'],operation_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'plan-trade:'+body['operation_id'])))
        saved=store.trade(trade,_db=db)
        execution=save_execution(store,{'id':body['id'],'revision':0,'operation_id':str(uuid.uuid5(uuid.NAMESPACE_URL,'plan-execution:'+body['operation_id'])),'plan_id':plan['id'],'plan_revision':body['plan_revision'],'step_index':body['step_index'],'trade_id':saved['id'],'trade_revision':saved['revision'],'note':body['note']},_db=db)
        return store._result(db,body,fp,{'trade':saved,'execution':execution})
