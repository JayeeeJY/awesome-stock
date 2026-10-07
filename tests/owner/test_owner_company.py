import json
import pytest
from awesome_stock.storage import owner_company as company,owner_business as b,owner_research_reports as reports
from awesome_stock.storage.owner import OwnerStore,restore_owner
from awesome_stock.storage.local import Conflict
from awesome_stock.runtime.owner_connections import ConnectionFailure
from test_owner_api import app,login,request
from test_owner_market_history import configured,uid,KEY

def raw():return {'Symbol':'TEST','Currency':'USD','Name':'Synthetic Company','Description':'Synthetic <script>window.companyExecuted=true</script>','Sector':'Technology','Industry':'Software','LatestQuarter':'2026-03-31','PERatio':'None','PriceToBookRatio':'2.5','MarketCapitalization':'3500000000000','ReturnOnEquityTTM':'0.1234','QuarterlyRevenueGrowthYOY':'-0.012','QuarterlyEarningsGrowthYOY':'0'}

def saved(s,data=None):
    c=configured(lambda *a,**kw:data or raw());preview=c.company_overview({'symbol':'TEST'});body={'id':uid(),'operation_id':uid(),'token':preview['token']}
    return c,preview,body,company.save(s,body,c)

def test_workspace_company_label_uses_only_saved_matching_holdings(app):
    s=app.store
    s.add_account({'id':'company-usd','operation_id':uid(),'name':'Synthetic USD','currency':'USD','opening_cash':'1000'})
    s.add_account({'id':'company-hkd','operation_id':uid(),'name':'Synthetic HKD','currency':'HKD','opening_cash':'1000'})
    for account in ('company-usd','company-hkd'):
        s.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':account,'symbol':'TEST','side':'buy','quantity':'1','price':'10','fee':'0','executed_at':'2026-01-01T00:00:00Z'})
    assert b.workspace(s)['company_sources']=={}
    _,_,_,first=saved(s)
    sources=b.workspace(s)['company_sources']
    assert sources['TEST|USD']=={'name':'Synthetic Company','source':first['source'],'retrieved_at':first['retrieved_at'],'verification':'supplier_unverified','id':first['id'],'revision':first['revision']}
    assert 'TEST|HKD' not in sources
    saved(s,{**raw(),'Name':'Revised Synthetic Company'})
    assert b.workspace(s)['company_sources']['TEST|USD']['name']=='Revised Synthetic Company'
    assert not any(row['kind']=='company_snapshot' for row in b.workspace(s)['records'])

def test_company_receipt_exact_values_backup_and_no_auto_verification(app,tmp_path):
    c,p,body,result=saved(app.store)
    assert p['stored'] is False
    assert result['company']['pe'] is None and result['company']['market_cap_usd']=='3500000000000'
    assert result['company']['roe_ttm_percent']=='12.3400' and result['company']['quarterly_revenue_growth_yoy_percent']=='-1.200'
    assert result['company']['quarterly_earnings_growth_yoy_percent']=='0'
    assert result['verification']=='supplier_unverified'
    c.clear();assert company.save(app.store,body,c)==result
    assert KEY not in app.store.path.read_bytes().decode('latin1')
    with pytest.raises(Conflict):b.save(app.store,{'id':result['id'],'revision':1,'operation_id':uid()},archive=True)
    assert not [r for r in b.workspace(app.store)['records'] if r['kind']=='evidence']
    backup=app.store.backup();target=tmp_path.resolve()/'company-restored';restore_owner(app.store.directory/'backups'/backup['name'],target)
    assert company.read(OwnerStore(target),{'symbol':'TEST'})['snapshot']==result

@pytest.mark.parametrize('patch',[{'Symbol':'OTHER'},{'Currency':'HKD'},{'Name':''},{'PERatio':'NaN'},{'ReturnOnEquityTTM':'1e3'},{'LatestQuarter':'2999-01-01'},{'MarketCapitalization':'-1'}])
def test_invalid_provider_response_never_has_receipt(patch):
    c=configured(lambda *a,**kw:{**raw(),**patch})
    with pytest.raises(ConnectionFailure) as e:c.company_overview({'symbol':'TEST'})
    assert str(e.value)=='company_unavailable_or_quota' and not c.companies

def test_expiry_and_config_change(app):
    c=configured(lambda *a,**kw:raw());preview=c.company_overview({'symbol':'TEST'});created,packet=c.companies[preview['token']];c.companies[preview['token']]=(created-301,packet)
    with pytest.raises(ConnectionFailure):c.company_receipt(preview['token'])
    c.last_call.clear();preview=c.company_overview({'symbol':'TEST'});c.configure(dict(kind='data',provider='',model='',key='',enabled=False))
    with pytest.raises(ConnectionFailure):c.company_receipt(preview['token'])

def test_snapshot_update_invalidates_ai_and_report_but_preserves_history(app):
    s=app.store;saved(s);inp={'symbol':'TEST','lenses':['business','valuation']};p=reports.preview(s,inp);packet=p['packet']
    body={'id':uid(),'operation_id':uid(),'input':inp,'expected_token':p['token']};fixed=reports.save(s,body)
    source={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':x} for x in inp['lenses']],'records':[],'price_snapshots':[],'position_context':[],'company_source':packet['company_source'],'research_memory':packet['research_memory']}
    receipt={'provider':'synthetic','model':'synthetic','generated_at':'synthetic','draft':'synthetic','synthesis':{'status':'structured'},'context':{'task':'research_synthesis','context':json.dumps(source)}}
    reports.bound_synthesis(packet,'receipt',{'receipt':receipt})
    saved(s,{**raw(),'Name':'Changed supplier name'})
    with pytest.raises(Conflict):reports.bound_synthesis(reports.preview(s,inp)['packet'],'receipt',{'receipt':receipt})
    with pytest.raises(Conflict):reports.save(s,{**body,'id':uid(),'operation_id':uid()})
    assert reports.history(s)['reports'][0]==fixed
    assert reports.preview(s,{'symbol':'TEST','lenses':['risk']})['packet']['company_source'] is None

def test_api_auth_csrf_and_confirm_boundary(app):
    assert request(app,'/api/v1/owner/company-source','POST',{'symbol':'TEST'})['status']==401
    auth=login(app);app.connections.send=lambda *a,**kw:raw()
    request(app,'/api/v1/owner/connections','POST',dict(kind='data',provider='alphavantage',model='',key=KEY,enabled=True),**auth)
    assert request(app,'/api/v1/owner/company-fetch','POST',{'symbol':'TEST'},cookie=auth['cookie'])['status']==403
    preview=request(app,'/api/v1/owner/company-fetch','POST',{'symbol':'TEST'},**auth)['body']
    assert company.read(app.store,{'symbol':'TEST'})['snapshot'] is None
    body={'id':uid(),'operation_id':uid(),'token':preview['token']}
    assert request(app,'/api/v1/owner/company-snapshots','POST',{**body,'company':{}},**auth)['status']==400
    assert request(app,'/api/v1/owner/company-snapshots','POST',body,**auth)['status']==200
