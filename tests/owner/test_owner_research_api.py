from test_owner_api import app,request,login
from test_research_store import document,link
from test_owner_store import account,trade


def test_documents_auth_csrf_and_read_persistence(app):
    assert request(app,'/api/v1/owner/documents')['status']==401
    auth=login(app);body=document()
    assert request(app,'/api/v1/owner/documents','POST',body,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/documents','POST',body,**auth)['status']==200
    assert request(app,'/api/v1/owner/documents',**auth)['body']['documents'][0]['content']=='Original reasoning'
    assert request(app,'/api/v1/owner/documents','POST',body|{'workspace':'spoof'},**auth)['status']==400


def test_reference_api_cross_symbol_and_archive(app):
    auth=login(app);d=request(app,'/api/v1/owner/documents','POST',document('decision'),**auth)['body']
    app.store.add_account(account());t=trade();app.store.trade(t)
    assert request(app,'/api/v1/owner/trade-reference','POST',link(t,d),**auth)['status']==200
    assert request(app,'/api/v1/owner/documents','DELETE',{'id':d['id'],'revision':1,'operation_id':'archive-test'},**auth)['status']==200
    result=request(app,'/api/v1/owner/documents',**auth)['body']
    assert result['documents'][0]['archived'] and result['links'][0]['decision_revision']==1
