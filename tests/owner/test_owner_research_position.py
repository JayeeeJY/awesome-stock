import json
from decimal import Decimal
from datetime import timedelta
import pytest
from awesome_stock.storage import owner_business as b,owner_research_position as position,owner_research_reports as reports,owner_constitution as constitution,owner_fx as fx
from awesome_stock.storage.local import Conflict
from test_owner_api import app
from test_owner_market_history import uid

def funded(s,currency='USD',symbol='TEST',quantity='3',price='10'):
    aid=uid();s.add_account(dict(id=aid,operation_id=uid(),name='Synthetic '+currency,currency=currency,opening_cash='10000'))
    s.trade(dict(id=uid(),revision=0,operation_id=uid(),account_id=aid,symbol=symbol,side='buy',quantity=quantity,price=price,fee='0',executed_at='2026-01-01T00:00:00Z'))
    b.save(s,dict(id=uid(),revision=0,operation_id=uid(),kind='quote',data=dict(symbol=symbol,currency=currency,price=price,as_of=b.now().date().isoformat(),source='Synthetic')))

def policy(s,revision=0,maximum='30'):
    return constitution.save(s,{'operation_id':uid(),'revision':revision,'config':{'policy':{'warning_percent':'20','max_percent':maximum,'shock_percent':'10','custom_rules':[]},'require_reason_before_trade':False,'prohibited_actions':[]}})

def test_saved_discipline_boundary_and_no_default(app):
    s=app.store;funded(s);funded(s,symbol='OTHER',quantity='7')
    result=position.read(s,{'symbol':'TEST'});assert Decimal(result['weight_percent'])==30 and result['status']=='policy_missing' and not result['signals']
    policy(s);result=position.read(s,{'symbol':'TEST'});assert result['risk_level']=='critical'
    assert result['total_holdings_usd']=='100' # Cash excluded.
    assert result['constitution_evidence']['revision']==1
    assert result['signals'][0]['limit_percent']=='30'
    assert position.read(s,{'symbol':'ABSENT'})['risk_level']=='unknown'


def test_missing_fx_blocks_false_normal_and_expiry(app,monkeypatch):
    s=app.store;funded(s);funded(s,currency='HKD',symbol='OTHER',quantity='10');policy(s)
    assert position.read(s,{'symbol':'TEST'})['weight_percent'] is None
    today=b.now().date().isoformat();fx.save(s,{'operation_id':uid(),'revision':0,'currency':'HKD','rate':'0.1','as_of':today,'expires_on':today,'source':'Synthetic FX'})
    result=position.read(s,{'symbol':'TEST'});assert Decimal(result['weight_percent'])==75 and result['risk_level']=='critical'
    assert any(r['fx_evidence'] for r in result['valuation_basis'])
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=1))
    expired=position.read(s,{'symbol':'TEST'});assert expired['status']=='unavailable' and not expired['signals']


def test_constitution_change_invalidates_report_and_synthesis(app):
    s=app.store;funded(s);funded(s,symbol='OTHER',quantity='7');policy(s)
    inp={'symbol':'TEST','lenses':['position']};preview=reports.preview(s,inp);packet=preview['packet']
    assert packet['rule_report']['summary']['headline']=='仓位达到或超过已保存纪律上限'
    body={'id':uid(),'operation_id':uid(),'input':inp,'expected_token':preview['token']};saved=reports.save(s,body)
    context={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':'position'}],'records':packet['records'],'price_snapshots':[],'position_context':[reports.position_source(a,p,packet['evaluated_on']) for a in packet['accounts'] for p in a['positions']],'position_intelligence':packet['position_intelligence'],'research_memory':packet['research_memory']}
    receipt={'provider':'synthetic','model':'synthetic','generated_at':'synthetic','context':{'task':'research_synthesis','context':json.dumps(context)},'draft':'synthetic','synthesis':{'status':'structured'}}
    reports.bound_synthesis(packet,'receipt',{'receipt':receipt})
    policy(s,revision=1,maximum='40')
    with pytest.raises(Conflict):reports.save(s,{**body,'id':uid(),'operation_id':uid()})
    with pytest.raises(Conflict):reports.bound_synthesis(reports.preview(s,inp)['packet'],'receipt',{'receipt':receipt})
    assert reports.history(s)['reports'][0]==saved


def test_expired_prices_never_become_normal(app,monkeypatch):
    funded(app.store);policy(app.store)
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=4))
    result=position.read(app.store,{'symbol':'TEST'})
    assert result['status']=='unavailable' and result['risk_level']=='unknown'
    assert result['weight_percent'] is None and not result['signals']
    assert any('价格缺失或过期' in item for item in result['missing'])


@pytest.mark.parametrize('quantity,triggered',[('24.99999999',False),('25',True),('25.00000001',True)])
def test_generic_concentration_global_holdings_boundary_without_policy(app,quantity,triggered):
    s=app.store;funded(s,quantity=quantity,price='1')
    funded(s,symbol='OTHER',quantity=str(Decimal('100')-Decimal(quantity)),price='1')
    result=reports.preview(s,{'symbol':'TEST','lenses':['position']})['packet']
    cue=result['rule_report']['concentration']
    assert cue['triggered'] is triggered and cue['status']=='evaluated'
    assert Decimal(cue['weight_percent'])==Decimal(quantity)
    assert result['position_intelligence']['status']=='policy_missing'
    assert Decimal(result['position_intelligence']['total_holdings_usd'])==100
    assert (result['rule_report']['summary']['posture']=='risk_review') is triggered
    assert reports.preview(s,{'symbol':'TEST','lenses':['business']})['packet']['rule_report']['concentration']['status']=='not_evaluated'


def test_generic_concentration_missing_fx_and_stale_prices_not_evaluated(app,monkeypatch):
    s=app.store;funded(s);funded(s,currency='HKD',symbol='OTHER',quantity='10')
    inp={'symbol':'TEST','lenses':['position']}
    cue=lambda:reports.preview(s,inp)['packet']['rule_report']['concentration']
    assert cue()['status']=='not_evaluated' and not cue()['triggered']
    today=b.now().date().isoformat()
    fx.save(s,{'operation_id':uid(),'revision':0,'currency':'HKD','rate':'0.1','as_of':today,'expires_on':today,'source':'Synthetic FX'})
    assert cue()['triggered'] and Decimal(cue()['weight_percent'])==75
    preview=reports.preview(s,inp)
    saved=reports.save(s,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':preview['token']})
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=4))
    assert cue()['status']=='not_evaluated' and not cue()['triggered']
    assert reports.history(s)['reports'][0]==saved


@pytest.mark.parametrize('price,expected',[('9.00000001',False),('9',True),('8.99999999',True)])
def test_cost_line_is_exact_per_account_without_fx_or_default_policy(app,price,expected):
    s=app.store;funded(s,currency='HKD',quantity='1',price='10')
    b.save(s,dict(id=uid(),revision=0,operation_id=uid(),kind='quote',data=dict(symbol='TEST',currency='HKD',price=price,as_of=b.now().date().isoformat(),source='Synthetic new quote')))
    result=position.read(s,{'symbol':'TEST'})
    assert result['weight_percent'] is None and not result['signals']
    assert bool(result['context_signals']) is expected
    assert result['context_basis'][0]['currency']=='HKD' and result['context_basis'][0]['open_cost']=='10'
    if expected:assert result['context_signals'][0]['code'].startswith('below_cost_line:')


def test_stale_price_suppresses_cost_but_estimated_event_keeps_explicit_source(app,monkeypatch):
    from test_owner_company import saved
    from datetime import datetime,timezone
    s=app.store;funded(s);saved(s)
    original=position.read(s,{'symbol':'TEST'});due=original['earnings_window']['estimated_next_earnings_date']
    now=datetime.fromisoformat(due).replace(tzinfo=timezone.utc)-timedelta(days=3)
    monkeypatch.setattr(b,'now',lambda:now)
    result=position.read(s,{'symbol':'TEST'})
    assert result['earnings_window']['days_to_earnings']==3
    assert any(x['code']=='earnings_window' and '未经公告确认' in x['title'] for x in result['context_signals'])
    assert not any(x['code'].startswith('below_cost_line') for x in result['context_signals'])
    assert position.read(s,{'symbol':'ABSENT'})['context_basis']==[]
