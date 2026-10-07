import pytest
from awesome_stock.storage import owner_business as b
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import OwnerStore,restore_owner
from test_owner_business import funded,obj,uid
from test_owner_api import app

def layer(**changes):return dict(account_id='account-test',title='Core',tier=1,sector='Broad market',target_percent='60',target_amount=None,max_single_percent='25',strategy_note='Synthetic strategy',symbols=['TEST'],stock_pool=['NEW'])|changes

def test_layer_version_archive_restore_and_no_ledger_write(funded,tmp_path):
    before=funded.ledger();l=obj(funded,'allocation_layer',layer());updated=obj(funded,'allocation_layer',layer(title='Core revised'),l['id'],1)
    with pytest.raises(Conflict):obj(funded,'allocation_layer',layer(title='Stale'),l['id'],1)
    assert updated['revision']==2 and funded.ledger()==before
    b.save(funded,dict(id=l['id'],revision=2,operation_id=uid()),archive=True)
    assert not [r for r in b.workspace(funded)['records'] if r['kind']=='allocation_layer']
    assert len([r for r in b.workspace(funded)['versions'] if r['id']==l['id']])==3
    backup=funded.backup();target=tmp_path.resolve()/'restored';restore_owner(funded.directory/'backups'/backup['name'],target)
    assert b.workspace(OwnerStore(target))['versions']==b.workspace(funded)['versions']


def test_membership_unique_but_watch_pool_can_overlap(funded):
    first=obj(funded,'allocation_layer',layer())
    with pytest.raises(Conflict):obj(funded,'allocation_layer',layer(title='Other'))
    obj(funded,'allocation_layer',layer(title='Other',symbols=[],stock_pool=['TEST']))
    b.save(funded,dict(id=first['id'],revision=1,operation_id=uid()),archive=True)
    assert obj(funded,'allocation_layer',layer(title='Reassigned'))['symbols']==['TEST']

@pytest.mark.parametrize('change',[{'tier':True},{'tier':11},{'target_percent':'101'},{'max_single_percent':'-1'},{'target_amount':'NaN'},{'symbols':['TEST','test']},{'symbols':'TEST'},{'stock_pool':['INVALID SPACE']}])
def test_layer_input_rejected(funded,change):
    with pytest.raises(ValueError):obj(funded,'allocation_layer',layer(**change))


def test_atomic_position_move_clear_history_and_idempotency(funded):
    first=obj(funded,'allocation_layer',layer());second=obj(funded,'allocation_layer',layer(title='Other',symbols=[]));before=funded.ledger()
    body=dict(operation_id=uid(),account_id='account-test',symbol='TEST',layer_id=second['id'],expected_token=b.workspace(funded)['token'])
    result=b.assign_position(funded,body);assert b.assign_position(funded,body)==result
    current={r['id']:r for r in b.workspace(funded)['records']}
    assert current[first['id']]['symbols']==[] and current[second['id']]['symbols']==['TEST']
    assert len(result['changed'])==2 and funded.ledger()==before
    with pytest.raises(Conflict):b.assign_position(funded,body|{'operation_id':uid()})
    b.assign_position(funded,body|{'operation_id':uid(),'layer_id':None,'expected_token':b.workspace(funded)['token']})
    assert all(not r['symbols'] for r in b.workspace(funded)['records'])
    assert len(b.workspace(funded)['versions'])==5

@pytest.mark.parametrize('change',[{'symbol':'MISSING'},{'layer_id':'missing-layer'},{'account_id':'missing-account'}])
def test_invalid_assignment_keeps_layers(funded,change):
    l=obj(funded,'allocation_layer',layer());before=b.workspace(funded)
    with pytest.raises(ValueError):b.assign_position(funded,dict(operation_id=uid(),account_id='account-test',symbol='TEST',layer_id=l['id'],expected_token=before['token'])|change)
    assert b.workspace(funded)==before


def test_layer_allocation_exact_cash_gaps_and_fixed_versions(funded):
    from test_owner_business import quote
    quote(funded);l=obj(funded,'allocation_layer',layer(target_amount='1'))
    before=funded.ledger();input={'type':'layer_allocation','account_id':'account-test','cash_percent':'40'}
    preview=b.preview_plan(funded,input);rows=preview['result']['rows']
    assert rows[0]['adjustment_value']=='459.4' and rows[-1]['adjustment_value']=='-459.4'
    saved=obj(funded,'scenario',dict(title='Layer snapshot',input=input,expected_token=preview['token']))
    assert saved['result']['layer_evidence'][0]['revision']==1
    obj(funded,'allocation_layer',layer(target_percent='50'),l['id'],1)
    with pytest.raises(Conflict):obj(funded,'scenario',dict(title='Stale',input=input,expected_token=preview['token']))
    assert saved['result']['layer_evidence'][0]['target_percent']=='60' and funded.ledger()==before


def test_layer_allocation_incomplete_target_and_price_rejected(funded):
    obj(funded,'allocation_layer',layer())
    input=dict(type='layer_allocation',account_id='account-test',cash_percent='40')
    with pytest.raises(ValueError):b.preview_plan(funded,input)
    from test_owner_business import quote
    quote(funded)
    with pytest.raises(ValueError):b.preview_plan(funded,input|{'cash_percent':'0'})
    with pytest.raises(ValueError):b.preview_plan(funded,input|{'cash_percent':'101'})
