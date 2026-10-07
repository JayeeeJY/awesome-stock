import copy
from datetime import date,timedelta,datetime,timezone
from decimal import Decimal
import json
import uuid
import pytest
from awesome_stock.storage import owner_business as b, owner_privacy as p
from awesome_stock.storage.owner import OwnerStore, restore_owner
from awesome_stock.storage.local import Conflict
from awesome_stock.runtime.owner import application
from test_owner_api import app,request,login,PASSWORD

def uid():return str(uuid.uuid4())
def obj(store,kind,data,id=None,revision=0):return b.save(store,dict(id=id or uid(),revision=revision,operation_id=uid(),kind=kind,data=data))
def candidate(s,sy='TEST'):return obj(s,'candidate',dict(symbol=sy,title=sy+' company',market='US',thesis='Synthetic only',review_on='2026-01-01'))
def ev(s,sy='TEST',metric='revenue_growth',value='20',**extra):
    today=datetime.now(timezone.utc).date().isoformat();return obj(s,'evidence',dict(symbol=sy,title='Synthetic metric',metric=metric,value=value,source='Synthetic source',as_of=today,expires_on=today,verification='verified')|extra)
def quote(s,sy='TEST',**extra):return obj(s,'quote',dict(symbol=sy,currency='USD',price='20',as_of=datetime.now(timezone.utc).date().isoformat(),source='Synthetic manual quote')|extra)
@pytest.fixture
def funded(app):
    s=app.store;s.add_account(dict(id='account-test',operation_id=uid(),name='Synthetic',currency='USD',opening_cash='1000'))
    s.trade(dict(id='trade-test',operation_id=uid(),revision=0,account_id='account-test',symbol='TEST',side='buy',quantity='10',price='10',fee='1',executed_at='2026-01-01T00:00:00Z'))
    return s

def test_version_archive_idempotency_and_kind_isolation(funded):
    c=candidate(funded);body=dict(id=c['id'],revision=1,operation_id=uid(),kind='candidate',data={k:c[k] for k in ['symbol','title','market','thesis','review_on']});body['data']['title']='Revised'
    r=b.save(funded,body);assert r['revision']==2 and b.save(funded,body)==r
    with pytest.raises(Conflict):b.save(funded,body|{'operation_id':uid()})
    assert not funded.documents()['documents']
    b.save(funded,dict(id=c['id'],revision=2,operation_id=uid()),archive=True)
    assert not b.workspace(funded)['records'] and len(b.workspace(funded)['versions'])==3
    with pytest.raises(Conflict):candidate(funded) if False else b.save(funded,body|{'revision':3,'operation_id':uid()})

@pytest.mark.parametrize('extra',[{'as_of':'2999-01-01'},{'source':'javascript://x'},{'source':'https://name:secret@example.com/'},{'verification':'auto'},{'value':'NaN'},{'expires_on':'1900-01-01'},{'metric':'rating'},{'value':'1e9'}])
def test_evidence_validation(funded,extra):
    with pytest.raises(ValueError):ev(funded,**extra)

def test_screen_missing_stale_unverified_and_no_ranking(funded):
    candidate(funded);rules=dict(market='ALL',growth_min='12',margin_min='35',debt_max='2')
    assert b.screen(funded,rules)['rows'][0]['status']=='needs_evidence'
    e=ev(funded);ev(funded,metric='gross_margin',value='40');ev(funded,metric='net_debt_ebitda',value='1')
    assert b.screen(funded,rules)['rows'][0]['status']=='matched'
    ev(funded,value='0',verification='unverified')
    r=b.screen(funded,rules);assert r['rows'][0]['status']=='needs_evidence' and r['ranked'] is False
    ev(funded,value='5');assert b.screen(funded,rules)['rows'][0]['status']=='excluded'
    with pytest.raises(Conflict):candidate(funded)

def test_handoff_fixed_evidence_and_atomic_stale_check(funded):
    c=candidate(funded);e=ev(funded);w=b.workspace(funded);body=dict(id=uid(),operation_id=uid(),candidate_ids=[c['id']],expected_token=w['token'])
    result=b.handoff(funded,body);assert b.handoff(funded,body)==result
    note=result['notes'][0]
    assert note['symbol']=='TEST' and e['id'] in note['content']
    assert note['content'].startswith('候选交接快照 · 仅供继续研究')
    assert '观察逻辑：Synthetic only' in note['content']
    assert '证据快照（1 条' in note['content']
    assert '人工已核验' in note['content']
    ev(funded,value='50');assert funded.documents()['documents'][0]['content']==note['content']
    with pytest.raises(Conflict):b.handoff(funded,body|{'id':uid(),'operation_id':uid()})
    with pytest.raises(ValueError):b.handoff(funded,body|{'id':uid(),'operation_id':uid(),'candidate_ids':[c['id'],'missing-test'],'expected_token':b.workspace(funded)['token']})
    assert len(funded.documents()['documents'])==1

def test_quote_valuation_currency_stale_and_baseline(funded):
    base=obj(funded,'baseline',{'title':'Before'})
    assert b.workspace(funded)['accounts'][0]['estimated_assets'] is None
    quote(funded,currency='HKD');assert b.workspace(funded)['accounts'][0]['estimated_assets'] is None
    quote(funded,as_of=(datetime.now(timezone.utc).date()-timedelta(days=4)).isoformat());assert b.workspace(funded)['accounts'][0]['positions'][0]['quote_status']=='stale'
    quote(funded);a=b.workspace(funded)['accounts'][0];assert a['estimated_assets']=='1099' and a['positions'][0]['unrealized_pnl']=='99'
    assert b.workspace(funded)['changes'][0]['cash_change']=='0'
    from awesome_stock.storage.owner_cash import save
    save(funded,dict(id=uid(),revision=0,operation_id=uid(),account_id='account-test',direction='deposit',amount='25',occurred_at='2026-01-02T00:00:00Z',note='test'))
    assert b.workspace(funded)['changes'][0]['cash_change']=='25'
    assert b.workspace(funded)['changes'][0]['cost_change']=='0'

def plan_input(**extra):return dict(type='pre_trade',account_id='account-test',symbol='TEST',side='buy',quantity='2',price='15',fee='1',max_percent='100')|extra

def test_pretrade_mark_execution_difference_and_no_write(funded):
    with pytest.raises(ValueError):b.preview_plan(funded,plan_input())
    quote(funded);before=funded.path.read_bytes();r=b.preview_plan(funded,plan_input())['result'];assert funded.path.read_bytes()==before
    assert r['cash_after']=='868' and r['quantity_after']=='12' and r['position_value_after']=='240' and r['estimated_assets_after']=='1108'
    assert r['executes_trades'] is False
    assert b.preview_plan(funded,plan_input(side='sell',quantity='11'))['result']['status']=='blocked'
    assert b.preview_plan(funded,plan_input(quantity='100'))['result']['status']=='blocked'
    assert b.preview_plan(funded,plan_input(side='sell',quantity='1',price='1',fee='999'))['result']['status']=='blocked'

def test_allocation_build_budget_and_saved_snapshot(funded):
    quote(funded);r=b.preview_plan(funded,dict(type='allocation',account_id='account-test',targets={'TEST':'50','@CASH':'50'}))['result']
    assert sum(Decimal(x['adjustment_value']) for x in r['rows'])==0
    with pytest.raises(ValueError):b.preview_plan(funded,dict(type='allocation',account_id='account-test',targets={'@CASH':'100'}))
    inp=dict(type='build_up',account_id='account-test',symbol='TEST',price='20',fee='1',max_percent='100',budget='100',stages=2)
    r=b.preview_plan(funded,inp);assert r['result']['planned_cash']=='82' and r['result']['unallocated_budget']=='18'
    snapshot=obj(funded,'scenario',dict(title='Test',input=inp,expected_token=r['token']))
    quote(funded,price='22')
    with pytest.raises(Conflict):obj(funded,'scenario',dict(title='Old',input=inp,expected_token=r['token']))
    assert next(x for x in b.workspace(funded)['records'] if x['id']==snapshot['id'])['result']==r['result']

def test_actions_manual_feedback_rules_and_empty_trends(funded):
    c=candidate(funded);a=b.workspace(funded)['actions'][0]
    assert a['source_id']==c['id'] and a['priority']=='P1'
    with pytest.raises(ValueError):obj(funded,'action_state',dict(action_id=a['id'],status='ignored',reason='',snooze_until=''))
    obj(funded,'action_state',dict(action_id=a['id'],status='ignored',reason='synthetic false positive',snooze_until=''))
    assert b.workspace(funded)['actions'][0]['status']=='ignored'
    with pytest.raises(ValueError):obj(funded,'rule',dict(title='Rule',condition='condition',action='check',scope='all',enabled=True))
    rule=obj(funded,'rule',dict(title='Rule',condition='condition',action='check',scope='all',enabled=False))
    obj(funded,'rule',{k:rule[k] for k in ['title','condition','action','scope']}|{'enabled':True},id=rule['id'],revision=1)
    assert b.trends(funded,{'from':'2026-01-01','to':'2026-12-31'})['total']==0

def test_reset_preview_stale_password_csrf_and_other_process_session(funded,app):
    auth=login(app);second=application(port=4322,data_dir=funded.directory);other=login(second);candidate(funded);before=p.preview(funded);quote(funded)
    body=dict(token=before['token'],confirmation='清空当前业务数据',current_password=PASSWORD)
    assert request(app,'/api/v1/owner/reset','POST',body,**auth)['status']==409
    body['token']=p.preview(funded)['token']
    assert request(app,'/api/v1/owner/reset','POST',body|{'current_password':'wrong'},**auth)['status']==401
    assert request(app,'/api/v1/owner/reset','POST',body,**(auth|{'csrf':'bad'}))['status']==403
    backup=funded.backup();assert request(app,'/api/v1/owner/reset','POST',body,**auth)['status']==200
    assert all(v==0 for v in p.preview(funded)['counts'].values()) and funded.owner() is not None
    assert request(second,'/api/v1/owner/ledger',**other)['status']==401
    assert request(app,'/api/v1/owner/ledger',**login(app))['body']['accounts']==[]
    assert (funded.directory/'backups'/backup['name']).exists()
    with funded.connection() as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

def test_backup_delete_is_scoped_and_restore_includes_business(funded,tmp_path):
    candidate(funded);quote(funded);backup=funded.backup();other=funded.backup();item=p.backup_list(funded)['backups'][0]
    restored=tmp_path/'restored';restore_owner(funded.directory/'backups'/backup['name'],restored);new=OwnerStore(restored)
    assert len(b.workspace(new)['records'])==2
    with pytest.raises(Conflict):p.delete_backup(funded,dict(name='../owner.sqlite3',token=item['token'],confirmation='删除此备份',current_password=PASSWORD))
    p.delete_backup(funded,dict(name=item['name'],token=item['token'],confirmation='删除此备份',current_password=PASSWORD))
    assert len(p.backup_list(funded)['backups'])==1 and funded.path.exists()

@pytest.mark.parametrize('endpoint,method,body',[('business','GET',None),('business','POST',{}),('screen','POST',{}),('planning','POST',{}),('trends','POST',{}),('privacy','GET',None),('connections','GET',None),('connections','POST',{}),('ai-preview','POST',{}),('ai-generate','POST',{}),('quote-fetch','POST',{})])
def test_new_routes_require_auth(app,endpoint,method,body):
    assert request(app,'/api/v1/owner/'+endpoint,method,body)['status']==401

def test_nonempty_trends_counts_current_versions_not_profit(app):
    from test_research_store import document
    from test_owner_evolve import review
    from awesome_stock.storage.owner_evolve import save_review
    s=app.store;s.save_document(document('decision'));body=review(s,reviewed_on='2026-01-15');first=save_review(s,body)
    save_review(s,body|{'revision':1,'operation_id':uid(),'process_status':'deviated','outcome_status':'observed','outcome_note':'Positive result does not undo deviation'})
    r=b.trends(s,{'from':'2026-01-01','to':'2026-01-31'});m=r['months'][0]
    assert r['total']==1 and m['deviated']==1 and m['observed']==1 and m['followed']==0 and m['record_ids']==[first['id']]
    save_review(s,{'id':first['id'],'revision':2,'operation_id':uid()},archive=True)
    assert b.trends(s,{'from':'2026-01-01','to':'2026-12-31'})['total']==0

def test_reset_transaction_failure_rolls_back_every_table(funded):
    candidate(funded);before=p.preview(funded)
    with funded.transaction() as db:db.execute("CREATE TRIGGER prevent_account_delete BEFORE DELETE ON accounts BEGIN SELECT RAISE(ABORT,'test failure'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):p.reset(funded,dict(token=before['token'],confirmation='清空当前业务数据',current_password=PASSWORD),funded.owner().credential.digest_hex)
    assert p.preview(funded)==before

def test_allocation_cash_ticker_not_confused_with_cash_balance(funded):
    quote(funded)
    funded.trade(dict(id=uid(),operation_id=uid(),revision=0,account_id='account-test',symbol='CASH',side='buy',quantity='1',price='5',fee='0',executed_at='2026-01-03T00:00:00Z'))
    quote(funded,sy='CASH',price='5')
    r=b.preview_plan(funded,dict(type='allocation',account_id='account-test',targets={'TEST':'40','CASH':'10','@CASH':'50'}))['result']
    values={x['symbol']:x['current_value'] for x in r['rows']}
    assert values['CASH']=='5' and values['@CASH']=='894'

def test_reset_invalidates_old_csv_preview_even_when_business_recreated(app):
    from awesome_stock.storage.owner_transfer import preview
    s=app.store;body=dict(id='account-test',operation_id='operation-account',name='Synthetic',currency='USD',opening_cash='1000');s.add_account(body)
    inp={'account_id':'account-test','csv':'record_id,symbol,side,quantity,price,fee,executed_at\nrow1,TEST,buy,1,10,0,2026-01-01T00:00:00Z\n'}
    token=preview(s,inp)['preview_token'];p.reset(s,dict(token=p.preview(s)['token'],confirmation='清空当前业务数据',current_password=PASSWORD),s.owner().credential.digest_hex);s.add_account(body)
    assert preview(s,inp)['preview_token']!=token


def test_valuation_evidence_survives_backup_without_qualifying_screen(funded,tmp_path):
    candidate(funded)
    pe=ev(funded,metric='pe',value='15.25')
    pb=ev(funded,metric='pb',value='2.5')
    result=b.screen(funded,dict(market='ALL',growth_min='12',margin_min='35',debt_max='2'))
    assert result['rows'][0]['status']=='needs_evidence'
    assert set(result['rows'][0]['gaps'])=={'revenue_growth','gross_margin','net_debt_ebitda'}
    backup=funded.backup();destination=tmp_path/'valuation-restored'
    restore_owner(funded.directory/'backups'/backup['name'],destination)
    restored={r['id']:r for r in b.workspace(OwnerStore(destination))['records']}
    assert restored[pe['id']]['value']=='15.25'
    assert restored[pb['id']]['source']=='Synthetic source'
