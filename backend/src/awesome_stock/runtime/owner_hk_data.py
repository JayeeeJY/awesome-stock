"""User-authorized EODHD Hong Kong daily data. Fixed destinations, two requests.

First verify listing identity and HKD currency; then fetch bounded daily rows.
Prices are raw. Provider volume is split-adjusted and is labelled separately.
"""
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode
from awesome_stock.research.market_identity import hong_kong_symbol, valuation_day
from awesome_stock.research.position_intelligence import PositionIntelligenceEngine
from awesome_stock.storage.owner import number, text
from awesome_stock.storage.owner_business import day, digest


def numeric(value, *, positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float,str,Decimal)):
        raise ValueError('invalid numeric source')
    amount=Decimal(str(value))
    if not amount.is_finite():raise ValueError('nonfinite value')
    return number(format(amount,'f'),positive=positive)


def fetch(send,key,symbol,at,limit):
    if not hong_kong_symbol(symbol):raise ValueError('Hong Kong code required')
    code=symbol.zfill(5);remote=str(int(code)).zfill(4)
    metadata=send('eodhd.com','/api/exchange-symbol-list/HK?'+urlencode(
        {'symbols':remote,'api_token':key,'fmt':'json'}),None)
    if not isinstance(metadata,list) or len(metadata)!=1:raise ValueError('listing unavailable')
    listing=metadata[0]
    if not isinstance(listing,dict) or listing.get('Code')!=remote or listing.get('Exchange') not in {'HK','HKEX'} or listing.get('Currency')!='HKD' or listing.get('Type') not in {'Common Stock','Preferred Stock','ETF','FUND'}:
        raise ValueError('listing identity mismatch')
    evidence={k:text(listing[k],200) for k in ['Code','Name','Exchange','Currency','Type']}
    evidence['Name']=evidence['Name'].replace(key,'[REDACTED]')
    # Do not save provider URLs: query parameters contain the user's token.
    today=valuation_day(code,'HKD',at);first=today-timedelta(days=30 if limit==2 else 200 if limit==100 else 550)
    raw=send('eodhd.com','/api/eod/'+remote+'.HK?'+urlencode(
        {'api_token':key,'fmt':'json','period':'d','order':'a','from':first.isoformat(),'to':today.isoformat()}),None)
    if not isinstance(raw,list) or not 1<=len(raw)<=(today-first).days+1:raise ValueError('invalid history size')
    rows=[];seen=set()
    for row in raw:
        if not isinstance(row,dict):raise ValueError('invalid candle')
        date=day(row['date'])
        if not first.isoformat()<=date<=today.isoformat() or date in seen:raise ValueError('invalid history date')
        seen.add(date)
        rows.append({'date':date,**{k:numeric(row[k],positive=k!='volume') for k in ['open','high','low','close','volume']}})
    rows.sort(key=lambda r:r['date']);PositionIntelligenceEngine.normalize_candles(rows)
    received=len(rows);fingerprint=digest(rows);rows=rows[-limit:]
    return {'symbol':code,'provider_symbol':remote+'.HK','market':'HK','currency':'HKD','provider':'eodhd',
            'source':'EODHD daily / '+remote+'.HK / '+evidence['Name']+' / HKD','date_basis':'Asia/Hong_Kong','listing_evidence':evidence,
            'price_basis':'raw_unadjusted','volume_basis':'split_adjusted','retrieved_at':at.isoformat(),
            'requested_from':first.isoformat(),'requested_to':today.isoformat(),'from':rows[0]['date'],
            'as_of':rows[-1]['date'],'received_points':received,'received_digest':fingerprint,
            'retained_points':len(rows),'retention_limit':limit,'candles':rows,'realtime':False}
