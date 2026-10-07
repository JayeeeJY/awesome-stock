"""User-entered USD conversion evidence; no fallback rates or external requests."""
import json
from decimal import Decimal, localcontext
from uuid import uuid5,NAMESPACE_URL
from . import owner_business as b
from .owner import number,text,CURRENCIES
from .local import Conflict
from ..research.market_identity import china_a_symbol,hong_kong_symbol
from zoneinfo import ZoneInfo


def rate_id(currency):return str(uuid5(NAMESPACE_URL,'awesome-owner-fx-to-usd:'+currency))


def save(store,body):
    b.fields(body,'operation_id revision currency rate as_of expires_on source')
    currency=body['currency']
    if not isinstance(currency,str) or currency not in CURRENCIES or currency=='USD':raise ValueError('invalid source currency')
    store._revision(body['revision']);rate=number(body['rate'],positive=True)
    observed=b.day(body['as_of']);expires=b.day(body['expires_on'])
    if observed>b.now().date().isoformat() or expires<observed:raise ValueError('invalid rate dates')
    source=text(body['source'],300);identifier=rate_id(currency)
    with store.transaction() as db:
        fp,old=store._operation(db,body,'fx_rate_save')
        if old is not None:return old
        current=db.execute('SELECT revision FROM documents WHERE id=?',(identifier,)).fetchone()
        if (current[0] if current else 0)!=body['revision']:raise Conflict('exchange rate changed')
        result=b._put(store,db,{'id':identifier,'revision':body['revision']},
                      {'kind':'fx_rate','title':currency+' → USD','currency':currency,'quote_currency':'USD',
                       'rate':rate,'as_of':observed,'expires_on':expires,'source':source,'origin':'user_entered'})
        return store._result(db,body,fp,result)


def history(store):
    with store.connection() as db:
        versions=[json.loads(row[0]) for row in db.execute('SELECT payload FROM document_versions ORDER BY revision DESC')]
        return {'rates':sorted(b.records(db,'fx_rate'),key=lambda r:r['currency']),
                'versions':[r for r in versions if r['kind']=='fx_rate'],'rate_convention':'USD per 1 unit of source currency'}


def valuation(store):
    with store.connection() as db:
        db.execute('BEGIN')
        return calculate(db,b.valued_accounts(store,db))


def calculate(db,native_accounts):
    """Convert the supplied native snapshot inside the caller's read transaction."""
    at=b.now();today=at.date().isoformat();market_dates={'UTC':today}
    for a in native_accounts:
        zone='Asia/Shanghai' if a['currency']=='CNY' and any(china_a_symbol(p['symbol']) for p in a['positions']) else 'Asia/Hong_Kong' if a['currency']=='HKD' and any(hong_kong_symbol(p['symbol']) for p in a['positions']) else None
        if zone:market_dates[zone]=at.astimezone(ZoneInfo(zone)).date().isoformat()
    rates={r['currency']:r for r in b.records(db,'fx_rate')};rows=[]
    with localcontext() as ctx:
        ctx.prec=60
        for a in native_accounts:
            evidence=rates.get(a['currency'])
            status='identity' if a['currency']=='USD' else 'missing' if not evidence else 'current' if evidence['as_of']<=today<=evidence['expires_on'] else 'stale'
            rate=Decimal('1') if status=='identity' else Decimal(evidence['rate']) if status=='current' else None
            def convert(value):
                if value is None:return None
                amount=Decimal(value)
                if amount==0:return '0'
                return format(amount*rate,'f') if rate is not None else None
            holdings=sum((Decimal(p['market_value']) for p in a['positions']),Decimal(0)) if a['valuation_complete'] else None
            gain=(sum((Decimal(p['realized_pnl']) for p in a['holdings']),Decimal(0))+sum((Decimal(p['unrealized_pnl']) for p in a['positions']),Decimal(0))) if a['valuation_complete'] else None
            rows.append({'account_id':a['id'],'name':a['name'],'currency':a['currency'],'fx_status':status,'fx_evidence':evidence,
                         'holdings_value_usd':convert(holdings),'assets_value_usd':convert(a['estimated_assets']),
                         'day_price_effect_usd':convert(sum((Decimal(p['day_price_effect']) for p in a['positions']),Decimal(0))) if all(p['day_price_effect'] is not None for p in a['positions']) else None,'cash_usd':convert(a['cash']),'realized_at_current_fx_usd':convert(sum((Decimal(p['realized_pnl']) for p in a['holdings']),Decimal(0))),'unrealized_at_current_fx_usd':convert(sum((Decimal(p['unrealized_pnl']) for p in a['positions']),Decimal(0)) if a['valuation_complete'] else None),'positions':[{'symbol':p['symbol'],'market_value_usd':convert(p['market_value']),'total_return_at_current_fx_usd':convert(Decimal(p['realized_pnl'])+Decimal(p['unrealized_pnl'])) if p['unrealized_pnl'] is not None else None} for p in a['positions']],'total_return_at_current_fx_usd':convert(gain),'price_complete':a['valuation_complete']})
        complete=all(r['holdings_value_usd'] is not None for r in rows)
        total=sum((Decimal(r['holdings_value_usd']) for r in rows),Decimal(0)) if complete else None
        ranked=sorted(rows,key=lambda r:(-Decimal(r['holdings_value_usd'] or '0'),r['account_id']))
        lead=ranked[0]['account_id'] if complete and total and total>0 else None
    return {'base_currency':'USD','evaluated_on':today,'evaluated_market_dates':market_dates,'accounts':rows,'native_accounts':native_accounts,'holdings_complete':complete,
            'total_holdings_usd':None if total is None else format(total,'f'),'lead_account_id':lead,
            'return_basis':'Native ledger P&L converted at the recorded current rate; excludes historical FX gain/loss.',
            'external_calls':False,'executes_trades':False}
