import pytest
from awesome_stock.storage import owner_daily as daily, owner_diagnosis as diagnosis, owner_business as business
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import OwnerStore, restore_owner
from test_owner_business import funded, quote, uid
from test_owner_diagnosis import body
from test_owner_api import app, request, login


def payload(store):
    data=body()
    return {'operation_id':uid(),'input':data,'expected_token':diagnosis.preview(store,data)['token']}


def test_atomic_fixed_capture_retry_and_restore(funded,tmp_path):
    quote(funded);before=funded.ledger();data=payload(funded)
    result=daily.capture(funded,data)
    assert daily.capture(funded,data)==result
    assert result['brief']['facts']['score']=='75.60'
    assert result['run']['data_status']=='complete'
    assert result['brief']['snapshot_id']==result['snapshot']['id']
    assert result['brief']['diagnosis_id']==result['diagnosis']['id']
    assert len(daily.history(funded,'account-test')['records'])==3
    assert len(diagnosis.history(funded,'account-test')['reports'])==1
    assert funded.ledger()==before
    # A new explicit observation is appended, never overwrites the earlier one.
    daily.capture(funded,payload(funded))
    assert len(daily.history(funded,'account-test')['records'])==6
    backup=funded.backup();dest=tmp_path.resolve()/'daily-restored'
    restore_owner(funded.directory/'backups'/backup['name'],dest)
    assert daily.history(OwnerStore(dest),'account-test')==daily.history(funded,'account-test')


def test_failure_rolls_back_all_artifacts_and_allows_retry(funded,monkeypatch):
    quote(funded);data=payload(funded);before=diagnosis.preview(funded,body())['token']
    real=business._put
    def fail(store,db,request,payload):
        result=real(store,db,request,payload)
        if payload['kind']=='daily_brief':raise RuntimeError('synthetic failure')
        return result
    with monkeypatch.context() as m:
        m.setattr(business,'_put',fail)
        with pytest.raises(RuntimeError):daily.capture(funded,data)
    assert not daily.history(funded,'account-test')['records']
    assert not diagnosis.history(funded,'account-test')['reports']
    assert diagnosis.preview(funded,body())['token']==before
    assert daily.capture(funded,data)['run']['status']=='completed'


def test_stale_input_and_partial_data(funded):
    data=payload(funded);quote(funded)
    with pytest.raises(Conflict):daily.capture(funded,data)
    assert not daily.history(funded,'account-test')['records']
    data=payload(funded);data['input']['holding_context']={}
    result=daily.capture(funded,data)
    assert result['run']['status']=='completed' and result['run']['data_status']=='partial'
    assert result['brief']['facts']['score'] is None
    assert result['brief']['provider_used'] is False


def test_api_auth_csrf(funded,app):
    quote(funded);data=payload(funded)
    assert request(app,'/api/v1/owner/daily-capture','POST',data)['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/daily-capture','POST',data,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/daily-capture','POST',data,**auth)['status']==200
    assert len(request(app,'/api/v1/owner/daily-history','POST',{'account_id':'account-test'},**auth)['body']['records'])==3


def test_daily_notification_feedback_preserves_facts(funded):
    quote(funded);data=payload(funded);result=daily.capture(funded,data)
    ws=business.workspace(funded)
    action=next(a for a in ws['actions'] if a['source_id']==result['brief']['id'])
    assert action['href']=='/review/diagnosis' and action['status']=='pending'
    state=business.save(funded,{'id':uid(),'revision':0,'operation_id':uid(),'kind':'action_state','data':{'action_id':action['id'],'status':'resolved','reason':'Reviewed synthetic report','snooze_until':''}})
    assert next(a for a in business.workspace(funded)['actions'] if a['id']==action['id'])['status']=='resolved'
    assert daily.capture(funded,data)==result
    assert len([a for a in business.workspace(funded)['actions'] if a['source_id']==result['brief']['id']])==1
    assert next(r for r in daily.history(funded,'account-test')['records'] if r['id']==result['brief']['id'])==result['brief']


def test_daily_journal_fixed_text_and_review_projection(funded):
    from awesome_stock.storage.owner_evolve import workspace
    quote(funded);result=daily.capture(funded,payload(funded))
    journal=result['brief']['journal']
    assert journal['tickers']==['TEST'] and '75.60' in journal['content']
    assert journal['tags']==['daily-brief','portfolio','manual']
    entries=workspace(funded)['daily_journal']
    assert entries==[result['brief']]
    assert business.workspace(funded)['daily_index']==[{'id':result['brief']['id'],'account_id':'account-test'}]
    assert workspace(funded)['reviews']==[]
    # Feedback and new observations must not replace the text stored with the report.
    daily.capture(funded,payload(funded))
    assert next(e for e in workspace(funded)['daily_journal'] if e['id']==result['brief']['id'])['journal']==journal


def test_ai_draft_requires_completed_receipt_and_never_overwrites_facts(funded):
    from test_owner_connections import configured
    quote(funded);brief=daily.capture(funded,payload(funded))['brief'];calls=[]
    def send(*args,**kwargs):
        calls.append(args);return {'done':True,'message':{'content':'Synthetic summary'}}
    connection=configured('ollama',send)
    preview=connection.preview({'task':'review','question':'Summarize fixed facts','context':str(brief['facts'])})
    data={'id':uid(),'operation_id':uid(),'brief_id':brief['id'],'token':preview['token']}
    with pytest.raises(Conflict):daily.save_ai_draft(funded,data,connection.receipts)
    assert not calls
    connection.generate({'token':preview['token'],'confirm':True})
    saved=daily.save_ai_draft(funded,data,connection.receipts)
    assert saved['review_status']=='unverified' and saved['replaces_facts'] is False
    assert saved['draft']=='Synthetic summary' and saved['sent_context']==preview['payload']
    connection.clear()
    assert daily.save_ai_draft(funded,data,connection.receipts)==saved
    assert len(calls)==1
    assert next(r for r in daily.history(funded,'account-test')['records'] if r['id']==brief['id'])==brief
    assert next(r for r in daily.history(funded,'account-test')['records'] if r['id']==saved['id'])==saved


def test_ai_draft_endpoint_requires_auth_and_csrf(funded,app):
    quote(funded);brief=daily.capture(funded,payload(funded))['brief']
    data={'id':uid(),'operation_id':uid(),'brief_id':brief['id'],'token':'unknown'}
    assert request(app,'/api/v1/owner/daily-ai-draft','POST',data)['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/daily-ai-draft','POST',data,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/daily-ai-draft','POST',data,**auth)['status']==409
