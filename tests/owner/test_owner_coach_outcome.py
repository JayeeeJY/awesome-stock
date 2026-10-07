from copy import deepcopy
from awesome_stock.storage.owner_coach_outcome import evaluate

TRADE = {'id':'trade', 'account_id':'account', 'symbol':'TEST', 'side':'buy',
         'price':'100', 'executed_at':'2026-09-20T12:00:00+00:00', 'revision':1}
QUOTE = {'id':'quote', 'symbol':'TEST', 'currency':'USD', 'price':'110',
         'as_of':'2026-09-26', 'source':'Synthetic fixture', 'revision':1}


def run(trade=None, quote=QUOTE, today='2026-09-27'):
    return evaluate(trade or TRADE, quote, currency='USD', observed_on=today)


def test_direction_separate_from_cash_return_and_inputs_unchanged():
    before=deepcopy((TRADE,QUOTE))
    buy=run();sell=run(TRADE|{'side':'sell'})
    assert buy['outcome_score']==70 and buy['outcome_return_pct']=='10.0'
    assert sell['outcome_score']==30 and sell['outcome_return_pct']=='-10.0'
    assert run(quote=QUOTE|{'price':'200'})['outcome_score']==100
    assert run(quote=QUOTE|{'price':'1'})['outcome_score']==0
    assert (TRADE,QUOTE)==before
    assert buy['price_evidence']['source']=='Synthetic fixture'


def test_missing_stale_future_identity_and_same_day_are_unknown():
    cases=[(None,'missing_quote'),(QUOTE|{'as_of':'2026-09-23'},'stale_quote'),
           (QUOTE|{'as_of':'2026-09-28'},'future_quote'),
           (QUOTE|{'as_of':'2026-09-20'},'quote_not_after_trade'),
           (QUOTE|{'symbol':'OTHER'},'quote_identity_mismatch'),
           (QUOTE|{'currency':'EUR'},'quote_identity_mismatch'),
           (QUOTE|{'price':'NaN'},'invalid_quote_price')]
    for q,reason in cases:
        r=run(quote=q)
        assert r['reason']==reason and r['outcome_score'] is None and r['outcome_return_pct'] is None
    assert run(quote=QUOTE|{'as_of':'2026-09-24'})['status']=='complete'
    assert run(TRADE|{'price':'0'})['reason']=='invalid_trade_price'


def test_decimal_rounding_and_timezone_boundary():
    # Original Python round semantics: ties to even, not float drift.
    assert run(quote=QUOTE|{'price':'100.25'})['outcome_score']==50
    assert run(quote=QUOTE|{'price':'100.75'})['outcome_score']==52
    assert run(TRADE|{'executed_at':'2026-09-25T23:30:00-02:00'})['reason']=='quote_not_after_trade'
    r=run(TRADE|{'price':'999999999999.99999999'}, QUOTE|{'price':'999999999999.99999998'})
    assert r['outcome_score']==50 and r['outcome_return_pct'].startswith('-')
