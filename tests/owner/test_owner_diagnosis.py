import copy
import pytest
from awesome_stock.storage import owner_diagnosis as d,owner_business as b
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import OwnerStore,restore_owner
from test_owner_business import funded,quote,uid
from test_owner_api import app,request,login

def body():return {'account_id':'account-test','policy':{'warning_percent':'20','max_percent':'30','shock_percent':'10','custom_rules':[]},'holding_context':{'TEST':{'company':'Synthetic company','news':'neutral','source':'Synthetic observation','as_of':b.now().date().isoformat()}}}
def save(s,input):
    p=d.preview(s,input);return d.save(s,{'id':uid(),'operation_id':uid(),'input':input,'expected_token':p['token']})

def test_five_dimensions_and_shock_exact(funded):
    quote(funded);before=funded.ledger();r=d.preview(funded,body())['report']
    assert r['status']=='complete' and r['score']=='75.60' and r['grade']=='B'
    assert {key:v['score'] for key,v in r['dimensions'].items()}=={'concentration':'60.00','profitability':'100.00','diversification':'20.00','position_size':'100.00','discipline':'84.00'}
    assert r['impacts'][0]['scenario_pnl']=='-20' and r['total_value']=='200'
    assert funded.ledger()==before

def test_missing_context_and_price_never_fake_full_score(funded):
    assert d.preview(funded,body())['report']['status']=='unavailable'
    quote(funded);input=body();input['holding_context']={};r=d.preview(funded,input)['report']
    assert r['status']=='partial' and r['score'] is None and r['grade'] is None
    assert r['dimensions']['discipline']['score'] is None and r['dimensions']['diversification']['score'] is None


def test_rule_breaches_and_invalid_rule(funded):
    quote(funded);input=body();input['policy']['custom_rules']=[{'name':'Synthetic cap','metric':'position_percent','operator':'gte','threshold':'50','severity':'critical'}]
    r=d.preview(funded,input)['report'];assert r['dimensions']['discipline']['score']=='68.00'
    input['policy']['custom_rules'][0]['operator']='execute'
    with pytest.raises(ValueError):d.preview(funded,input)


def test_fixed_history_stale_save_and_restore(funded,tmp_path):
    quote(funded);input=body();preview=d.preview(funded,input);payload={'id':uid(),'operation_id':uid(),'input':input,'expected_token':preview['token']}
    saved=d.save(funded,payload);assert d.save(funded,payload)==saved
    with pytest.raises(Conflict):d.save(funded,payload|{'id':uid(),'operation_id':uid()})
    changed=copy.deepcopy(input);changed['holding_context']={};save(funded,changed)
    h=d.history(funded,'account-test');assert len(h['reports'])==2 and h['comparison']['score_delta'] is None
    assert h['reports'][1]['report']['score']=='75.60'
    backup=funded.backup();dest=tmp_path.resolve()/'diagnosis-restored';restore_owner(funded.directory/'backups'/backup['name'],dest)
    assert d.history(OwnerStore(dest),'account-test')==h

@pytest.mark.parametrize('change',[{'warning_percent':'40','max_percent':'30'},{'shock_percent':'101'},{'max_percent':'0'}])
def test_invalid_policy(funded,change):
    input=body();input['policy'].update(change)
    with pytest.raises(ValueError):d.preview(funded,input)


def test_policy_change_disables_score_comparison(funded):
    quote(funded);input=body();save(funded,input);input['policy']['max_percent']='40';save(funded,input)
    c=d.history(funded,'account-test')['comparison']
    assert c['policy_comparable'] is False and c['score_delta'] is None and all(x is None for x in c['dimension_deltas'].values())


def test_api_auth_csrf_and_record(funded,app):
    quote(funded);input=body()
    assert request(app,'/api/v1/owner/diagnosis-preview','POST',input)['status']==401
    auth=login(app)
    assert request(app,'/api/v1/owner/diagnosis-preview','POST',input,cookie=auth['cookie'])['status']==403
    preview=request(app,'/api/v1/owner/diagnosis-preview','POST',input,**auth)
    assert preview['status']==200
    saved=request(app,'/api/v1/owner/diagnosis','POST',{'id':uid(),'operation_id':uid(),'input':input,'expected_token':preview['body']['token']},**auth)
    assert saved['status']==200
    assert len(request(app,'/api/v1/owner/diagnosis-history','POST',{'account_id':'account-test'},**auth)['body']['reports'])==1


def test_intelligence_source_ranking_and_fixed_facts(funded):
    quote(funded);input=body();report=d.preview(funded,input)['report'];brain=report['intelligence']
    impact=brain['top_impacts'][0]
    assert impact['risk_score']==53 and impact['risk_level']=='high'
    assert brain['high_impact_count']==1 and brain['rule_breach_count']==1
    assert impact['review_actions']==['review_position_size']
    assert d.preview(funded,input)['report']['intelligence']==brain
    input['policy']['custom_rules']=[{'name':'Synthetic cap','metric':'position_percent','operator':'gte','threshold':'50','severity':'critical'}]
    changed=d.preview(funded,input)['report']['intelligence']['top_impacts'][0]
    assert changed['risk_score']==71 and changed['risk_level']=='critical'
    assert changed['fact_hash']!=impact['fact_hash']
    saved=save(funded,input)
    assert d.history(funded,'account-test')['reports'][0]['report']['intelligence']==saved['report']['intelligence']


def test_intelligence_missing_facts_are_not_zero_risk(funded):
    unavailable=d.preview(funded,body())['report']['intelligence']
    assert unavailable['high_impact_count'] is None and unavailable['rule_breach_count'] is None
    assert unavailable['coverage_count']==0 and unavailable['position_count']==1
    quote(funded);input=body();input['holding_context']={}
    partial=d.preview(funded,input)['report']['intelligence']
    assert partial['status']=='partial' and partial['missing']
    assert 'complete_evidence' in partial['top_impacts'][0]['review_actions']


def test_constitution_pins_exact_version_and_rejects_mismatch(funded):
    from awesome_stock.storage import owner_constitution as c
    quote(funded)
    cfg={'policy':body()['policy'],'require_reason_before_trade':True,'prohibited_actions':['Synthetic restriction']}
    one=c.save(funded,{'operation_id':uid(),'revision':0,'config':cfg})
    inp=body()|{'constitution_revision':1}
    saved=save(funded,inp)
    c.save(funded,{'operation_id':uid(),'revision':1,'config':cfg|{'policy':cfg['policy']|{'max_percent':'40'}}})
    assert d.preview(funded,inp)['report']['constitution_evidence']==one
    assert saved['report']['constitution_evidence']==one
    with pytest.raises(ValueError):d.preview(funded,inp|{'constitution_revision':2})
    with pytest.raises(ValueError):d.preview(funded,inp|{'constitution_revision':True})
    with pytest.raises(ValueError):d.preview(funded,inp|{'constitution_revision':999})
