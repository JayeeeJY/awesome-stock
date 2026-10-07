from decimal import Decimal
from awesome_stock.core.owner_views import project
from test_owner_store import account,trade,store
from test_owner_api import request,login,app


def test_empty_views(store):
    v=project(store.ledger());assert v['account_count']==v['trade_count']==v['open_position_count']==0
    assert v['data_gaps'][0]['code']=='no_accounts'
    assert v['market_value'] is None and v['cross_currency_total'] is None


def test_currency_totals_closed_positions_and_no_fake_valuation(store):
    store.add_account(account());store.add_account(account(id='account-two',currency='USD',opening_cash='500'))
    store.add_account(account(id='account-cny',currency='CNY',opening_cash='800'))
    store.trade(trade());store.trade(trade(side='sell',quantity='10',price='20',executed_at='2026-01-02T00:00:00Z'))
    store.trade(trade(account_id='account-two',quantity='2',price='10'))
    v=project(store.ledger());totals={b['currency']:b for b in v['currency_balances']}
    assert totals['USD']['cash']=='1577' and Decimal(totals['USD']['realized_pnl'])==98
    assert totals['CNY']['cash']=='800'
    assert v['open_position_count']==1 and v['positions'][0]['account_id']=='account-two'
    assert {x['code'] for x in v['data_gaps']}=={'missing_quotes','missing_fx'}
    assert v['market_value'] is v['allocation'] is v['unrealized_pnl'] is None


def test_recent_order_limit_and_read_only(store):
    store.add_account(account())
    for i in range(12):store.trade(trade(quantity='1',fee='0',executed_at=f'2026-01-{i+1:02d}T00:00:00Z'))
    before=store.ledger();v=project(before)
    assert v['trade_count']==12 and len(v['recent_trades'])==10
    assert v['recent_trades'][0]['executed_at'].startswith('2026-01-12')
    assert store.ledger()==before


def test_views_authenticated_and_updated_after_mutations(app):
    assert request(app,'/api/v1/owner/views')['status']==401
    auth=login(app);assert request(app,'/api/v1/owner/views',**auth)['body']['trade_count']==0
    app.store.add_account(account());t=trade();app.store.trade(t)
    assert request(app,'/api/v1/owner/views',**auth)['body']['positions'][0]['quantity']=='10'
    app.store.trade({'id':t['id'],'revision':1,'operation_id':'delete-unique'},delete=True)
    v=request(app,'/api/v1/owner/views',**auth)['body'];assert v['positions']==[] and v['currency_balances'][0]['cash']=='1000'
