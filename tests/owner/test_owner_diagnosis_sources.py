import copy
from datetime import timedelta
import pytest
from awesome_stock.storage import owner_diagnosis as d,owner_diagnosis_sources as sources,owner_business as b
from awesome_stock.storage.local import Conflict
from test_owner_api import app,login,request
from test_owner_business import funded,quote,uid
from test_owner_diagnosis import body
from test_owner_company import saved as save_company
from test_owner_news import save as save_news,raw


def seed(store):
    save_company(store)
    save_news(store,raw(ticker_sentiment=[{'ticker':'TEST','ticker_sentiment_label':'Bearish','ticker_sentiment_score':'-0.2'}]))


def test_explicit_sources_bound_to_versions_and_fixed_reports(funded):
    quote(funded);assert sources.read(funded,{'account_id':'account-test','symbol':'TEST'})['context'] is None
    seed(funded);context=sources.read(funded,{'account_id':'account-test','symbol':'TEST'})['context']
    assert context['news']=='negative' and context['source_evidence']['verification']=='supplier_unverified'
    data=body();data['holding_context']={'TEST':context};preview=d.preview(funded,data)
    report=d.save(funded,{'id':uid(),'operation_id':uid(),'input':data,'expected_token':preview['token']})
    assert report['report']['holding_context']['TEST']==context
    forged=copy.deepcopy(data);forged['holding_context']['TEST']['news']='neutral'
    with pytest.raises(Conflict):d.preview(funded,forged)
    save_company(funded)
    with pytest.raises(Conflict):d.preview(funded,data)
    assert d.history(funded,'account-test')['reports'][0]['report']['holding_context']['TEST']==context


def test_supplier_missing_news_stays_unknown_and_age_not_refreshed(funded,monkeypatch):
    quote(funded);save_company(funded);c=sources.read(funded,{'account_id':'account-test','symbol':'TEST'})['context'];assert c['news']=='unavailable'
    seed(funded);c=sources.read(funded,{'account_id':'account-test','symbol':'TEST'})['context'];data=body();data['holding_context']={'TEST':c}
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=4));b.save(funded,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{'symbol':'TEST','currency':'USD','price':'20','as_of':b.now().date().isoformat(),'source':'Synthetic current quote'}})
    assert d.preview(funded,data)['report']['status']=='partial'
    assert sources.read(funded,{'account_id':'account-test','symbol':'TEST'})['context']['as_of']==c['as_of']


def test_sources_api_requires_auth_csrf_and_held_symbol(funded,app):
    data={'account_id':'account-test','symbol':'TEST'}
    assert request(app,'/api/v1/owner/diagnosis-sources','POST',data)['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/diagnosis-sources','POST',data,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/diagnosis-sources','POST',data,**auth)['status']==200
    with pytest.raises(ValueError):sources.read(funded,{**data,'symbol':'OTHER'})
