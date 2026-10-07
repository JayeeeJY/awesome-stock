import json
import pytest
from awesome_stock.runtime.owner_research_synthesis import parse_synthesis
from test_owner_connections import configured

FACTS={'decision_brief':'Synthetic conclusion <script>not executable</script>', 'why_now':'Synthetic observation', 'uncertainty':'Missing source confirmation', 'decision_conditions':['Verify source']}

@pytest.mark.parametrize('provider',['openai','deepseek','ollama'])
def test_explicit_request_preserves_source_and_receipt(provider):
    calls=[]
    def send(*args,**kwargs):
        calls.append(args)
        output=json.dumps(FACTS)
        if provider=='openai':return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':output}]}]}
        if provider=='deepseek':return {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':output}}]}
        return {'done':True,'message':{'content':output}}
    c=configured(provider,send)
    payload={'task':'research_synthesis','question':'Synthesize TEST only','context':'Frozen TEST evidence v1'}
    p=c.preview(payload);assert p['payload']==payload and not calls
    r=c.generate({'token':p['token'],'confirm':True})
    assert r['context']==payload and r['synthesis']['verified'] is False
    assert r['synthesis']['decision_brief']==FACTS['decision_brief']
    assert r['stored'] is False and r['confirmed_by_user'] is False
    assert c.generate({'token':p['token'],'confirm':True})==r and len(calls)==1
    assert 'decision_brief' in json.dumps(calls[0][2])

@pytest.mark.parametrize('bad',[
    'not json', 'prefix '+json.dumps(FACTS), '[1]',
    json.dumps(FACTS|{'decision_brief':12}),
    json.dumps(FACTS|{'decision_brief':'x'*1201}),
    json.dumps(FACTS|{'uncertainty':''}),
    json.dumps(FACTS|{'decision_conditions':'verify'}),
    json.dumps(FACTS|{'decision_conditions':['one']*4}),
    json.dumps(FACTS|{'decision_conditions':[{}]}),
    json.dumps(FACTS|{'action':'buy'}),
    json.dumps(FACTS)[:-1]+',"decision_brief":"duplicate"}',
])
def test_invalid_schema_is_unstructured_without_retry(bad):
    c=configured('ollama',lambda *a,**kw:{'done':True,'message':{'content':bad}})
    p=c.preview({'task':'research_synthesis','question':'Summarize','context':'Synthetic'})
    r=c.generate({'token':p['token'],'confirm':True})
    assert r['draft']==bad and r['synthesis']['status']=='unstructured'
    assert r['synthesis']['verified'] is False and r['fallback'] is False


def test_exact_json_fence_accepted_without_field_truncation():
    assert parse_synthesis('```json\n'+json.dumps(FACTS)+'\n```')['decision_conditions']==FACTS['decision_conditions']
