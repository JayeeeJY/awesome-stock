"""Immutable, server-built research packets. No model calls or credential storage."""
import json
from decimal import Decimal, localcontext, ROUND_DOWN, ROUND_HALF_UP
from datetime import date
from . import owner_business as b
from . import owner_news as news
from . import owner_company as company
from . import owner_research_memory as memory
from . import owner_research_technical as technical
from . import owner_research_position as position_intelligence
from .owner import identifier
from .local import Conflict

LENSES=('position','business','valuation','momentum','catalysts','risk')


def calculate(store,db,body,receipts=None):
    b.fields(body,'symbol lenses ai_receipt' if isinstance(body,dict) and 'ai_receipt' in body else 'symbol lenses')
    symbol=b.symbol(body['symbol']);lenses=body['lenses']
    if not isinstance(lenses,list) or not lenses or any(not isinstance(x,str) or x not in LENSES for x in lenses) or len(lenses)!=len(set(lenses)):
        raise ValueError('invalid research lenses')
    selected=[x for x in LENSES if x in lenses]
    records=[r for r in b.records(db) if r['kind'] in {'candidate','evidence','note','decision'} and r.get('symbol')==symbol]
    quotes=[r for r in b.records(db,'quote') if r['symbol']==symbol]
    valued=b.valued_accounts(store,db)
    held=[a for a in valued if any(p['symbol']==symbol for p in a['positions'])]
    accounts=[]
    if 'position' in selected:
        for a in valued:
            positions=[p for p in a['positions'] if p['symbol']==symbol]
            if not positions:continue
            # Keep the account denominator and its price provenance, not other trades or notes.
            account={k:a[k] for k in ['id','name','currency','cash','cost_method','estimated_assets','valuation_complete']}
            account['positions']=positions
            account['valuation_basis']=[{'symbol':p['symbol'],'quantity':p['quantity'],'quote':p['quote'],'market_value':p['market_value']} for p in a['positions']]
            accounts.append(account)
    packet={'format':'owner-research-packet-v1','symbol':symbol,'lenses':selected,
            'evaluated_on':b.now().date().isoformat(),'accounts':accounts,'records':records,'quotes':quotes,
            'valuation_scope':'account assets in account currency; no FX aggregation',
            'verified':False}
    packet['market_technical']=technical.calculate(db,symbol,packet['evaluated_on']) if 'momentum' in selected else None
    packet['position_intelligence']=position_intelligence.calculate(store,db,symbol,packet['evaluated_on'],valued) if 'position' in selected else None
    packet['company_source']=company.latest(db,symbol) if any(x in selected for x in ['business','valuation']) else None
    packet['news_source']=news.latest(db,symbol) if any(x in selected for x in ['business','catalysts','risk']) else None
    packet['research_memory']=memory.calculate(db,symbol,packet['evaluated_on'])
    packet['rule_report']=compose(packet,held)
    if 'ai_receipt' in body:packet['rule_report']['ai_synthesis']=bound_synthesis(packet,body['ai_receipt'],receipts or {})
    return packet,b.digest(packet)


def bound_synthesis(packet,receipt_id,receipts):
    if not isinstance(receipt_id,str) or not receipt_id or len(receipt_id)>100:raise ValueError('invalid receipt')
    receipt=receipts.get(receipt_id)
    if not receipt or receipt.get('synthesis',{}).get('status')!='structured' or receipt.get('context',{}).get('task')!='research_synthesis':
        raise Conflict('research generation receipt unavailable')
    try:
        source=json.loads(receipt['context']['context'])
        if not isinstance(source,dict):raise ValueError('source')
        if source.get('symbols')!=[packet['symbol']] or source.get('evaluated_on')!=packet['evaluated_on']:raise ValueError('symbol/date')
        if [q['id'] for q in source['research_questions']]!=packet['lenses']:raise ValueError('lenses')
        keyed=lambda rows:sorted(rows,key=lambda r:r['id'])
        if keyed(source['records'])!=keyed(packet['records']):raise ValueError('records')
        quotes={}
        for q in sorted(packet['quotes'],key=lambda q:(q['as_of'],q['updated_at'],q['id'])):quotes[q['currency']]=q
        expected=list(quotes.values()) if 'momentum' in packet['lenses'] else []
        if keyed(source['price_snapshots'])!=keyed(expected):raise ValueError('quotes')
        expected_technical=packet.get('market_technical')
        if source.get('market_technical')!=expected_technical and source.get('market_technical')!=(technical.context_payload(expected_technical) if expected_technical else None) and (source.get('market_technical') is not None or expected_technical and expected_technical.get('source')):raise ValueError('market history')
        expected_intelligence=packet.get('position_intelligence')
        if source.get('position_intelligence')!=expected_intelligence and (source.get('position_intelligence') is not None or expected_intelligence and expected_intelligence['status']=='ready'):raise ValueError('position intelligence')
        if source.get('news_source')!=packet.get('news_source'):raise ValueError('news source')
        if source.get('company_source')!=packet.get('company_source'):raise ValueError('company source')
        expected_memory=packet.get('research_memory')
        if source.get('research_memory')!=expected_memory and (source.get('research_memory') is not None or expected_memory and (expected_memory['event_count'] or expected_memory.get('earnings_window'))):raise ValueError('research memory')
        expected_positions=[position_source(a,p,packet['evaluated_on']) for a in packet['accounts'] for p in a['positions']]
        actual=source['position_context']
        if not isinstance(actual,list) or sorted(actual,key=lambda p:p['account_id'])!=sorted(expected_positions,key=lambda p:p['account_id']):raise ValueError('positions')
    except (ValueError,KeyError,TypeError,RecursionError):raise Conflict('research generation evidence changed') from None
    # Take values only from the completed in-memory receipt; no user-submitted model result.
    return {k:receipt[k] for k in ['provider','model','generated_at','context','draft','synthesis']}


def position_source(account,position,evaluated_on):
    """Match the exact displayed context, including rounded weight and cost/P&L fields."""
    today=date.fromisoformat(evaluated_on)
    def current(quote):
        return bool(quote and 0<=(today-date.fromisoformat(quote['as_of'])).days<=3)
    fresh=current(position['quote']);value=position['market_value'] if fresh else None
    weight='—';assets=account['estimated_assets']
    if value is not None and assets is not None and Decimal(assets)!=0 and all(current(p['quote']) for p in account['valuation_basis']):
        with localcontext() as ctx:
            ctx.prec=60
            ratio=(Decimal(value)/Decimal(assets)).quantize(Decimal('.000001'),rounding=ROUND_DOWN)
            weight=format((ratio*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),',.2f')+'%'
    return {**position,'market_value':value,'unrealized_pnl':position['unrealized_pnl'] if fresh else None,
            'quote_status':position['quote_status'] if fresh else 'stale' if position['quote'] else 'missing',
            'account_id':account['id'],'account_name':account['name'],'currency':account['currency'],'weight':weight}


def compose(packet,held):
    records=packet['records'];today=packet['evaluated_on']
    decisions=sorted([r for r in records if r['kind']=='decision'],key=lambda r:(r['updated_at'],r['id']),reverse=True)
    decision=decisions[0] if decisions else None
    evidence=[r for r in records if r['kind']=='evidence']
    valid=[r for r in evidence if r['verification']=='verified' and r['expires_on']>=today]
    directional=sorted([r for r in valid if r.get('direction','neutral')!='neutral'],key=lambda r:(r['as_of'],r['updated_at'],r['id']),reverse=True)
    supporting=[r for r in directional if r['direction']=='strengthens']
    counter=[r for r in directional if r['direction']=='weakens']
    weakened=bool(directional and (directional[0]['direction']=='weakens' or len(counter)>len(supporting)))
    intelligence=packet.get('position_intelligence') or {}
    value=intelligence.get('symbol_holdings_usd');total=intelligence.get('total_holdings_usd')
    with localcontext() as ctx:
        ctx.prec=60
        concentrated=bool(value is not None and total is not None and Decimal(total)>0 and Decimal(value)*4>=Decimal(total))
    detail=('最新保存判断「'+decision['title']+'」：'+str(decision.get('content') or '尚未填写论点')+'；失效条件：'+str(decision.get('invalidation') or '待补')) if decision else '尚未保存可追溯的投资判断；先核对持仓、证据缺口与下一步验证。'
    intelligence=packet.get('position_intelligence') or {}
    critical=intelligence.get('risk_level')=='critical' and intelligence.get('signals')
    if critical:posture,headline='risk_review',intelligence['signals'][0]['title']
    elif not held:posture,headline='research_first','先补齐关键证据，再决定是否进入观察清单'
    elif concentrated:posture,headline='risk_review','先复核仓位集中度，再判断个股逻辑'
    elif weakened:posture,headline='thesis_review','最新证据正在削弱原判断，需要复核持仓逻辑'
    elif decision:posture,headline='conditional_watch','已有保存判断，后续行动仍需绑定证据和条件'
    else:posture,headline='needs_thesis','有持仓但缺少保存判断，先补充可证伪的投资逻辑'
    gaps=[r['title']+'：'+('尚未核验' if r['verification']!='verified' else '已过期') for r in evidence if r not in valid]
    if not records:gaps.insert(0,'尚无本地研究材料')
    def fact(metric):
        rows=sorted([r for r in evidence if r['metric']==metric],key=lambda r:(r['as_of'],r['updated_at'],r['id']),reverse=True)
        return rows[0] if rows and rows[0] in valid and rows[0].get('value') is not None else None
    if 'valuation' in packet['lenses']:
        gaps.extend(metric.upper()+' 缺少有效来源' for metric in ['pe','pb'] if not fact(metric))
    actions=[]
    if critical:actions.append(intelligence['signals'][0]['next_step'])
    if weakened:actions.append('复核人工标记为削弱判断的有效证据；方向标记不等于系统已证实原判断失效。')
    if concentrated:actions.append('核对全组合持仓集中度与自己的投资纪律；25%为研究提示线，不替代个人纪律阈值。')
    actions.append('复核已保存判断的支持依据、反方证据和失效条件。' if decision else '记录最关键的支持理由及一条可检验的失效条件。')
    if 'catalysts' in packet['lenses']:actions.append('核对下一项财报或公司事件；复核日期不等于已确认事件日期。')
    if gaps:actions.append('补齐证据缺口，再评估材料是否足以支持判断。')
    return {'formula':'owner-research-rules-v4','summary':{'posture':posture,'headline':headline,'detail':detail},
            'concentration':{'triggered':concentrated,'weight_percent':intelligence.get('weight_percent'),'scope':'全部账户USD持仓市值，不含现金','status':'evaluated' if value is not None and total is not None else 'not_evaluated'},'concentration_threshold_percent':'25','threshold_kind':'research_cue_not_personal_rule',
            'next_actions':actions,'evidence_gaps':gaps,'valid_evidence_count':len(valid),'evidence_count':len(evidence),
            'evidence_balance':{'supporting':len(supporting),'counter':len(counter),'latest_direction':directional[0]['direction'] if directional else None,'needs_thesis_review':weakened,'basis':'user_labeled_verified_unexpired_evidence'},
            'confidence':None,'metrics':{m:fact(m) for m in ['pe','pb','revenue_growth','gross_margin']},'ai_synthesis':None}


def preview(store,body,receipts=None):
    with store.connection() as db:
        db.execute('BEGIN');packet,token=calculate(store,db,body,receipts)
        return {'packet':packet,'token':token,'stored':False}


def save(store,body,receipts=None):
    b.fields(body,'id operation_id input expected_token');identifier(body['id'])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'research_report_save')
        if old is not None:return old
        if db.execute('SELECT 1 FROM documents WHERE id=?',(body['id'],)).fetchone():raise Conflict('research report immutable')
        packet,token=calculate(store,db,body['input'],receipts)
        if token!=body['expected_token']:raise Conflict('research evidence changed')
        result=b._put(store,db,{'id':body['id'],'revision':0},
            {'kind':'research_report','title':packet['symbol']+' · 固定研究材料',
             'input':{k:v for k,v in body['input'].items() if k!='ai_receipt'},'packet':packet,'evidence_token':token})
        return store._result(db,body,fp,result)


def history(store):
    with store.connection() as db:
        return {'reports':sorted(b.records(db,'research_report'),key=lambda r:(r['updated_at'],r['id']),reverse=True)}
