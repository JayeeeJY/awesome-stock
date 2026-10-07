import pytest
from awesome_stock.storage import owner_business as b
from test_owner_business import funded,quote,obj
from test_owner_api import app

def entry(**values):return dict(symbol='TEST',side='buy',quantity='1',price='20',fee='1',max_percent='100')|values

def test_sequence_uses_proceeds_and_fees_without_writes_and_saves(funded):
    quote(funded);before=funded.ledger()
    body={'type':'pre_trade_batch','account_id':'account-test','trades':[entry(side='sell',quantity='10'),entry(symbol='NEW',quantity='50')]}
    preview=b.preview_plan(funded,body);r=preview['result']
    assert r['status']=='passed' and r['cash_after']=='97' and r['estimated_assets_after']=='1097'
    assert r['rows'][0]['cash_after']=='1098' and len(r['rows'])==2
    saved=obj(funded,'scenario',{'title':'Synthetic batch','input':body,'expected_token':preview['token']})
    assert saved['result']==r and saved['input']==body and funded.ledger()==before


def test_blocked_first_leg_does_not_spend_future_proceeds(funded):
    quote(funded)
    body={'type':'pre_trade_batch','account_id':'account-test','trades':[entry(symbol='NEW',quantity='50'),entry(side='sell',quantity='10')]}
    r=b.preview_plan(funded,body)['result'];assert r['status']=='blocked' and r['evaluated_count']==1 and r['cash_after']=='899'


def test_same_new_symbol_keeps_first_mark_price(funded):
    quote(funded)
    body={'type':'pre_trade_batch','account_id':'account-test','trades':[entry(symbol='NEW',price='10'),entry(symbol='NEW',price='20')]}
    r=b.preview_plan(funded,body)['result'];assert r['cash_after']=='867' and r['estimated_assets_after']=='1087'

@pytest.mark.parametrize('trades',[[],[entry()]*21,[entry(quantity='NaN')]])
def test_bad_sequence_rejected(funded,trades):
    quote(funded)
    with pytest.raises(ValueError):b.preview_plan(funded,{'type':'pre_trade_batch','account_id':'account-test','trades':trades})
