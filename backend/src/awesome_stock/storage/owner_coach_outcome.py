"""Source-compatible directional price score; never realized investment return."""
from datetime import date, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from .owner_coach import instant

FORMULA = 'selfuse-coach-directional-price-v1'


def evaluate(trade, quote, *, currency, observed_on):
    """Date-only quotes must be strictly after the UTC execution date.

    A current quote is at most three calendar days old, matching Owner valuation.
    The caller supplies its observation date and freezes all returned evidence.
    Quantity, fees, cashflows, dividends and FX are intentionally not inferred.
    """
    today = date.fromisoformat(observed_on)
    executed = instant(trade['executed_at']).astimezone(timezone.utc).date()
    result = {'formula': FORMULA, 'status': 'pending', 'reason': None,
              'outcome_score': None, 'outcome_return_pct': None,
              'observed_on': observed_on, 'currency': currency,
              'trade_evidence': trade, 'price_evidence': quote,
              'scope': 'directional price change; excludes quantity, fees, dividends and FX; not realized return'}
    def pending(reason):
        return {**result, 'reason': reason}
    if trade['side'] not in {'buy', 'sell'}:
        raise ValueError('invalid trade side')
    price = Decimal(trade['price'])
    if not price.is_finite() or price <= 0:
        return pending('invalid_trade_price')
    if quote is None:
        return pending('missing_quote')
    if quote['symbol'] != trade['symbol'] or quote['currency'] != currency:
        return pending('quote_identity_mismatch')
    quoted_on = date.fromisoformat(quote['as_of'])
    if quoted_on > today:
        return pending('future_quote')
    if quoted_on <= executed:
        return pending('quote_not_after_trade')
    if (today - quoted_on).days > 3:
        return pending('stale_quote')
    current = Decimal(quote['price'])
    if not current.is_finite() or current <= 0:
        return pending('invalid_quote_price')
    with localcontext() as ctx:
        ctx.prec = 60
        change = (current - price) / price * 100
        if trade['side'] == 'sell':
            change = -change
        score = int((50 + change * 2).to_integral_value(rounding=ROUND_HALF_EVEN))
        return {**result, 'status': 'complete', 'outcome_score': max(0, min(100, score)),
                'outcome_return_pct': format(change, 'f')}
