"""Diagnostic scope projections, never synthetic ledger accounts.

The reserved scope contains ':' and cannot be a valid ledger account identifier.
Currency-qualified holding keys do not assert that cross-market tickers are equal.
"""
from decimal import Decimal, localcontext
from . import owner_business as b, owner_fx as fx
from .owner import identifier

ALL = 'portfolio:all'


def scope_id(value):
    return value if value == ALL else identifier(value)


def resolve(store, db, value):
    scope_id(value)
    accounts = b.valued_accounts(store, db)
    if value != ALL:
        account = next((a for a in accounts if a['id'] == value), None)
        if account is None:
            raise ValueError('account missing')
        return account
    conversion = fx.calculate(db, accounts)
    conversion.pop('native_accounts')
    converted = {a['account_id']: a for a in conversion['accounts']}
    groups = {}
    with localcontext() as ctx:
        ctx.prec = 60
        for account in accounts:
            evidence = converted[account['id']]
            rate = Decimal(1) if evidence['fx_status'] == 'identity' else (
                Decimal(evidence['fx_evidence']['rate']) if evidence['fx_status'] == 'current' else None)
            for position in account['positions']:
                key = account['currency'] + ':' + position['symbol']
                group = groups.setdefault(key, {'symbol': key, 'ticker': position['symbol'],
                    'source_currency': account['currency'], 'components': []})
                def convert(amount):
                    if amount is None or rate is None:
                        return None
                    return format(Decimal(amount) * rate, 'f')
                group['components'].append({'account_id': account['id'], 'account_name': account['name'],
                    'currency': account['currency'], 'position': position,
                    'fx_status': evidence['fx_status'], 'fx_evidence': evidence['fx_evidence'],
                    'market_value_usd': convert(position['market_value']),
                    'open_cost_usd': convert(position['open_cost']),
                    'unrealized_pnl_usd': convert(position['unrealized_pnl'])})
        for group in groups.values():
            for target, source in [('market_value', 'market_value_usd'), ('open_cost', 'open_cost_usd'),
                                   ('unrealized_pnl', 'unrealized_pnl_usd')]:
                values = [c[source] for c in group['components']]
                group[target] = (format(sum(map(Decimal, values), Decimal(0)), 'f')
                                 if all(v is not None for v in values) else None)
            statuses = [c['position']['quote_status'] for c in group['components']]
            group['quote_status'] = ('missing' if 'missing' in statuses else
                                     'stale' if 'stale' in statuses else 'current_snapshot')
            group['quote'] = None  # Exact native quotes live in components, never a fabricated USD quote.
        positions = sorted(groups.values(), key=lambda p: p['symbol'])
    return {'id': ALL, 'scope_kind': 'all_accounts', 'name': '全部账户组合', 'currency': 'USD',
            'positions': positions, 'valuation_complete': all(p['market_value'] is not None for p in positions),
            'estimated_assets': None, 'native_accounts': accounts, 'conversion_evidence': conversion,
            'return_basis': conversion['return_basis'],
            'grouping': 'source currency and ticker; same-currency positions combined across accounts'}


def read(store, value):
    with store.connection() as db:
        db.execute('BEGIN')
        return resolve(store, db, value)


def size_alerts(db, scope):
    """Layer limits keep their original account-assets denominator and native currency."""
    accounts = scope.get('native_accounts', [scope])
    limits = {(r['account_id'], sy): Decimal(r['max_single_percent'])
              for r in b.records(db, 'allocation_layer') for sy in r['symbols']}
    result = []
    with localcontext() as ctx:
        ctx.prec = 60
        for account in accounts:
            assets = account['estimated_assets']
            if assets is None or Decimal(assets) <= 0:
                continue
            for position in account['positions']:
                limit = limits.get((account['id'], position['symbol']))
                if limit is not None and position['market_value'] is not None and Decimal(position['market_value']) / Decimal(assets) * 100 > limit:
                    prefix = account['name'] + ' · ' if scope['id'] == ALL else ''
                    result.append(prefix + position['symbol'] + ' 超过已保存单股上限')
    return result
