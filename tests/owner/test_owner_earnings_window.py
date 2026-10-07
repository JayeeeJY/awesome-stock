from datetime import date,timedelta
import json
import pytest
from awesome_stock.research.earnings_window import _build_earnings_reminder
from awesome_stock.storage import owner_research_memory as memory,owner_research_reports as reports,owner_business as b
from awesome_stock.storage.local import Conflict
from test_owner_api import app
from test_owner_company import saved,raw
from test_owner_market_history import uid


@pytest.mark.parametrize('period,today,expected,days',[('2026-03-31','2026-07-25','2026-08-14',20),('2025-09-30','2026-03-10','2026-03-16',6),('2026-03-31','2026-08-14','2026-08-14',0),('2026-03-31','2026-08-15','2026-11-14',91)])
def test_native_window_dates_and_roll_forward(period,today,expected,days):
    result=_build_earnings_reminder('US',period,evaluated_on=date.fromisoformat(today))
    assert result['estimated_next_earnings_date']==expected and result['days_to_earnings']==days
    assert result['is_estimated'] is True


def test_missing_financial_period_has_no_default_window(app):
    assert memory.read(app.store,{'symbol':'TEST'})['earnings_window'] is None
    saved(app.store,{**raw(),'LatestQuarter':'None'})
    assert memory.read(app.store,{'symbol':'TEST'})['earnings_window'] is None


def test_window_is_not_a_historical_event_and_keeps_source(app):
    _,_,_,source=saved(app.store)
    result=memory.read(app.store,{'symbol':'TEST'})
    assert result['event_count']==0 and result['quality_score'] is None and result['freshness_score'] is None
    window=result['earnings_window'];assert window['source_evidence']==source and not window['confirmed']
    assert window['estimated_next_earnings_date']>=b.now().date().isoformat()
    assert '仅有推算窗口，尚无公司公告日期来源' in result['coverage_gaps']


def test_source_or_date_changes_invalidate_preview_and_keep_frozen_window(app,monkeypatch):
    s=app.store;saved(s);inp={'symbol':'TEST','lenses':['catalysts']};p=reports.preview(s,inp);packet=p['packet']
    context={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':'catalysts'}],'records':[],'price_snapshots':[],'position_context':[],'research_memory':packet['research_memory']}
    receipt={'provider':'synthetic','model':'synthetic','generated_at':'synthetic','draft':'synthetic','synthesis':{'status':'structured'},'context':{'task':'research_synthesis','context':json.dumps(context)}}
    reports.bound_synthesis(packet,'receipt',{'receipt':receipt})
    fixed=reports.save(s,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']})
    saved(s,{**raw(),'LatestQuarter':'2026-06-30'})
    with pytest.raises(Conflict):reports.bound_synthesis(reports.preview(s,inp)['packet'],'receipt',{'receipt':receipt})
    now=b.now();monkeypatch.setattr(b,'now',lambda:now+timedelta(days=70))
    assert reports.history(s)['reports'][0]==fixed
    assert memory.read(s,{'symbol':'TEST'})['earnings_window']['evaluated_on']!=fixed['packet']['research_memory']['earnings_window']['evaluated_on']
