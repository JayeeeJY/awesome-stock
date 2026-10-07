from datetime import timedelta
import json
import pytest
from awesome_stock.storage import owner_business as b,owner_research_memory as memory,owner_research_reports as reports
from awesome_stock.storage.local import Conflict
from test_owner_api import app
from test_owner_market_history import uid


def record(store,monkeypatch,age=0,symbol='TEST',kind='decision'):
    now=b.now()
    with monkeypatch.context() as m:
        m.setattr(b,'now',lambda:now-timedelta(days=age))
        with store.transaction() as db:
            return b._put(store,db,{'id':uid(),'revision':0},{'kind':kind,'symbol':symbol,'title':'Synthetic source','content':'Synthetic only','invalidation':'Synthetic stop','packet':{'symbol':symbol}})


def test_empty_memory_does_not_invent_thesis_or_confidence(app):
    result=memory.read(app.store,{'symbol':'TEST'})
    assert result['quality_score'] is None and result['freshness_score'] is None
    assert result['thesis'] is None and result['latest_delta'] is None
    assert result['event_count']==0 and len(result['coverage_gaps'])==3


def test_freshness_source_references_and_archive(app,monkeypatch):
    s=app.store
    fresh=record(s,monkeypatch,age=14);record(s,monkeypatch,age=15);record(s,monkeypatch,age=61)
    record(s,monkeypatch,symbol='OTHER');record(s,monkeypatch,age=-1)
    result=memory.read(s,{'symbol':'TEST'})
    assert result['event_count']==3 and result['quality_score']==60 and result['freshness_score']==57
    assert [e['freshness'] for e in result['timeline']]==['fresh','aging','stale']
    assert result['timeline'][0]['source_id']==fresh['id'] and result['timeline'][0]['source_digest']==b.digest(fresh)
    with s.transaction() as db:b._put(s,db,{'id':fresh['id'],'revision':1},{**fresh,'archived':True})
    assert memory.read(s,{'symbol':'TEST'})['event_count']==2


def test_scoring_and_display_limits_are_explicit(app,monkeypatch):
    for age in range(45):record(app.store,monkeypatch,age=age,kind='research_report')
    result=memory.read(app.store,{'symbol':'TEST'})
    assert result['event_count']==45 and result['scored_event_count']==40 and len(result['timeline'])==12
    assert result['quality_score']==65
    assert '尚无固定研究报告来源' not in result['coverage_gaps']


def test_new_events_invalidate_ai_and_keep_fixed_history(app,monkeypatch):
    s=app.store;record(s,monkeypatch)
    inp={'symbol':'TEST','lenses':['risk']};preview=reports.preview(s,inp);packet=preview['packet']
    context={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':'risk'}],'records':packet['records'],'price_snapshots':[],'position_context':[],'research_memory':packet['research_memory']}
    receipt={'provider':'synthetic','model':'synthetic','generated_at':'synthetic','context':{'task':'research_synthesis','context':json.dumps(context)},'draft':'synthetic','synthesis':{'status':'structured'}}
    reports.bound_synthesis(packet,'receipt',{'receipt':receipt})
    fixed=reports.save(s,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':preview['token']})
    assert fixed['packet']['research_memory']['event_count']==1
    assert memory.read(s,{'symbol':'TEST'})['event_count']==2
    with pytest.raises(Conflict):reports.bound_synthesis(reports.preview(s,inp)['packet'],'receipt',{'receipt':receipt})
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=70))
    assert memory.read(s,{'symbol':'TEST'})['freshness_score']==15
    assert reports.history(s)['reports'][0]==fixed


def test_reminder_versions_keep_original_symbol_source_and_feedback(app,tmp_path):
    from test_owner_business import candidate,obj
    from awesome_stock.storage.owner import OwnerStore,restore_owner
    s=app.store;c=candidate(s)
    action_id=c['id']+'-v1'
    data={'action_id':action_id,'status':'ignored','reason':'Synthetic counter evidence','snooze_until':''}
    first=obj(s,'action_state',data)
    second=obj(s,'action_state',{**data,'status':'resolved','reason':'Synthetic checked'},id=first['id'],revision=1)
    events=lambda symbol:[e for e in memory.read(s,{'symbol':symbol})['timeline'] if e['event_type']=='reminder_action']
    current=events('TEST');assert len(current)==2 and len({e['event_key'] for e in current})==2
    assert {e['source_revision'] for e in current}=={1,2}
    assert {e['action']['reason'] for e in current}=={'Synthetic counter evidence','Synthetic checked'}
    assert all(e['linked_source']['digest']==b.digest(c) for e in current)
    inp={'symbol':'TEST','lenses':['risk']};p=reports.preview(s,inp)
    fixed=reports.save(s,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']})
    changed=obj(s,'candidate',{**{k:c[k] for k in ['symbol','title','market','thesis','review_on']},'symbol':'OTHER','title':'Changed source'},id=c['id'],revision=1)
    b.save(s,{'id':changed['id'],'revision':2,'operation_id':uid()},archive=True)
    assert events('TEST')==current and events('OTHER')==[]
    assert reports.history(s)['reports'][0]==fixed
    backup=s.backup();target=tmp_path.resolve()/'reminder-restored';restore_owner(s.directory/'backups'/backup['name'],target)
    assert memory.read(OwnerStore(target),{'symbol':'TEST'})==memory.read(s,{'symbol':'TEST'})
    b.save(s,{'id':second['id'],'revision':2,'operation_id':uid()},archive=True)
    assert events('TEST')==[] and reports.history(s)['reports'][0]==fixed


def test_reminder_snooze_date_is_not_event_date_and_change_invalidates_preview(app):
    from test_owner_business import candidate,obj
    s=app.store;c=candidate(s);until=(b.now().date()+timedelta(days=7)).isoformat()
    data={'action_id':c['id']+'-v1','status':'snoozed','reason':'Check later','snooze_until':until}
    state=obj(s,'action_state',data)
    events=[e for e in memory.read(s,{'symbol':'TEST'})['timeline'] if e['event_type']=='reminder_action']
    assert len(events)==1 and events[0]['freshness']=='fresh'
    assert events[0]['occurred_at'][:10]==b.now().date().isoformat() and events[0]['action']['snooze_until']==until
    inp={'symbol':'TEST','lenses':['risk']};p=reports.preview(s,inp)
    obj(s,'action_state',{**data,'status':'confirmed','snooze_until':''},id=state['id'],revision=1)
    with pytest.raises(Conflict):reports.save(s,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']})


def test_reminder_missing_source_does_not_invent_event(app):
    with app.store.transaction() as db:
        b._put(app.store,db,{'id':uid(),'revision':0},{'kind':'action_state','title':'Synthetic orphan','action_id':'missing-v1','status':'confirmed','reason':'','snooze_until':''})
    assert memory.read(app.store,{'symbol':'TEST'})['event_count']==0
