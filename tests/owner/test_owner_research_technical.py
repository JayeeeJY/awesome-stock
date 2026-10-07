import json
from datetime import timedelta
import pytest
from awesome_stock.storage import owner_business as b,owner_market_history as history,owner_research_technical as technical,owner_research_reports as reports
from awesome_stock.storage.local import Conflict
from test_owner_api import app
from test_owner_market_history import configured,uid


def source(store,age=0,count=90):
    end=b.now().date()-timedelta(days=age)
    data={'Meta Data':{'2. Symbol':'TEST'},'Time Series (Daily)':{}}
    for i in range(count):
        value=100+i
        data['Time Series (Daily)'][(end-timedelta(days=count-1-i)).isoformat()]={'1. open':str(value),'2. high':str(value+2),'3. low':str(value-2),'4. close':str(value+1),'5. volume':str(10000+i)}
    c=configured(lambda *a,**kw:data);preview=c.market_history({'symbol':'TEST'})
    return history.save(store,{'id':uid(),'operation_id':uid(),'token':preview['token']},c)


def test_current_technical_has_provenance_and_no_invented_position(app):
    store=app.store
    assert technical.read(store,{'symbol':'TEST'})['status']=='missing'
    saved=source(store);result=technical.read(store,{'symbol':'TEST'})
    assert result['source']==saved and result['status']=='ready'
    assert result['technical']['rsi14']==100
    assert result['technical']['moving_averages']['ma120'] is None
    assert 'signals' not in result and 'position' not in result
    assert technical.read(store,{'symbol':'OTHER'})['status']=='missing'


def test_stale_and_short_history_keep_missing_explicit(app):
    source(app.store,age=4)
    stale=technical.read(app.store,{'symbol':'TEST'});assert stale['status']=='stale' and stale['technical'] is None
    source(app.store,count=1)
    partial=technical.read(app.store,{'symbol':'TEST'});assert partial['status']=='partial'
    assert partial['technical']['rsi14'] is None


def test_frozen_report_and_receipt_bind_exact_history(app):
    s=app.store;source(s)
    inp={'symbol':'TEST','lenses':['momentum']};preview=reports.preview(s,inp);packet=preview['packet']
    body={'id':uid(),'operation_id':uid(),'input':inp,'expected_token':preview['token']}
    saved=reports.save(s,body)
    context={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':'momentum'}],'records':packet['records'],'price_snapshots':[],'position_context':[],'market_technical':packet['market_technical']}
    receipt={'provider':'synthetic','model':'synthetic','generated_at':'synthetic','context':{'task':'research_synthesis','context':json.dumps(context)},'draft':'synthetic','synthesis':{'status':'structured'}}
    assert reports.bound_synthesis(packet,'receipt',{'receipt':receipt})['provider']=='synthetic'
    source(s,count=60)
    with pytest.raises(Conflict):reports.save(s,{**body,'id':uid(),'operation_id':uid()})
    changed=reports.preview(s,inp)['packet']
    with pytest.raises(Conflict):reports.bound_synthesis(changed,'receipt',{'receipt':receipt})
    assert reports.history(s)['reports'][0]==saved
    assert saved['packet']['market_technical']['source']['candles']!=changed['market_technical']['source']['candles']
    assert reports.preview(s,{'symbol':'TEST','lenses':['business']})['packet']['market_technical'] is None


def test_current_day_rollover_never_recomputes_frozen_report(app,monkeypatch):
    source(app.store)
    inp={'symbol':'TEST','lenses':['momentum']};preview=reports.preview(app.store,inp)
    saved=reports.save(app.store,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':preview['token']})
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=4))
    assert technical.read(app.store,{'symbol':'TEST'})['status']=='stale'
    assert reports.history(app.store)['reports'][0]==saved
    assert saved['packet']['market_technical']['status']=='ready'


def test_market_signals_have_native_evidence_without_default_discipline(app,monkeypatch):
    source(app.store)
    result=technical.read(app.store,{'symbol':'TEST'})
    codes={s['code'] for s in result['market_signals']}
    assert 'rsi_overbought' in codes and 'trend_confirmed' in codes
    assert all(s['category'] in {'momentum','price_structure','trend'} and s['evidence'] for s in result['market_signals'])
    assert not {'position_above_limit','position_concentrated','below_cost_line'}&codes
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=4))
    assert technical.read(app.store,{'symbol':'TEST'})['market_signals']==[]
