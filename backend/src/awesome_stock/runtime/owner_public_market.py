"""Keyless daily-chart candidate. Fixed origin, explicit queries, no source fallback.

This is an unofficial public interface, not a promise of exchange entitlement.
The release's source-use review is independent of successful network calls.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from awesome_stock.research.market_identity import identity, hong_kong_symbol
from awesome_stock.research.position_intelligence import PositionIntelligenceEngine
from awesome_stock.storage.owner_business import symbol, number, digest


def instrument(sy,market):
    sy=symbol(sy)
    if market=='HK':
        if not hong_kong_symbol(sy):raise ValueError('Hong Kong code required')
        code=sy.zfill(5)
        return dict(symbol=code,provider_symbol=str(int(code)).zfill(4)+'.HK',market='HK',currency='HKD',date_basis='Asia/Hong_Kong')
    row=identity(sy,market)
    if market=='CN':row['provider_symbol']=row['symbol']+('.SS' if row['symbol'].startswith(('60','68')) else '.SZ')
    if market=='US':row['date_basis']='America/New_York'
    return row


def numeric(value,positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float,Decimal)):raise ValueError('invalid number')
    parsed=Decimal(str(value))
    if not parsed.is_finite() or abs(parsed)>=Decimal('1e12'):raise ValueError('invalid number')
    return number(format(parsed.quantize(Decimal('.00000001'),rounding=ROUND_HALF_UP),'f'),positive=positive)


def fetch(send,sy,market,limit,at=None):
    row=instrument(sy,market);at=at or datetime.now(timezone.utc)
    raw=send('query1.finance.yahoo.com','/v8/finance/chart/'+row['provider_symbol']+'?'+urlencode(dict(range='1y',interval='1d')),None)
    try:
        chart=raw['chart']
        if chart.get('error') is not None or not isinstance(chart['result'],list) or len(chart['result'])!=1:raise ValueError('invalid chart')
        result=chart['result'][0];meta=result['meta']
        if meta['symbol']!=row['provider_symbol'] or meta['currency']!=row['currency'] or meta['instrumentType'] not in {'EQUITY','ETF'}:raise ValueError('identity mismatch')
        stamps=result['timestamp'];quotes=result['indicators']['quote']
        if not isinstance(stamps,list) or not 1<=len(stamps)<=400 or not isinstance(quotes,list) or len(quotes)!=1:raise ValueError('invalid bars')
        values=quotes[0]
        if any(not isinstance(values[k],list) or len(values[k])!=len(stamps) for k in ('open','high','low','close','volume')):raise ValueError('misaligned bars')
        zone=ZoneInfo(row['date_basis']);today=at.astimezone(zone).date();regular=meta['currentTradingPeriod']['regular'];end=regular['end']
        if isinstance(end,bool) or not isinstance(end,int):raise ValueError('invalid session')
        rows=[];seen=set()
        for index,stamp in enumerate(stamps):
            if isinstance(stamp,bool) or not isinstance(stamp,int) or stamp<0 or stamp>at.timestamp():raise ValueError('invalid timestamp')
            observed=datetime.fromtimestamp(stamp,zone).date()
            if observed>today or observed.isoformat() in seen:raise ValueError('invalid day')
            seen.add(observed.isoformat())
            # Never turn an unfinished daily bar into a saved closing-price fact.
            if observed==today and at.timestamp()<end:continue
            fields={key:values[key][index] for key in ('open','high','low','close','volume')}
            if any(fields.get(k) is None for k in ('open','high','low','close','volume')):continue
            rows.append(dict(date=observed.isoformat(),**{k:numeric(fields[k],positive=k!='volume') for k in ('open','high','low','close','volume')}))
        if not rows:raise ValueError('no completed bars')
        rows.sort(key=lambda x:x['date']);PositionIntelligenceEngine.normalize_candles(rows)
        return dict(**row,provider='yahoo_public',source='Yahoo Finance public chart / '+row['provider_symbol'],retrieved_at=at.isoformat(),from_date=rows[0]['date'],as_of=rows[-1]['date'],candles=rows[-limit:],received_points=len(rows),received_digest=digest(rows),price_basis='supplier_ohlcv_no_adjclose',precision='8 decimal places, rounded half up',realtime=False,listing_evidence=dict(symbol=meta['symbol'],currency=meta['currency'],instrument_type=meta['instrumentType'],exchange=meta.get('exchangeName')),notice='公共日线接口，非官方承诺服务；不含实时报价或公司/新闻资料。当前未完成交易日不作为收盘快照，缺失行不补造。沿用供应商 OHLCV，未读取 adjclose；复权差异需核对。')
    except (AttributeError,KeyError,TypeError,ValueError,InvalidOperation,OverflowError):
        raise ValueError('public daily data unavailable or identity invalid') from None


def public_transport(path):
    """Use standard system network routing; never redirects or sends credentials."""
    import json
    import re
    import ssl
    from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
    from urllib.error import URLError
    if not re.fullmatch(r'/v8/finance/chart/[A-Z0-9.-]{1,24}\?range=1y&interval=1d',path):raise ValueError('unsupported public path')
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=build_opener(HTTPSHandler(context=ssl.create_default_context()),NoRedirect())
    try:
        with opener.open(Request('https://query1.finance.yahoo.com'+path,headers={'User-Agent':'AwesomeStock/1.0','Accept':'application/json'}),timeout=30) as response:
            if response.status!=200 or int(response.headers.get('Content-Length','0'))>262144:raise ValueError('invalid response size')
            raw=response.read(262145)
            if len(raw)>262144:raise ValueError('response too large')
            result=json.loads(raw,parse_float=Decimal)
            if not isinstance(result,dict):raise ValueError('invalid response')
            return result
    except (URLError,OSError,ValueError):raise ValueError('public network unavailable') from None
