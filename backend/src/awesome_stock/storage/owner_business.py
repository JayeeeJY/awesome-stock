"""Versioned owner workbench objects. Prices are attributed snapshots, not live facts."""
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, localcontext, ROUND_DOWN
import hashlib
import json
import re
from urllib.parse import urlsplit
from .local import Conflict, _canonical
from .owner import identifier, text, number, CURRENCIES

from awesome_stock.research.market_identity import valuation_day

KINDS={'candidate','evidence','quote','rule','action_state','baseline','scenario','allocation_layer'}
METRICS={'revenue_growth','gross_margin','net_debt_ebitda','pe','pb','other'}

def now():return datetime.now(timezone.utc)
def digest(value):return hashlib.sha256(_canonical(value).encode()).hexdigest()
def symbol(value):
    value=text(value,24).upper()
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9.^_-]{0,23}',value):raise ValueError('invalid symbol')
    return value

def day(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('date required')
    return date.fromisoformat(value).isoformat()

def optional(value,limit):
    if not isinstance(value,str) or len(value)>limit or '\x00' in value:raise ValueError('invalid text')
    return value.strip()

def signed(value):
    if not isinstance(value,str) or not re.fullmatch(r'-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?',value):raise ValueError('decimal required')
    return format(Decimal(value),'f')

def fields(body,keys):
    if not isinstance(body,dict) or set(body)!=set(keys.split()):raise ValueError('invalid fields')

def currency(value):
    if value not in CURRENCIES:raise ValueError('invalid currency')
    return value

def records(db,kind=None):
    rows=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents ORDER BY id')]
    return [r for r in rows if not r['archived'] and (kind is None or r['kind']==kind)]

def ledger_snapshot(store,db):
    return [store._account_projection(db,r[0]) for r in db.execute('SELECT id FROM accounts ORDER BY id')]

def snapshot_token(store,db):
    return digest({'ledger':ledger_snapshot(store,db),'documents':records(db)})

def _put(store,db,body,payload):
    result={**payload,'id':body['id'],'revision':body['revision']+1,'updated_at':now().isoformat(),'archived':payload.get('archived',False)}
    encoded=_canonical(result)
    db.execute('INSERT INTO documents VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(body['id'],encoded,result['revision']))
    db.execute('INSERT INTO document_versions VALUES (?,?,?)',(body['id'],result['revision'],encoded))
    store._audit(db,'business_saved',body['id'],None,result)
    return result

def save(store,body,archive=False):
    fields(body,'id revision operation_id' if archive else 'id revision operation_id kind data')
    identifier(body['id']);store._revision(body['revision'])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'business_archive' if archive else 'business_save')
        if old is not None:return old
        row=db.execute('SELECT payload,revision FROM documents WHERE id=?',(body['id'],)).fetchone()
        current=json.loads(row[0]) if row else None
        if (row[1] if row else 0)!=body['revision']:raise Conflict('changed')
        if current and (current['kind'] not in KINDS or current['archived']):raise Conflict('unavailable')
        if archive:
            if not current:raise ValueError('not found')
            result=_put(store,db,body,{**current,'archived':True})
        else:
            kind=body['kind'];data=body['data']
            if kind not in KINDS or (current and current['kind']!=kind):raise ValueError('invalid kind')
            if current and kind in {'baseline','scenario'}:raise Conflict('immutable snapshot')
            payload=validate(store,db,kind,data,current)
            result=_put(store,db,body,{'kind':kind,**payload})
        return store._result(db,body,fp,result)

def validate(store,db,kind,d,current):
    if kind=='allocation_layer':
        fields(d,'account_id title tier sector target_percent target_amount max_single_percent strategy_note symbols stock_pool')
        identifier(d['account_id'])
        if not db.execute('SELECT 1 FROM accounts WHERE id=?',(d['account_id'],)).fetchone():raise ValueError('unknown account')
        if current and current['account_id']!=d['account_id']:raise ValueError('layer account is fixed')
        if type(d['tier']) is not int or not 1<=d['tier']<=10:raise ValueError('tier must be 1..10')
        target=number(d['target_percent']);limit=number(d['max_single_percent'])
        if Decimal(target)>100 or Decimal(limit)>100:raise ValueError('percentage exceeds100')
        lists={}
        for key in ('symbols','stock_pool'):
            if not isinstance(d[key],list) or len(d[key])>100:raise ValueError('invalid symbols')
            values=[symbol(v) for v in d[key]]
            if len(set(values))!=len(values):raise ValueError('duplicate symbol')
            lists[key]=values
        for other in records(db,'allocation_layer'):
            if other['account_id']==d['account_id'] and other['id']!=(current or {}).get('id') and set(other['symbols'])&set(lists['symbols']):raise Conflict('position already assigned to another layer')
        return dict(account_id=d['account_id'],title=text(d['title'],120),tier=d['tier'],sector=optional(d['sector'],80),target_percent=target,target_amount=None if d['target_amount'] is None else number(d['target_amount']),max_single_percent=limit,strategy_note=optional(d['strategy_note'],4000),**lists)
    if kind=='candidate':
        fields(d,'symbol title market thesis review_on')
        if d['market'] not in {'US','HK','CN'}:raise ValueError('invalid market')
        sy=symbol(d['symbol'])
        if any(r['symbol']==sy and r['id']!=(current or {}).get('id') for r in records(db,'candidate')):raise Conflict('duplicate candidate')
        return dict(symbol=sy,title=text(d['title'],120),market=d['market'],thesis=text(d['thesis'],4000),review_on=day(d['review_on']))
    if kind=='evidence':
        fields(d,'symbol title metric value source as_of expires_on verification'+(' direction' if 'direction' in d else ''))
        direction=d.get('direction','neutral')
        if direction not in {'neutral','strengthens','weakens'}:raise ValueError('invalid evidence direction')
        if d['metric'] not in METRICS or d['verification'] not in {'unverified','verified'}:raise ValueError('invalid evidence')
        src=text(d['source'],1000)
        if '://' in src:
            u=urlsplit(src)
            if u.scheme not in {'https','http'} or not u.hostname or u.username or u.password:raise ValueError('invalid source URL')
        a=day(d['as_of']);e=day(d['expires_on'])
        if e<a or a>now().date().isoformat():raise ValueError('invalid observation date')
        return dict(symbol=symbol(d['symbol']),title=text(d['title'],1000),metric=d['metric'],value=None if d['value']=='' else signed(d['value']),source=src,as_of=a,expires_on=e,verification=d['verification'],direction=direction)
    if kind=='quote':
        fields(d,'symbol currency price as_of source'+(' previous_close' if 'previous_close' in d else ''))
        a=day(d['as_of'])
        if a>valuation_day(symbol(d['symbol']),currency(d['currency']),now()).isoformat():raise ValueError('future quote')
        return dict(symbol=symbol(d['symbol']),title=symbol(d['symbol'])+'价格快照',currency=currency(d['currency']),price=number(d['price'],positive=True),as_of=a,source=text(d['source'],300),previous_close=None if d.get('previous_close') in (None,'') else number(d['previous_close'],positive=True))
    if kind=='rule':
        fields(d,'title condition action scope enabled')
        if type(d['enabled']) is not bool:raise ValueError('invalid rule state')
        if current is None and d['enabled']:raise ValueError('new rule starts disabled')
        return dict(title=text(d['title'],120),condition=text(d['condition'],4000),action=text(d['action'],4000),scope=text(d['scope'],120),enabled=d['enabled'])
    if kind=='action_state':
        fields(d,'action_id status reason snooze_until')
        if d['status'] not in {'confirmed','snoozed','resolved','ignored','pending'}:raise ValueError('invalid action status')
        if d['action_id'] not in {a['id'] for a in actions(db)}:raise Conflict('action no longer current')
        if body_id:=next((r['id'] for r in records(db,'action_state') if r['action_id']==d['action_id']),None):
            if body_id!=(current or {}).get('id'):raise Conflict('action already has feedback')
        reason=optional(d['reason'],2000)
        if d['status']=='ignored' and not reason:raise ValueError('ignore reason required')
        until=day(d['snooze_until']) if d['status']=='snoozed' else ''
        if until and until<=now().date().isoformat():raise ValueError('snooze must be future')
        return dict(title=d['action_id'],action_id=d['action_id'],status=d['status'],reason=reason,snooze_until=until)
    if kind=='baseline':
        fields(d,'title')
        return dict(title=text(d['title'],120),accounts=ledger_snapshot(store,db))
    if kind=='scenario':
        fields(d,'title input expected_token')
        if d['expected_token']!=snapshot_token(store,db):raise Conflict('planning evidence changed')
        return dict(title=text(d['title'],120),input=d['input'],result=calculate(store,db,d['input']),ledger_fingerprint=digest(ledger_snapshot(store,db)),price_fingerprint=digest(sorted(quote_map(db).values(),key=lambda q:q['id'])),price_evidence=sorted(quote_map(db).values(),key=lambda q:q['id']))
    raise ValueError('unsupported')

def actions(db):
    result=[];today=now().date().isoformat()
    for d in records(db):
        if d['kind']=='daily_brief':
            result.append({'id':d['id']+'-v'+str(d['revision']),'title':'日报已生成：'+d['captured_at'][:10],
                           'symbol':'','source_id':d['id'],'source_revision':d['revision'],
                           'updated_at':d['updated_at'],'due_on':d['captured_at'][:10],'priority':'P2',
                           'reason':'本地事实日报已保存；资料状态：'+{'complete':'齐全','partial':'不完整','unavailable':'不可用'}.get(d['facts']['status'],'未知'),
                           'next_step':'打开固定日报核对依据，阅读后可标记已解决。','href':'/review/diagnosis'})
            continue
        if d['kind'] not in {'decision','plan','candidate'} or not d.get('review_on') or d['review_on']>today:continue
        if d.get('status')=='completed':continue
        result.append({'id':d['id']+'-v'+str(d['revision']),'title':'复核：'+d['title'],'symbol':d.get('symbol',''),'source_id':d['id'],'source_revision':d['revision'],'updated_at':d['updated_at'],'due_on':d['review_on'],'priority':'P1','reason':'已到你设置的复核日期','next_step':'打开原记录，核对证据并更新判断或复核日期。','href':{'decision':'/decisions','plan':'/plans','candidate':'/screening'}[d['kind']]})
    return sorted(result,key=lambda a:(a['due_on'],a['id']))

def quote_map(db):
    out={}
    for q in sorted(records(db,'quote'),key=lambda q:(q['as_of'],q['updated_at'],q['id'])):out[(q['symbol'],q['currency'])]=q
    return out

def valued_accounts(store,db):
    quotes=quote_map(db);result=[]
    with localcontext() as ctx:
        ctx.prec=60
        for a in ledger_snapshot(store,db):
            positions=[];complete=True;total=Decimal(a['cash'])
            for h in a['holdings']:
                if Decimal(h['quantity'])==0:continue
                q=quotes.get((h['symbol'],a['currency']));fresh=q and 0<=(valuation_day(h['symbol'],a['currency'],now())-date.fromisoformat(q['as_of'])).days<=3
                value=Decimal(h['quantity'])*Decimal(q['price']) if fresh else None
                if value is None:complete=False
                else:total+=value
                day_change=Decimal(h['quantity'])*(Decimal(q['price'])-Decimal(q['previous_close'])) if fresh and q.get('previous_close') is not None and q['as_of']==valuation_day(h['symbol'],a['currency'],now()).isoformat() else None
                positions.append({**h,'day_price_effect':None if day_change is None else format(day_change,'f'),'quote':q,'quote_status':'current_snapshot' if fresh else 'stale' if q else 'missing','market_value':None if value is None else format(value,'f'),'unrealized_pnl':None if value is None else format(value-Decimal(h['open_cost']),'f')})
            result.append({**a,'positions':positions,'estimated_assets':format(total,'f') if complete else None,'valuation_complete':complete})
    return result

def workspace(store):
    with store.connection() as db:
        db.execute('BEGIN');rows=records(db);accounts=valued_accounts(store,db);acts=actions(db)
        held={(p['symbol'],a['currency']) for a in accounts for p in a['positions']}
        company_sources={}
        for source in sorted((r for r in rows if r['kind']=='company_snapshot'),key=lambda r:(r['updated_at'],r['id'])):
            key=(source['symbol'],source['currency'])
            name=source.get('company',{}).get('name')
            if key in held and name:
                company_sources[source['symbol']+'|'+source['currency']]={'name':name,'source':source['source'],'retrieved_at':source['retrieved_at'],'verification':source['verification'],'id':source['id'],'revision':source['revision']}
        states={r['action_id']:r for r in rows if r['kind']=='action_state'}
        for a in acts:
            a['feedback']=states.get(a['id']);a['status']=states.get(a['id'],{}).get('status','pending')
            a['snooze_due']=a['status']=='snoozed' and a['feedback']['snooze_until']<=now().date().isoformat()
            if a['snooze_due']:a['status']='pending'
        baselines=sorted([r for r in rows if r['kind']=='baseline'],key=lambda r:r['updated_at'])
        delta=[]
        if baselines:
            old={a['id']:a for a in baselines[-1]['accounts']};current={a['id']:a for a in accounts}
            for id in sorted(old.keys()|current.keys()):
                before=old.get(id);after=current.get(id)
                if not before or not after:delta.append({'account_id':id,'account_name':(after or before)['name'],'currency':(after or before)['currency'],'status':'new' if after else 'removed','cash_change':None,'cost_change':None,'quantities':[]});continue
                qty=lambda a:{h['symbol']:Decimal(h['quantity']) for h in a['holdings']}
                x=qty(before);y=qty(after)
                with localcontext() as ctx:
                    ctx.prec=60
                    delta.append({'account_id':id,'account_name':after['name'],'currency':after['currency'],'status':'compared','cash_change':str(Decimal(after['cash'])-Decimal(before['cash'])),'cost_change':str(sum((Decimal(h['open_cost']) for h in after['holdings']),Decimal(0))-sum((Decimal(h['open_cost']) for h in before['holdings']),Decimal(0))),'quantities':[{'symbol':sy,'change':str(y.get(sy,Decimal(0))-x.get(sy,Decimal(0)))} for sy in sorted(x.keys()|y.keys())]})
        versions=[json.loads(r[0]) for r in db.execute('SELECT payload FROM document_versions ORDER BY id,revision')]
        from .owner_fx import calculate as base_valuation
        converted=base_valuation(db,accounts);converted.pop('native_accounts')
        return {'base_valuation':converted,'company_sources':company_sources,'daily_index':[{'id':r['id'],'account_id':r['account_id']} for r in rows if r['kind']=='daily_brief'],'records':[r for r in rows if r['kind'] in KINDS],'versions':[r for r in versions if r['kind'] in KINDS],'accounts':accounts,'actions':acts,'baseline':baselines[-1] if baselines else None,'changes':delta,'token':snapshot_token(store,db),'ledger_fingerprint':digest(ledger_snapshot(store,db)),'price_fingerprint':digest(sorted(quote_map(db).values(),key=lambda q:q['id'])),'executes_trades':False}

def screen(store,body):
    fields(body,'market growth_min margin_min debt_max')
    if body['market'] not in {'ALL','US','HK','CN'}:raise ValueError('invalid market')
    limits={k:Decimal(signed(body[k])) for k in ('growth_min','margin_min','debt_max')}
    with store.connection() as db:
        db.execute('BEGIN');ev=records(db,'evidence');result=[]
        for c in records(db,'candidate'):
            if body['market']!='ALL' and c['market']!=body['market']:continue
            facts={};gaps=[];reasons=[]
            for metric,limit,minimum in [('revenue_growth','growth_min',True),('gross_margin','margin_min',True),('net_debt_ebitda','debt_max',False)]:
                matching=sorted([e for e in ev if e['symbol']==c['symbol'] and e['metric']==metric],key=lambda e:(e['as_of'],e['updated_at']))
                e=matching[-1] if matching else None
                facts[metric]=e
                if not e or e['value'] is None or e['verification']!='verified' or e['expires_on']<now().date().isoformat():gaps.append(metric);continue
                if (Decimal(e['value'])<limits[limit] if minimum else Decimal(e['value'])>limits[limit]):reasons.append(metric)
            result.append({'candidate':c,'facts':facts,'gaps':gaps,'outside_threshold':reasons,'status':'excluded' if reasons else 'needs_evidence' if gaps else 'matched'})
        return {'rows':result,'rules':body,'ranked':False,'scope':'personal_candidates'}

def handoff(store,body):
    fields(body,'id operation_id candidate_ids expected_token')
    identifier(body['id'])
    if not isinstance(body['candidate_ids'],list) or not 1<=len(body['candidate_ids'])<=4 or len(set(body['candidate_ids']))!=len(body['candidate_ids']):raise ValueError('select one to four')
    with store.transaction() as db:
        fp,old=store._operation(db,body,'research_handoff')
        if old is not None:return old
        if body['expected_token']!=snapshot_token(store,db):raise Conflict('evidence changed')
        pool={r['id']:r for r in records(db,'candidate')};ev=records(db,'evidence');saved=[]
        for i,id in enumerate(body['candidate_ids']):
            c=pool.get(id)
            if c is None:raise ValueError('unknown candidate')
            note_id='handoff-'+digest([body['id'],id])[:48]
            if db.execute('SELECT 1 FROM documents WHERE id=?',(note_id,)).fetchone():raise Conflict('handoff identifier already used')
            content=handoff_note_content(c,[e for e in ev if e['symbol']==c['symbol']])
            if len(content)>20000:raise ValueError('handoff too large')
            payload={'kind':'note','title':c['title']+' · 候选交接','symbol':c['symbol'],'content':content,'support':'','counter_case':'','invalidation':'','risk_limit':'','review_on':'','research_ref':None}
            saved.append(_put(store,db,{'id':note_id,'revision':0},payload))
        return store._result(db,body,fp,{'notes':saved})

def handoff_note_content(candidate,evidence):
    labels={'revenue_growth':'营收增长 %','gross_margin':'毛利率 %','net_debt_ebitda':'净债务 / EBITDA','pe':'市盈率 P/E','pb':'市净率 P/B','other':'其他'}
    directions={'strengthens':'支持判断','weakens':'削弱判断','neutral':'未标记 / 中性'}
    lines=[
        '候选交接快照 · 仅供继续研究，不是投资建议',
        f"标的：{candidate['symbol']} · {candidate['title']}",
        f"市场：{candidate['market']}",
        f"观察逻辑：{candidate['thesis']}",
        f"复核日期：{candidate['review_on']}",
        f"候选记录：{candidate['id']} · v{candidate['revision']}",
        '',
        f'证据快照（{len(evidence)} 条；缺失、过期或未核验材料不视为有效证据）',
    ]
    if not evidence:lines.append('尚无已保存证据，请先补充来源与复核日期。')
    for index,item in enumerate(evidence,1):
        lines.extend([
            f"{index}. {item['title']} · {labels.get(item['metric'],item['metric'])}：{item['value'] if item['value'] is not None else '缺失'}",
            f"   核验：{'人工已核验' if item['verification']=='verified' else '未核验'} · 方向：{directions.get(item.get('direction','neutral'),'未标记 / 中性')}",
            f"   来源：{item['source']} · 观察：{item['as_of']} · 截止：{item['expires_on']}",
            f"   证据记录：{item['id']} · v{item['revision']}",
        ])
    lines.extend(['','固定交接快照；后续更正候选或证据不会改写此版本，也不会因交接自动变成已核验。'])
    return '\n'.join(lines)

def calculate(store,db,b,_account=None):
    if not isinstance(b,dict) or b.get('type') not in {'allocation','layer_allocation','build_up','pre_trade','pre_trade_batch'}:raise ValueError('invalid scenario')
    a=_account if _account is not None else next((x for x in valued_accounts(store,db) if x['id']==b.get('account_id')),None)
    if a is None:raise ValueError('account missing')
    if not a['valuation_complete']:raise ValueError('complete recent price snapshots required')
    with localcontext() as ctx:
        ctx.prec=60
        assets=Decimal(a['estimated_assets']);cash=Decimal(a['cash'])
        if assets<=0:raise ValueError('positive assets required')
        base={'type':b['type'],'currency':a['currency'],'account_id':a['id'],'assets_before':str(assets),'cash_before':str(cash),'executes_trades':False,'valuation':'attributed_price_snapshots'}
        if b['type']=='pre_trade_batch':
            fields(b,'type account_id trades')
            trades=b['trades']
            if not isinstance(trades,list) or not 1<=len(trades)<=20:raise ValueError('1..20 trades required')
            state={**a,'positions':[dict(p) for p in a['positions']]};rows=[];issues=[]
            for index,entry in enumerate(trades):
                fields(entry,'symbol side quantity price fee max_percent')
                result=calculate(store,db,{'type':'pre_trade','account_id':a['id'],**entry},state)
                rows.append({'stage':index+1,'symbol':result['symbol'],'side':entry['side'],'quantity':entry['quantity'],'price':entry['price'],'fee':entry['fee'],'cash_after':result['cash_after'],'weight_after':result['weight_after'],'status':result['status']})
                if result['issues']:
                    issues=[f"第{index+1}笔：{issue}" for issue in result['issues']];break
                state['cash']=result['cash_after'];state['estimated_assets']=result['estimated_assets_after']
                existing=next((p for p in state['positions'] if p['symbol']==result['symbol']),None)
                if existing is None:
                    existing={'symbol':result['symbol'],'quote':{'price':result['mark_price']}};state['positions'].append(existing)
                existing.update(quantity=result['quantity_after'],market_value=result['position_value_after'])
            return {**base,'rows':rows,'trade_count':len(trades),'evaluated_count':len(rows),'cash_after':state['cash'],'estimated_assets_after':state['estimated_assets'],'issues':issues,'status':'blocked' if issues else 'passed','sequence_complete':not issues,'valuation_assumption':'Existing holdings use their snapshots; each new symbol keeps its first entered price throughout this sequence.'}
        if b['type']=='layer_allocation':
            fields(b,'type account_id cash_percent')
            layers=sorted((r for r in records(db,'allocation_layer') if r['account_id']==a['id']),key=lambda r:(r['tier'],r['id']))
            cash_target=Decimal(number(b['cash_percent']))
            if not layers or cash_target>100 or sum((Decimal(r['target_percent']) for r in layers),cash_target)!=100:raise ValueError('layer and cash targets must total100')
            rows=[];assigned=set()
            def allocation_row(label,current,target,**extra):
                return {'symbol':label,'current_value':str(current),'target_percent':str(target),'current_percent':str(current/assets*100),'adjustment_value':str(assets*target/100-current),**extra}
            for layer in layers:
                assigned.update(layer['symbols'])
                value=sum((Decimal(h['market_value']) for h in a['positions'] if h['symbol'] in layer['symbols']),Decimal(0))
                rows.append(allocation_row(layer['title'],value,Decimal(layer['target_percent']),layer_id=layer['id'],layer_revision=layer['revision']))
            unassigned=sum((Decimal(h['market_value']) for h in a['positions'] if h['symbol'] not in assigned),Decimal(0))
            rows.append(allocation_row('未分层持仓',unassigned,Decimal(0)))
            rows.append(allocation_row('现金',cash,cash_target))
            return {**base,'rows':rows,'layer_evidence':layers,'status':'preview','allocation_basis':'Saved percentage targets; target_amount is reference only. Positive gaps are target shortfalls, not orders.'}
        if b['type']=='allocation':
            fields(b,'type account_id targets')
            targets=b['targets'];values={h['symbol']:Decimal(h['market_value']) for h in a['positions']};values['@CASH']=cash
            if not isinstance(targets,dict) or not 1<=len(targets)<=100 or set(values)-set(targets):raise ValueError('all holdings and @CASH required')
            weights={('@CASH' if k=='@CASH' else symbol(k)):Decimal(number(v)) for k,v in targets.items()}
            if len(weights)!=len(targets) or sum(weights.values())!=100:raise ValueError('weights must total 100')
            return {**base,'rows':[{'symbol':sy,'current_value':str(values.get(sy,Decimal(0))),'target_percent':str(w),'current_percent':str(values.get(sy,Decimal(0))/assets*100),'adjustment_value':str(assets*w/100-values.get(sy,Decimal(0)))} for sy,w in weights.items()],'status':'preview'}
        sy=symbol(b.get('symbol'));h=next((h for h in a['positions'] if h['symbol']==sy),None)
        current_qty=Decimal(h['quantity']) if h else Decimal(0);current_value=Decimal(h['market_value']) if h else Decimal(0)
        price=Decimal(number(b.get('price'),positive=True));fee=Decimal(number(b.get('fee')));limit=Decimal(number(b.get('max_percent'),positive=True))
        if limit>100:raise ValueError('max percent exceeds100')
        if b['type']=='build_up':
            fields(b,'type account_id symbol price fee max_percent budget stages')
            budget=Decimal(number(b['budget'],positive=True));stages=b['stages']
            if type(stages) is not int or not 1<=stages<=12:raise ValueError('stages 1..12')
            quantity=max(Decimal(0),((budget/stages-fee)/price).to_integral_value(rounding=ROUND_DOWN));gross=quantity*price;spend=(gross+fee if quantity else Decimal(0))*stages
            mark=Decimal(h['quote']['price']) if h else price
            post_value=current_value+quantity*mark*stages;post_assets=assets-current_value+post_value-spend
            weight=post_value/post_assets*100 if post_assets>0 else None
            issues=[]
            if budget>cash or spend>cash:issues.append('现金不足')
            if not quantity:issues.append('单批预算不足以购买一股及费用')
            if weight is None or weight>limit:issues.append('超过用户仓位上限或净资产非正')
            return {**base,'symbol':sy,'rows':[{'stage':i+1,'quantity':str(quantity),'price':str(price),'fee':str(fee if quantity else 0),'required_cash':str(gross+fee if quantity else 0)} for i in range(stages)],'planned_cash':str(spend),'unallocated_budget':str(budget-spend),'cash_after':str(cash-spend),'weight_after':None if weight is None else str(weight),'issues':issues,'status':'blocked' if issues else 'ready_for_review'}
        fields(b,'type account_id symbol side quantity price fee max_percent')
        if b['side'] not in {'buy','sell'}:raise ValueError('invalid side')
        qty=Decimal(number(b['quantity'],positive=True));buy=b['side']=='buy';post_qty=current_qty+qty if buy else current_qty-qty;post_cash=cash-qty*price-fee if buy else cash+qty*price-fee
        # Existing position is valued at the disclosed snapshot; new position uses entered execution assumption.
        mark=Decimal(h['quote']['price']) if h else price;post_value=post_qty*mark;post_assets=assets-current_value+post_value+(post_cash-cash)
        weight=post_value/post_assets*100 if post_assets>0 and post_qty>=0 else None
        issues=[]
        if post_qty<0:issues.append('卖出数量超过持仓')
        if post_cash<0:issues.append('现金不足（含费用）')
        if weight is None:issues.append('无法计算有效交易后仓位')
        elif weight>limit:issues.append('超过用户仓位上限')
        return {**base,'symbol':sy,'cash_after':str(post_cash),'quantity_after':str(post_qty),'estimated_assets_after':str(post_assets),'position_value_after':str(post_value),'mark_price':str(mark),'weight_after':None if weight is None else str(weight),'issues':issues,'status':'blocked' if issues else 'passed'}

def preview_plan(store,body):
    with store.connection() as db:
        db.execute('BEGIN')
        return {'result':calculate(store,db,body),'token':snapshot_token(store,db)}

def trends(store,body):
    fields(body,'from to');start=day(body['from']);end=day(body['to'])
    if start>end:raise ValueError('invalid range')
    with store.connection() as db:
        db.execute('BEGIN');reviews=[r for r in records(db,'review') if start<=r['reviewed_on']<=end];months={}
        for r in reviews:
            month=r['reviewed_on'][:7];m=months.setdefault(month,{'month':month,'total':0,'followed':0,'deviated':0,'unclear':0,'observed':0,'pending':0,'record_ids':[]})
            m['total']+=1;m[r['process_status']]+=1;m[r['outcome_status']]+=1;m['record_ids'].append(r['id'])
        return {'from':start,'to':end,'total':len(reviews),'months':[months[k] for k in sorted(months)],'records':reviews,'performance_score':None,'basis':'每条当前有效复盘计一次；版本和归档不重复计数。过程判断与结果已知分别统计，不推导收益率。'}


def assign_position(store,body):
    fields(body,'operation_id account_id symbol layer_id expected_token')
    identifier(body['account_id']);sy=symbol(body['symbol'])
    if body['layer_id'] is not None:identifier(body['layer_id'])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'allocation_assign')
        if old is not None:return old
        if body['expected_token']!=snapshot_token(store,db):raise Conflict('allocation evidence changed')
        if not db.execute('SELECT 1 FROM accounts WHERE id=?',(body['account_id'],)).fetchone():raise ValueError('account missing')
        account=store._account_projection(db,body['account_id'])
        if not any(h['symbol']==sy and Decimal(h['quantity'])>0 for h in account['holdings']):raise ValueError('current holding required')
        layers=[r for r in records(db,'allocation_layer') if r['account_id']==body['account_id']]
        target=next((r for r in layers if r['id']==body['layer_id']),None)
        if body['layer_id'] is not None and target is None:raise ValueError('active layer from same account required')
        if target and sy not in target['symbols'] and len(target['symbols'])>=100:raise ValueError('layer capacity exceeded')
        changed=[]
        for layer in layers:
            symbols=[s for s in layer['symbols'] if s!=sy]
            if layer['id']==body['layer_id']:symbols.append(sy)
            if set(symbols)!=set(layer['symbols']):changed.append(_put(store,db,{'id':layer['id'],'revision':layer['revision']},{**layer,'symbols':symbols}))
        return store._result(db,body,fp,{'changed':changed,'symbol':sy,'layer_id':body['layer_id']})
