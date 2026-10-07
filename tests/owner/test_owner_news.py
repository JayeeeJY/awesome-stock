import json
from datetime import datetime,timezone,timedelta
from urllib.parse import parse_qs,urlsplit
import pytest
from awesome_stock.runtime.owner_connections import ConnectionFailure
from awesome_stock.storage import owner_news as news,owner_research_memory as memory,owner_research_reports as reports
from awesome_stock.storage.owner import OwnerStore,restore_owner
from awesome_stock.storage.local import Conflict
from test_owner_api import app,login,request
from test_owner_market_history import configured,uid,KEY


def raw(**patch):
    row={'title':'Synthetic title','summary':'Synthetic <script>window.newsExecuted=true</script>','url':'https://example.com/article','source':'Synthetic publisher','time_published':(datetime.now(timezone.utc)-timedelta(hours=1)).strftime('%Y%m%dT%H%M%S'),'ticker_sentiment':[{'ticker':'TEST'}]}
    return {'feed':[{**row,**patch}]}


def save(s,data=None):
    c=configured(lambda *a,**k:raw() if data is None else data);p=c.news_feed({'symbol':'TEST'});body={'id':uid(),'operation_id':uid(),'token':p['token']}
    return c,p,body,news.save(s,body,c)


def test_news_receipt_confirmation_memory_dedup_and_restore(app,tmp_path):
    calls=[]
    def send(host,path,*args):calls.append((host,parse_qs(urlsplit(path).query)));return raw()
    c=configured(send);p=c.news_feed({'symbol':'TEST'})
    assert news.read(app.store,{'symbol':'TEST'})['snapshot'] is None
    assert calls[0][0]=='www.alphavantage.co' and calls[0][1]['limit']==['20'] and calls[0][1]['tickers']==['TEST']
    body={'id':uid(),'operation_id':uid(),'token':p['token']};result=news.save(app.store,body,c)
    assert result['verification']=='supplier_unverified'
    c.clear();assert news.save(app.store,body,c)==result
    save(app.store);events=memory.read(app.store,{'symbol':'TEST'})
    assert events['event_count']==1 and events['timeline'][0]['event_type']=='news' and events['quality_score']==65
    assert memory.read(app.store,{'symbol':'OTHER'})['event_count']==0
    assert KEY not in app.store.path.read_bytes().decode('latin1')
    backup=app.store.backup();target=tmp_path.resolve()/'news-restored';restore_owner(app.store.directory/'backups'/backup['name'],target)
    assert memory.read(OwnerStore(target),{'symbol':'TEST'})==events


@pytest.mark.parametrize('patch',[{'url':'javascript:alert(1)'},{'url':'https://user:secret@example.com/a'},{'url':'https://example.com\\@evil.com/a'},{'time_published':'29990101T000000'},{'time_published':'invalid'},{'ticker_sentiment':[{'ticker':'OTHER'}]},{'title':''},{'summary':'x'*6001}])
def test_malformed_news_has_no_receipt(patch):
    c=configured(lambda *a,**k:raw(**patch))
    with pytest.raises(ConnectionFailure):c.news_feed({'symbol':'TEST'})
    assert not c.news


def test_empty_quota_expiry_and_clear():
    c=configured(lambda *a,**k:{'Information':'quota'})
    with pytest.raises(ConnectionFailure):c.news_feed({'symbol':'TEST'})
    c.last_call.clear();c.send=lambda *a,**k:{'feed':[]};p=c.news_feed({'symbol':'TEST'});assert p['packet']['articles']==[]
    created,packet=c.news[p['token']];c.news[p['token']]=(created-301,packet)
    with pytest.raises(ConnectionFailure):c.news_receipt(p['token'])
    c.last_call.clear();p=c.news_feed({'symbol':'TEST'});c.configure({'kind':'data','provider':'','model':'','key':'','enabled':False})
    with pytest.raises(ConnectionFailure):c.news_receipt(p['token'])


def test_news_changes_invalidate_synthesis_and_fixed_preview(app):
    s=app.store;save(s);inp={'symbol':'TEST','lenses':['risk']};p=reports.preview(s,inp);packet=p['packet']
    context={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':'risk'}],'records':[],'price_snapshots':[],'position_context':[],'news_source':packet['news_source'],'research_memory':packet['research_memory']}
    receipt={'provider':'synthetic','model':'synthetic','generated_at':'synthetic','draft':'synthetic','synthesis':{'status':'structured'},'context':{'task':'research_synthesis','context':json.dumps(context)}}
    reports.bound_synthesis(packet,'receipt',{'receipt':receipt})
    body={'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']};fixed=reports.save(s,body)
    save(s,raw(title='Updated supplier headline'))
    with pytest.raises(Conflict):reports.save(s,{**body,'id':uid(),'operation_id':uid()})
    with pytest.raises(Conflict):reports.bound_synthesis(reports.preview(s,inp)['packet'],'receipt',{'receipt':receipt})
    assert reports.history(s)['reports'][0]==fixed
    assert reports.preview(s,{'symbol':'TEST','lenses':['position']})['packet']['news_source'] is None


def test_news_auth_csrf_and_client_cannot_replace_content(app):
    assert request(app,'/api/v1/owner/news-source','POST',{'symbol':'TEST'})['status']==401
    auth=login(app);app.connections.send=lambda *a,**k:raw()
    request(app,'/api/v1/owner/connections','POST',dict(kind='data',provider='alphavantage',model='',key=KEY,enabled=True),**auth)
    assert request(app,'/api/v1/owner/news-fetch','POST',{'symbol':'TEST'},cookie=auth['cookie'])['status']==403
    p=request(app,'/api/v1/owner/news-fetch','POST',{'symbol':'TEST'},**auth)['body']
    assert news.read(app.store,{'symbol':'TEST'})['snapshot'] is None
    body={'id':uid(),'operation_id':uid(),'token':p['token']}
    assert request(app,'/api/v1/owner/news-snapshots','POST',{**body,'articles':[]},**auth)['status']==400
    assert request(app,'/api/v1/owner/news-snapshots','POST',body,**auth)['status']==200
