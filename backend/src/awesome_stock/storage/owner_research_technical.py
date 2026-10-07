"""Derived market indicators bound to one saved daily-source snapshot."""
from datetime import date
from awesome_stock.research.market_identity import china_a_symbol, hong_kong_symbol, valuation_day
from . import owner_business as b
from awesome_stock.research.position_intelligence import PositionIntelligenceEngine

NOTICE='日线未复权，拆股分红可能造成跳变。技术指标和条件提示不是投资结论；仅覆盖动量、支撑压力与趋势，不包含仓位纪律或历史汇率收益，不自动执行交易。'


def calculate(db,symbol,evaluated_on):
    sources=sorted([r for r in b.records(db,'market_history') if r['symbol']==symbol and ((r['market']=='US' and r['currency']=='USD' and not china_a_symbol(symbol) and not hong_kong_symbol(symbol)) or (r['market']=='CN' and r['currency']=='CNY' and china_a_symbol(symbol)) or (r['market']=='HK' and r['currency']=='HKD' and hong_kong_symbol(symbol)))],key=lambda r:(r['updated_at'],r['id']),reverse=True)
    result={'formula':'native-technical-owner-v3','evaluated_on':evaluated_on,'status':'missing','source':sources[0] if sources else None,'technical':None,'market_signals':[],'data_quality':None,'notice':NOTICE}
    if not sources:return result
    source=sources[0]
    if source.get('price_basis')=='supplier_ohlcv_no_adjclose':result['notice']='本来源沿用供应商 OHLCV，未读取 adjclose；不能视为已核验的未复权或全复权价格。'+NOTICE.split('。',1)[1]
    if source.get('volume_basis')=='split_adjusted':result['notice']=NOTICE+' 本来源价格未复权，成交量由供应商按拆股调整，量比沿用该口径。'
    evaluation_day=valuation_day(symbol,source['currency'],b.now()).isoformat() if source['market'] in {'CN','HK'} else evaluated_on
    result['market_evaluated_on']=evaluation_day
    age=(date.fromisoformat(evaluation_day)-date.fromisoformat(source['as_of'])).days
    if not 0<=age<=3:return {**result,'status':'stale'}
    # Only expose market calculations here. Engine defaults for unknown weight
    # or discipline must not become claims about the user's position.
    report=PositionIntelligenceEngine().analyze(ticker=symbol,position={'current_price':source['candles'][-1]['close']},history=source['candles'])
    return {**result,'status':report['status'],'technical':report['technical'],'data_quality':report['data_quality'],'market_signals':[s for s in report['signals'] if s['category'] in {'momentum','price_structure','trend'}]}


def context_payload(result):
    """Model receives indicators and immutable source identity, not all candle rows."""
    source=result.get('source')
    if not source:return result
    return {**result,'source':{**{k:v for k,v in source.items() if k!='candles'},'candle_count':len(source['candles']),'candles_digest':b.digest(source['candles'])}}


def read(store,body):
    b.fields(body,'symbol');symbol=b.symbol(body['symbol'])
    with store.connection() as db:
        db.execute('BEGIN')
        result=calculate(db,symbol,b.now().date().isoformat())
        return {**result,'assistant_context':context_payload(result)}
