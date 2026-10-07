import pytest
from awesome_stock.storage import owner_feedback as f,owner_diagnosis as d
from awesome_stock.storage.local import Conflict
from test_owner_business import funded,quote,uid
from test_owner_diagnosis import body,save
from test_owner_api import app,request,login


def payload(target,symbol=''):
    return {'operation_id':uid(),'target_id':target,'target_symbol':symbol,'revision':0,'rating':'useful','reason':'Relevant','note':'Synthetic feedback','action_taken':False,'action_type':''}


def test_feedback_versions_summary_and_immutable_target(funded):
    quote(funded);record=save(funded,body());data=payload(record['id'])
    one=f.save(funded,data);assert f.save(funded,data)==one
    f.save(funded,data|{'revision':1,'operation_id':uid(),'rating':'not_useful'})
    state=f.history(funded,{'target_id':record['id'],'target_symbol':''})
    assert [r['rating'] for r in state['versions']]==['not_useful','useful']
    assert f.summary(funded)['total']==1 and f.summary(funded)['not_useful']==1
    assert d.history(funded,'account-test')['reports'][0]['report']==record['report']
    with pytest.raises(Conflict):f.save(funded,data|{'operation_id':uid()})
    f.save(funded,payload(record['id'],'TEST'))
    assert f.summary(funded)['by_type']['portfolio_impact']['useful']==1


def test_target_and_action_validation(funded):
    quote(funded);record=save(funded,body())
    for change in [{'target_symbol':'UNKNOWN'},{'rating':'profitable'},{'action_taken':1},{'action_taken':True}]:
        with pytest.raises(ValueError):f.save(funded,payload(record['id'])|change)
    assert f.summary(funded)['total']==0


def test_feedback_api_auth(app):
    assert request(app,'/api/v1/owner/insight-feedback')['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/insight-feedback','POST',{},cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/insight-feedback',**auth)['body']['total']==0
