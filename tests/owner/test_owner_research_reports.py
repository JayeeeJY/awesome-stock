import uuid
import pytest
from datetime import timedelta
from awesome_stock.storage import owner_business as b, owner_research_reports as r
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import OwnerStore,restore_owner
from test_owner_api import app,login,request

def uid():return str(uuid.uuid4())
def quote(store,symbol='TEST',price='20'):
    return b.save(store,{'id':uid(),'operation_id':uid(),'revision':0,'kind':'quote','data':{'symbol':symbol,'currency':'USD','price':price,'as_of':b.now().date().isoformat(),'source':'Synthetic research quote'}})
def body(p):return {'id':uid(),'operation_id':uid(),'input':{'symbol':'TEST','lenses':['position','valuation']},'expected_token':p['token']}

def test_frozen_packet_idempotence_and_no_unrelated_material(app,tmp_path):
    store=app.store;quote(store);quote(store,'OTHER')
    p=r.preview(store,{'symbol':'TEST','lenses':['position','valuation']});assert not p['stored']
    assert all(q['symbol']=='TEST' for q in p['packet']['quotes'])
    req=body(p);saved=r.save(store,req);assert r.save(store,req)==saved
    quote(store,price='40');assert r.history(store)['reports']==[saved]
    assert saved['packet']['quotes'][0]['price']=='20'
    with pytest.raises(Conflict):r.save(store,body(p))
    with pytest.raises(Conflict):r.save(store,{**req,'operation_id':uid()})
    assert r.history(OwnerStore(store.directory))['reports']==[saved]
    backup=store.backup();target=tmp_path.resolve()/'restored-research'
    restore_owner(store.directory/'backups'/backup['name'],target)
    assert r.history(OwnerStore(target))['reports']==[saved]


def test_day_rollover_invalidates_capture(app,monkeypatch):
    now=b.now();p=r.preview(app.store,{'symbol':'TEST','lenses':['position','valuation']})
    monkeypatch.setattr(b,'now',lambda:now+timedelta(days=1))
    with pytest.raises(Conflict):r.save(app.store,body(p))

@pytest.mark.parametrize('lenses',[[],['unknown'],['position','position'],[{}],'position'])
def test_invalid_lenses(app,lenses):
    with pytest.raises(ValueError):r.preview(app.store,{'symbol':'TEST','lenses':lenses})


def test_api_requires_login_csrf_and_cannot_archive(app):
    assert request(app,'/api/v1/owner/research-reports')['status']==401
    auth=login(app);inp={'symbol':'TEST','lenses':['position','valuation']}
    assert request(app,'/api/v1/owner/research-report-preview','POST',inp,cookie=auth['cookie'])['status']==403
    p=request(app,'/api/v1/owner/research-report-preview','POST',inp,**auth)['body'];saved=request(app,'/api/v1/owner/research-reports','POST',body(p),**auth)
    assert saved['status']==200
    archive={'id':saved['body']['id'],'operation_id':uid(),'revision':1}
    assert request(app,'/api/v1/owner/business','DELETE',archive,**auth)['status']==409
    assert len(request(app,'/api/v1/owner/research-reports',**auth)['body']['reports'])==1



def test_ai_receipt_bound_frozen_and_restored(app,tmp_path):
    import json
    from test_owner_connections import configured
    from test_owner_research_synthesis import FACTS
    inp={'symbol':'TEST','lenses':['position','valuation']}
    packet=r.preview(app.store,inp)['packet']
    source={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':x} for x in inp['lenses']],
            'records':packet['records'],'price_snapshots':[],'position_context':[]}
    c=configured('ollama',lambda *a,**kw:{'done':True,'message':{'content':json.dumps(FACTS)}})
    token=c.preview({'task':'research_synthesis','question':'Synthetic research','context':json.dumps(source)})['token']
    generated=c.generate({'token':token,'confirm':True});assert generated['receipt_id']==token
    inp['ai_receipt']=token
    preview=r.preview(app.store,inp,c.receipts)
    req={'id':uid(),'operation_id':uid(),'input':inp,'expected_token':preview['token']}
    saved=r.save(app.store,req,c.receipts)
    assert saved['packet']['rule_report']['ai_synthesis']['synthesis']['verified'] is False
    assert token not in json.dumps(saved)
    c.clear();assert r.save(app.store,req,c.receipts)==saved
    assert r.history(app.store)['reports']==[saved]
    with pytest.raises(Conflict):r.preview(app.store,inp,c.receipts)
    backup=app.store.backup();target=tmp_path.resolve()/'restored-ai-research'
    restore_owner(app.store.directory/'backups'/backup['name'],target)
    assert r.history(OwnerStore(target))['reports']==[saved]

@pytest.mark.parametrize('change',['symbol','date','records','lenses','positions','quote','malformed','unstructured'])
def test_ai_receipt_rejects_unrelated_source(app,change):
    import json
    inp={'symbol':'TEST','lenses':['position','valuation'],'ai_receipt':'test-receipt'}
    source={'symbols':['TEST'],'evaluated_on':b.now().date().isoformat(),'research_questions':[{'id':'position'},{'id':'valuation'}],
            'records':[],'price_snapshots':[],'position_context':[]}
    if change=='symbol':source['symbols']=['OTHER']
    if change=='date':source['evaluated_on']='2000-01-01'
    if change=='records':source['records']=[{'id':'forged'}]
    if change=='lenses':source['research_questions']=[]
    if change=='positions':source['position_context']=[{}]
    if change=='quote':source['price_snapshots']=[{'id':'forged'}]
    receipts={'test-receipt':{'synthesis':{'status':'unstructured' if change=='unstructured' else 'structured'},'context':{'task':'research_synthesis','context':'bad' if change=='malformed' else json.dumps(source)}}}
    with pytest.raises(Conflict):r.preview(app.store,inp,receipts)


def test_position_receipt_checks_cost_profit_weight_and_extra_fields(app):
    import copy,json
    inp={'symbol':'TEST','lenses':['position','valuation']}
    account_id=uid()
    app.store.add_account({'id':account_id,'operation_id':uid(),'name':'Receipt account','currency':'USD','opening_cash':'1000'})
    app.store.trade({'id':uid(),'operation_id':uid(),'revision':0,'account_id':account_id,'symbol':'TEST','side':'buy','quantity':'2','price':'10','fee':'1','executed_at':'2026-01-01T00:00:00Z'})
    quote(app.store)
    packet=r.preview(app.store,inp)['packet'];a=packet['accounts'][0]
    position=r.position_source(a,a['positions'][0],packet['evaluated_on']);assert position['weight']=='3.93%'
    source={'symbols':['TEST'],'evaluated_on':packet['evaluated_on'],'research_questions':[{'id':x} for x in inp['lenses']],
            'records':packet['records'],'price_snapshots':[],'position_context':[position],'research_memory':packet['research_memory']}
    receipt={'synthesis':{'status':'structured'},'context':{'task':'research_synthesis','context':json.dumps(source)},'provider':'ollama','model':'synthetic','generated_at':'Synthetic','draft':'Synthetic'}
    assert r.bound_synthesis(packet,'receipt',{'receipt':receipt})['model']=='synthetic'
    for key in ['open_cost','realized_pnl','weight','extra_unverified_value']:
        changed=copy.deepcopy(source);changed['position_context'][0][key]='999'
        bad={**receipt,'context':{**receipt['context'],'context':json.dumps(changed)}}
        with pytest.raises(Conflict):r.bound_synthesis(packet,'receipt',{'receipt':bad})
    stale=r.position_source(a,a['positions'][0],(b.now().date()+timedelta(days=4)).isoformat())
    assert stale['market_value'] is None and stale['unrealized_pnl'] is None and stale['weight']=='—'


def test_deep_json_receipt_is_rejected_as_evidence_conflict(app):
    packet=r.preview(app.store,{'symbol':'TEST','lenses':['position']})['packet']
    receipt={'synthesis':{'status':'structured'},'context':{'task':'research_synthesis','context':'['*2000+']'*2000}}
    with pytest.raises(Conflict):r.bound_synthesis(packet,'receipt',{'receipt':receipt})


def test_directional_evidence_precedence_and_frozen_history(app,tmp_path):
    from test_owner_business import ev
    s=app.store
    s.add_account(dict(id='direction-account',operation_id=uid(),name='Synthetic',currency='USD',opening_cash='1000'))
    s.trade(dict(id='direction-trade',operation_id=uid(),revision=0,account_id='direction-account',symbol='TEST',side='buy',quantity='1',price='10',fee='0',executed_at='2026-01-01T00:00:00Z'))
    quote(s)
    s.trade(dict(id=uid(),operation_id=uid(),revision=0,account_id='direction-account',symbol='OTHER',side='buy',quantity='10',price='10',fee='0',executed_at='2026-01-01T00:00:00Z'))
    quote(s,'OTHER') # Keep TEST below the global holdings cue while testing evidence precedence.
    first=ev(s,direction='weakens')
    inp={'symbol':'TEST','lenses':['position','valuation']}
    p=r.preview(s,inp)
    assert p['packet']['rule_report']['summary']['posture']=='thesis_review'
    assert p['packet']['rule_report']['evidence_balance']['counter']==1
    saved=r.save(s,body(p))
    # Unverified and expired directions must not affect the current assessment.
    ev(s,direction='strengthens',verification='unverified')
    yesterday=(b.now().date()-timedelta(days=1)).isoformat()
    ev(s,direction='strengthens',as_of=yesterday,expires_on=yesterday)
    assert r.preview(s,inp)['packet']['rule_report']['evidence_balance']['supporting']==0
    b.save(s,{'id':first['id'],'revision':1,'operation_id':uid()},archive=True)
    assert r.preview(s,inp)['packet']['rule_report']['summary']['posture']=='needs_thesis'
    assert r.history(s)['reports'][0]==saved
    backup=s.backup();target=tmp_path.resolve()/'direction-restored'
    restore_owner(s.directory/'backups'/backup['name'],target)
    assert r.history(OwnerStore(target))['reports'][0]==saved
    # Existing records with no direction remain neutral; invalid directions are rejected.
    legacy=ev(s);assert legacy['direction']=='neutral'
    with pytest.raises(ValueError):ev(s,direction='sell')


def test_direction_balance_order_and_concentration_precedence():
    today=b.now().date().isoformat()
    def evidence(id,direction,updated):
        return dict(id=id,kind='evidence',title=id,metric='other',value=None,verification='verified',as_of=today,expires_on=today,updated_at=updated,direction=direction)
    packet=dict(symbol='TEST',evaluated_on=today,lenses=['position'],records=[evidence('a','weakens','1'),evidence('b','weakens','2'),evidence('c','strengthens','3')])
    held=[dict(name='Synthetic',estimated_assets='1000',positions=[dict(symbol='TEST',market_value='20')])]
    assert r.compose(packet,held)['summary']['posture']=='thesis_review'
    assert r.compose(packet,[])['summary']['posture']=='research_first'
    packet['position_intelligence']={'symbol_holdings_usd':'300','total_holdings_usd':'1000','weight_percent':'30'}
    assert r.compose(packet,held)['summary']['posture']=='risk_review'
