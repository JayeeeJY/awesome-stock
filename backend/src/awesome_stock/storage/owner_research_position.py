"""Native discipline precedence using complete USD holdings and saved policy."""
from decimal import Decimal,localcontext
from . import owner_business as b
from . import owner_research_earnings as earnings
from . import owner_research_news as news
from .owner_constitution import ID
import json


def calculate(store,db,symbol,evaluated_on,accounts=None):
    row=db.execute('SELECT payload FROM documents WHERE id=?',(ID,)).fetchone()
    constitution=json.loads(row[0]) if row else None
    accounts=b.valued_accounts(store,db) if accounts is None else accounts
    rates={r['currency']:r for r in b.records(db,'fx_rate')}
    basis=[];missing=[];held=False
    with localcontext() as ctx:
        ctx.prec=60;total=Decimal(0);selected=Decimal(0)
        for a in accounts:
            if not a['positions']:continue
            fx=rates.get(a['currency']);rate=Decimal(1) if a['currency']=='USD' else Decimal(fx['rate']) if fx and fx['as_of']<=evaluated_on<=fx['expires_on'] else None
            if rate is None:missing.append(a['name']+'：缺少有效USD汇率')
            for p in a['positions']:
                held=held or p['symbol']==symbol
                value=None if p['market_value'] is None or rate is None else Decimal(p['market_value'])*rate
                if p['market_value'] is None:missing.append(a['name']+' / '+p['symbol']+'：价格缺失或过期')
                basis.append({'account_id':a['id'],'account_name':a['name'],'currency':a['currency'],'symbol':p['symbol'],'quantity':p['quantity'],'market_value':p['market_value'],'quote':p['quote'],'fx_evidence':fx if a['currency']!='USD' else None,'market_value_usd':None if value is None else format(value,'f')})
                if value is not None:
                    total+=value
                    if p['symbol']==symbol:selected+=value
        weight=selected/total*100 if not missing and total>0 else None
        signals=[]
        if not constitution:missing.append('尚未保存个人纪律阈值，不采用默认20%/30%')
        if held and weight is not None and constitution:
            policy=constitution['config']['policy'];warning=Decimal(policy['warning_percent']);maximum=Decimal(policy['max_percent'])
            severity='critical' if selected*100>=total*maximum else 'watch' if selected*100>=total*warning else None
            if severity:
                signals.append({'code':'position_above_limit' if severity=='critical' else 'position_concentrated','severity':severity,'title':'仓位达到或超过已保存纪律上限' if severity=='critical' else '仓位达到或超过已保存观察阈值','current_percent':format(weight,'f'),'limit_percent':str(maximum if severity=='critical' else warning),'next_step':'先核对仓位纪律与持仓依据；需要修改阈值时显式保存，不自动执行交易。'})
        result={'evaluated_on':evaluated_on,'formula':'native-position-weight-owner-v3','status':'not_held' if not held else 'unavailable' if weight is None else 'policy_missing' if not constitution else 'ready','symbol':symbol,'scope':'全部账户USD持仓市值占比；不含现金；达到阈值即提示。','weight_percent':None if not held or weight is None else format(weight,'f'),'total_holdings_usd':None if not held or weight is None else format(total,'f'),'symbol_holdings_usd':None if not held or weight is None else format(selected,'f'),'constitution_evidence':constitution if held else None,'valuation_basis':basis if held else [],'signals':signals,'missing':missing if held else [],'risk_level':'critical' if any(s['severity']=='critical' for s in signals) else 'watch' if signals else 'normal' if held and weight is not None and constitution else 'unknown','notice':'本项仅覆盖已保存的仓位观察/上限阈值，不代表全部技术、新闻、财报或自定义纪律已评估。'}

        context_basis=[];context_signals=[]
        for a in accounts:
            for p in a['positions']:
                if p['symbol']!=symbol:continue
                context_basis.append({'account_id':a['id'],'account_name':a['name'],'currency':a['currency'],'quantity':p['quantity'],'open_cost':p['open_cost'],'market_value':p['market_value'],'quote':p['quote']})
                cost=Decimal(p['open_cost']);value=Decimal(p['market_value']) if p['market_value'] is not None else None
                if cost>0 and value is not None and value*100<=cost*90:
                    context_signals.append({'code':'below_cost_line:'+a['id'],'title':a['name']+' · 价格明显低于持仓成本','severity':'watch','detail':'当前持仓市值相对未平仓成本 '+format((value/cost-1)*100,'.2f')+'%；按账户原币核对，不混入汇率收益。','next_step':'先检查买入逻辑是否仍成立，不因摊低成本而机械补仓。'})
        window=earnings.calculate(db,symbol,evaluated_on) if held else None
        if window and window['earnings_status'] in {'critical','watch'}:
            context_signals.append({'code':'earnings_window','title':'预计财报窗口临近 · 未经公告确认','severity':'watch','detail':window['estimated_next_earnings_date']+' · 距评估日 '+str(window['days_to_earnings'])+' 天；推算来源需核对。','next_step':'提前写下预期、关键验证指标和财报后行动条件；先核对真实公告日期。'})
        news_context=news.latest(db,symbol,evaluated_on) if held else None
        if news_context and news_context['freshness']=='fresh' and (news_context['sentiment'] or {}).get('normalized')=='negative':
            context_signals.append({'code':'negative_news','title':'供应商将近期新闻标为负面 · 未人工核验','severity':'watch','detail':news_context['article']['title']+' · '+news_context['article']['published_at'],'next_step':'核对新闻原文及其是否改变原有判断；分类标签本身不证明投资逻辑失效。'})
        return {**result,'news_context':news_context,'context_basis':context_basis,'context_signals':context_signals,'earnings_window':window,
                'notice':'仓位阈值使用已保存纪律；成本提示按各账户原币未平仓成本与有效价格比较。财报窗口是推算，不是公告日期；新闻情绪来自供应商原始标签/分数，未人工核验；自定义纪律不自动解释执行，不代表完整风险评估。'}


def read(store,body):
    b.fields(body,'symbol');symbol=b.symbol(body['symbol'])
    with store.connection() as db:
        db.execute('BEGIN');return calculate(store,db,symbol,b.now().date().isoformat())
