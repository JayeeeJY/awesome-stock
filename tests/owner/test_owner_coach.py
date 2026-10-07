from awesome_stock.storage.owner_coach import evaluate


def trade(id='current',day='15',price='109',side='buy',account='account-a'):
    return {'id':id,'account_id':account,'symbol':'TEST','executed_at':f'2026-09-{day}T12:00:00+00:00','price':price,'side':side}


def test_ordinary_never_scored():
    r=evaluate(trade(),[trade('a','10'),trade('b','11',side='sell')],decision_context='ordinary')
    assert r['process_score'] is None and r['patterns']==[] and not r['process_scored']


def test_source_patterns_and_context_reason():
    h=[trade('buy','01','100'),trade('sell','10','100','sell')]
    r=evaluate(trade(),h,decision_context='linked_decision')
    assert {p['code'] for p in r['patterns']}=={'overtrading','rapid_reversal','chasing'}
    assert r['process_score']==65 and r['outcome_score'] is None
    assert evaluate(trade(),[],decision_context='required_without_context')['process_score']==80
    assert evaluate(trade(),[],decision_context='required_without_context',reason='Documented')['process_score']==100


def test_thresholds_account_time_and_unknown_history():
    h=[trade('buy','01','100'),trade('other','14',account='account-b'),trade('future','20')]
    r=evaluate(trade(price='108'),h,decision_context='linked_decision')
    assert r['patterns']==[] and r['history_trade_ids']==['buy']
    assert evaluate(trade(price='92'),h,decision_context='linked_decision')['patterns']==[]
    assert evaluate(trade(price='91.99'),h,decision_context='linked_decision')['patterns'][0]['code']=='averaged_down_unreviewed'
    assert evaluate(trade(),h,decision_context='linked_decision',history_complete=False)['process_score'] is None
    tied=[trade('one','01','100'),trade('two','01','110')]
    assert evaluate(trade(),tied,decision_context='linked_decision')['status']=='partial'

from awesome_stock.storage import owner_coach as coach
from awesome_stock.storage.local import Conflict
from test_owner_store import store
from test_owner_evolve import seed
from test_owner_api import app, request, login
import uuid
import pytest


def test_frozen_coach_and_stale_evidence(store):
    d,t=seed(store);data={'decision_ref':{'id':d['id'],'revision':d['revision']},'history_complete':False}
    p=coach.preview(store,data)
    assert p['report']['checks'][0]['process_score'] is None
    body={'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4()),'input':data,'expected_token':p['token']}
    saved=coach.save(store,body);assert coach.save(store,body)==saved
    store.trade(t|{'revision':1,'quantity':'12','operation_id':str(uuid.uuid4())})
    current=coach.history(store)['reports'][0]
    assert current['evidence_changed'] is True
    assert current['report']['evidence']['decision_evidence']['trades'][0]['quantity']=='10'
    with pytest.raises(Conflict):coach.save(store,body|{'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4())})


def test_coach_api_auth(app):
    assert request(app,'/api/v1/owner/coach')['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/coach-preview','POST',{},cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/coach',**auth)['body']['reports']==[]


def test_human_review_versions_and_atomic_journal(store):
    from awesome_stock.storage import owner_evolve
    d,t=seed(store);data={'decision_ref':{'id':d['id'],'revision':1},'history_complete':True}
    p=coach.preview(store,data)
    report=coach.save(store,{'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4()),'input':data,'expected_token':p['token']})
    body={'report_id':report['id'],'revision':0,'operation_id':str(uuid.uuid4()),'title':'Human review','content':'Checked original facts','status':'reviewed'}
    reviewed=coach.annotate(store,body);assert coach.annotate(store,body)==reviewed
    journal=coach.annotate(store,body|{'revision':1,'operation_id':str(uuid.uuid4()),'status':'journaled'})
    rows=owner_evolve.workspace(store)['coach_journal'];assert len(rows)==1
    assert rows[0]['annotation_revision']==2 and rows[0]['report']==report['report']
    coach.annotate(store,body|{'revision':2,'operation_id':str(uuid.uuid4()),'content':'Later reassessment','status':'draft'})
    assert owner_evolve.workspace(store)['coach_journal']==rows
    history=coach.history(store)['reports'][0]
    assert history['annotation']['status']=='draft' and history['report']==report['report']
    assert [r['revision'] for r in history['annotation_versions']]==[3,2,1]
    assert history['annotation_versions'][1]['content']=='Checked original facts'
    assert history['annotation_versions'][0]['content']=='Later reassessment'
    with pytest.raises(Conflict):coach.annotate(store,body|{'operation_id':str(uuid.uuid4())})


def test_coach_review_rejects_unknown_report_and_requires_auth(app):
    auth=login(app);body={'report_id':str(uuid.uuid4()),'revision':0,'operation_id':str(uuid.uuid4()),'title':'Review','content':'Checked','status':'reviewed'}
    assert request(app,'/api/v1/owner/coach-review','POST',body)['status']==401
    assert request(app,'/api/v1/owner/coach-review','POST',body,cookie=auth['cookie'])['status']==403
    assert request(app,'/api/v1/owner/coach-review','POST',body,**auth)['status']==400


def test_outcome_snapshot_quote_change_does_not_invalidate_process(store):
    from test_owner_business import quote
    d,t=seed(store)
    quote(store,price='11')
    data={'decision_ref':{'id':d['id'],'revision':1},'history_complete':True}
    p=coach.preview(store,data)
    check=p['report']['checks'][0]
    assert check['process_score']==100 and check['outcome_score']==70
    body={'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4()),'input':data,'expected_token':p['token']}
    saved=coach.save(store,body)
    quote(store,price='12')
    old=coach.history(store)['reports'][0]
    assert old['outcome_evidence_changed'] is True and old['evidence_changed'] is False
    from awesome_stock.storage import owner_coach_period
    period=owner_coach_period.preview(store,{'start':'2026-01-01','end':'2026-12-31'})['report']
    assert period['summary']['scored_count']==1 and period['entries'][0]['outcome_stale'] is True
    assert old['report']==saved['report'] and old['report']['checks'][0]['outcome_score']==70
    assert coach.preview(store,data)['report']['checks'][0]['outcome_score']==90
    with pytest.raises(Conflict):
        coach.save(store,body|{'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4())})


def test_important_trade_reason_policy_and_version_changes(store):
    from test_owner_store import account,trade
    from awesome_stock.storage import owner_constitution as constitution,owner_trade_context as context,owner_coach_period as period
    from test_owner_constitution import CONFIG
    store.add_account(account());t=trade();store.trade(t)
    inp={'trade_id':t['id'],'history_complete':True,'constitution_revision':1}
    with pytest.raises(ValueError):coach.preview(store,inp)
    cfg={'operation_id':str(uuid.uuid4()),'revision':0,'config':CONFIG}
    constitution.save(store,cfg)
    mark={'operation_id':str(uuid.uuid4()),'trade_id':t['id'],'trade_revision':1,'revision':0,'decision_required':True,'reason':''}
    context.save(store,mark)
    p=coach.preview(store,inp);check=p['report']['checks'][0]
    assert check['process_score']==80 and check['patterns'][0]['code']=='missing_reason'
    assert p['report']['evidence']['decision_evidence']['decision'] is None
    assert coach.history(store)['important_trades'][0]['id']==t['id']
    stats=period.preview(store,{'start':'2026-01-01','end':'2026-01-01'})['report']
    assert stats['ordinary_trade_count']==0 and stats['important_without_report_count']==1
    saved=coach.save(store,{'id':str(uuid.uuid4()),'operation_id':str(uuid.uuid4()),'input':inp,'expected_token':p['token']})
    constitution.save(store,cfg|{'operation_id':str(uuid.uuid4()),'revision':1,'config':CONFIG|{'require_reason_before_trade':False}})
    assert coach.preview(store,inp|{'constitution_revision':2})['report']['checks'][0]['process_score']==100
    assert coach.preview(store,inp)['report']['checks'][0]['process_score']==80
    context.save(store,mark|{'operation_id':str(uuid.uuid4()),'revision':1,'reason':'Explicit synthetic reason'})
    assert coach.preview(store,inp)['report']['checks'][0]['process_score']==100
    old=coach.history(store)['reports'][0]
    assert old['evidence_changed'] and old['report']==saved['report']
    context.save(store,mark|{'operation_id':str(uuid.uuid4()),'revision':2,'decision_required':False})
    with pytest.raises(ValueError):coach.preview(store,inp)
    assert coach.history(store)['reports'][0]['evidence_changed']
