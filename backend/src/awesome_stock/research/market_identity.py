"""Explicit provider symbol identities; no guessed exchange or currency."""
import re
from zoneinfo import ZoneInfo


def china_a_symbol(symbol):
    return isinstance(symbol,str) and bool(re.fullmatch(r'(?:(?:60|68)[0-9]{4}(?:\.SHH)?|(?:00|30)[0-9]{4}(?:\.SHZ)?)',symbol))


def hong_kong_symbol(symbol):
    return isinstance(symbol,str) and bool(re.fullmatch(r'[0-9]{4,5}',symbol)) and int(symbol)>0


def identity(symbol,market='US'):
    if market=='US' and re.fullmatch(r'[A-Z][A-Z0-9-]{0,9}',symbol):
        return {'symbol':symbol,'provider_symbol':symbol,'market':'US','currency':'USD','date_basis':'UTC conservative validation'}
    if market=='CN' and china_a_symbol(symbol):
        code=symbol.split('.')[0]
        return {'symbol':code,'provider_symbol':code+('.SHH' if code.startswith(('60','68')) else '.SHZ'),'market':'CN','currency':'CNY','date_basis':'Asia/Shanghai'}
    raise ValueError('unsupported market symbol')


def china_day(at):
    return at.astimezone(ZoneInfo('Asia/Shanghai')).date()


def valuation_day(symbol,currency,at):
    if currency=='CNY' and china_a_symbol(symbol):return china_day(at)
    if currency=='HKD' and hong_kong_symbol(symbol):return at.astimezone(ZoneInfo('Asia/Hong_Kong')).date()
    return at.date()
