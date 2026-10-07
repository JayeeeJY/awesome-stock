"""The approved native first release defers Yahoo; legacy clients cannot call it."""
import pytest
from awesome_stock.runtime.owner_connections import Connections, ConnectionFailure, transport
from test_owner_api import app, request, login

@pytest.mark.parametrize('configured',[False,True])
@pytest.mark.parametrize('history',[False,True])
def test_deferred_connection_never_calls_provider_or_creates_receipts(configured,history):
    calls=[];c=Connections(lambda *a,**kw:calls.append((a,kw)))
    if configured:c.configure(dict(kind='data',provider='alphavantage',model='',key='Synthetic-own-key',enabled=True))
    with pytest.raises(ConnectionFailure,match='public_market_deferred'):
        c.public_market(dict(symbol='AAPL',market='US'),history=history)
    assert calls==[] and c.histories=={} and c.last_call=={}
    assert c.status()['data_public']==dict(enabled=False,provider=None,model=None,tested=False,deferred=True)
    assert c.status()['data']['enabled'] is configured

@pytest.mark.parametrize('path',['/api/v1/owner/quote-fetch-public','/api/v1/owner/market-history-fetch-public'])
def test_legacy_api_is_authenticated_and_rejects_without_network_or_writes(app,path):
    calls=[];app.connections.send=lambda *a,**kw:calls.append((a,kw))
    assert request(app,path,'POST',dict(symbol='AAPL',market='US'))['status']==401
    auth=login(app);before=app.store.path.read_bytes()
    for body in (dict(symbol='AAPL',market='US'),dict(symbol='00700',market='HK',outputsize='full')):
        result=request(app,path,'POST',body,**auth)
        assert result['status']==503 and result['body']['error']['code']=='public_market_deferred'
        assert '未发起查询、未保存' in result['body']['error']['message']
    assert app.store.path.read_bytes()==before and calls==[]
    assert request(app,path,'POST',{},**(auth|dict(csrf='bad')))['status']==403

@pytest.mark.parametrize('key,local',[('',False),('Synthetic-never-forward',False),('',True)])
def test_legacy_transport_destination_cannot_be_reached(monkeypatch,key,local):
    def forbidden(*a,**kw):raise AssertionError('network construction must not happen')
    monkeypatch.setattr('http.client.HTTPSConnection',forbidden)
    monkeypatch.setattr('http.client.HTTPConnection',forbidden)
    with pytest.raises(ConnectionFailure,match='public_market_deferred'):
        transport('query1.finance.yahoo.com','/v8/finance/chart/AAPL?range=1y&interval=1d',None,key,local)
