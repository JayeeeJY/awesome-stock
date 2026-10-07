from datetime import datetime,timezone,timedelta
import pytest
from awesome_stock.research.news_sentiment import supplied
from awesome_stock.storage import owner_research_position as position,owner_research_reports as reports
from test_owner_api import app
from test_owner_news import raw,save
from test_owner_research_position import funded
from test_owner_market_history import configured,uid
from awesome_stock.runtime.owner_connections import ConnectionFailure

@pytest.mark.parametrize('label,score,expected',[('Bearish','0.8','negative'),('Somewhat-Bearish',None,'negative'),('Bullish',None,'positive'),('Neutral','-.4','neutral'),('mixed',None,'neutral'),('负面',None,'negative'),(None,'-0.15000001','negative'),(None,'-0.15','neutral'),(None,'0.15','neutral'),(None,'0.15000001','positive'),('unrecognized',None,None),(None,None,None)])
def test_native_mapping_keeps_supplied_fields_and_unknown(label,score,expected):
    # Accept canonical decimal spelling; label has original native precedence.
    score='-0.4' if score=='-.4' else score
    result=supplied({'ticker_sentiment_label':label,'ticker_sentiment_score':score})
    assert result['normalized']==expected and result['score']==score and result['label']==label and not result['verified']

@pytest.mark.parametrize('score',['NaN','Infinity','1.1','-1.1','1e2',True,{},0.2])
def test_invalid_score_rejects_preview(score):
    data=raw(ticker_sentiment=[{'ticker':'TEST','ticker_sentiment_score':score}]);c=configured(lambda *a,**k:data)
    with pytest.raises(ConnectionFailure):c.news_feed({'symbol':'TEST'})
    assert not c.news


def news_data(age=0,label='Bearish',score='-0.4'):
    stamp=(datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=age)).strftime('%Y%m%dT%H%M%S')
    return raw(time_published=stamp,ticker_sentiment=[{'ticker':'TEST','ticker_sentiment_label':label,'ticker_sentiment_score':score}])

@pytest.mark.parametrize('age,expected',[(14,True),(15,False)])
def test_latest_news_negative_signal_age_and_source(app,age,expected):
    s=app.store;funded(s);_,_,_,source=save(s,news_data(age))
    result=position.read(s,{'symbol':'TEST'})
    assert any(x['code']=='negative_news' for x in result['context_signals']) is expected
    assert result['news_context']['source_id']==source['id']
    assert result['news_context']['sentiment']['label']=='Bearish'
    assert result['risk_level']=='unknown' # No default personal discipline.
    assert position.read(s,{'symbol':'ABSENT'})['news_context'] is None


def test_newest_unknown_overrides_old_negative_and_fixed_report_keeps_old(app):
    s=app.store;funded(s);save(s,news_data(1));inp={'symbol':'TEST','lenses':['position']};p=reports.preview(s,inp)
    fixed=reports.save(s,{'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']})
    assert any(x['code']=='negative_news' for x in fixed['packet']['position_intelligence']['context_signals'])
    save(s,news_data(0,label=None,score=None))
    current=position.read(s,{'symbol':'TEST'})
    assert current['news_context']['sentiment']['normalized'] is None
    assert not any(x['code']=='negative_news' for x in current['context_signals'])
    assert reports.history(s)['reports'][0]==fixed
