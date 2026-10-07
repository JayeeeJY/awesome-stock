import uuid
import pytest
from awesome_stock.storage import owner_coach as c, owner_coach_period as p
from awesome_stock.storage.local import Conflict
from test_owner_store import store
from test_owner_evolve import seed
from test_owner_api import app,request,login


def uid():return str(uuid.uuid4())
def report(store,d,complete=True):
    data={'decision_ref':{'id':d['id'],'revision':1},'history_complete':complete}
    draft=c.preview(store,data)
    return c.save(store,{'id':uid(),'operation_id':uid(),'input':data,'expected_token':draft['token']})
RANGE={'start':'2020-01-01','end':'2030-01-01'}


def test_unique_trade_missing_and_stale_exclusion(store):
    d,t=seed(store);day=t['executed_at'][:10];period={'start':day,'end':day}
    assert p.preview(store,period)['report']['linked_without_report_count']==1
    report(store,d);report(store,d)
    result=p.preview(store,period)['report'];assert result['summary']['unique_trade_count']==1
    assert result['summary']['process_score']=='100.00' and result['months'][0]['scored_count']==1
    report(store,d,False)
    result=p.preview(store,period)['report'];assert result['summary']['process_score'] is None
    assert result['summary']['incomplete_count']==1
    store.trade(t|{'revision':1,'quantity':'12','operation_id':uid()})
    result=p.preview(store,period)['report'];assert result['summary']['stale_count']==1 and result['summary']['scored_count']==0


def test_period_snapshot_and_stale_save(store):
    d,t=seed(store);period={'start':t['executed_at'][:10],'end':t['executed_at'][:10]};report(store,d)
    draft=p.preview(store,period);body={'id':uid(),'operation_id':uid(),'input':period,'expected_token':draft['token']}
    saved=p.save(store,body);assert p.save(store,body)==saved
    report(store,d,False)
    with pytest.raises(Conflict):p.save(store,body|{'id':uid(),'operation_id':uid()})
    assert p.history(store)['reports'][0]['report']['summary']['process_score']=='100.00'


def test_empty_invalid(store):
    assert p.preview(store,{'start':'2026-09-01','end':'2026-09-30'})['report']['summary']['process_score'] is None
    with pytest.raises(ValueError):p.preview(store,RANGE)


def test_period_auth(app):
    assert request(app,'/api/v1/owner/coach-period')['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/coach-period-preview','POST',{},cookie=auth['cookie'])['status']==403


def test_conclusions_do_not_invent_strengths_for_missing_data():
    summary={'patterns':{},'scored_count':0,'stale_count':2,'incomplete_count':1}
    result=p.conclusions(summary)
    assert result['strengths']==[] and result['risks'][0]['basis']['stale_count']==2
    summary.update(scored_count=3,patterns={'rapid_reversal':2,'missing_reason':1})
    result=p.conclusions(summary)
    assert len(result['strengths'])==1
    assert result['risks'][0]['basis']=={'pattern':'rapid_reversal','count':2}
    assert any('理由' in a for a in result['next_actions']) and any('冷静期' in a for a in result['next_actions'])


def test_result_denominator_independent_and_fixed_history(store):
    from test_owner_business import quote
    d,t=seed(store);period={'start':t['executed_at'][:10],'end':t['executed_at'][:10]}
    quote(store,price='11');report(store,d,False)
    draft=p.preview(store,period);summary=draft['report']['summary']
    assert summary['process_score'] is None and summary['scored_count']==0
    assert summary['outcome_score']=='70.00' and summary['outcome_scored_count']==1
    assert draft['report']['months'][0]['outcome_score']=='70.00'
    body={'id':uid(),'operation_id':uid(),'input':period,'expected_token':draft['token']}
    p.save(store,body)
    quote(store,price='12')
    changed=p.preview(store,period)['report']['summary']
    assert changed['outcome_score'] is None and changed['outcome_stale_count']==1
    assert changed['outcome_pending_count']==0
    assert p.history(store)['reports'][0]['report']['summary']['outcome_score']=='70.00'
    report(store,d)
    current=p.preview(store,period)['report']['summary']
    assert current['unique_trade_count']==1 and current['process_score']=='100.00'
    assert current['outcome_score']=='90.00' and current['outcome_scored_count']==1


def test_result_missing_is_not_zero(store):
    d,t=seed(store);report(store,d)
    summary=p.preview(store,{'start':t['executed_at'][:10],'end':t['executed_at'][:10]})['report']['summary']
    assert summary['outcome_score'] is None and summary['outcome_pending_count']==1
    assert summary['outcome_scored_count']==0 and summary['outcome_stale_count']==0
