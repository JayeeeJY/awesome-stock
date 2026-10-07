"""Isolated browser fixture. Never used by a shipped entrypoint."""
import argparse
import json
import sys
import time
from pathlib import Path
from wsgiref.simple_server import make_server
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend/src'))
from awesome_stock.runtime.owner import application
from awesome_stock.runtime.server import QuietRequestHandler
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int);parser.add_argument('--data-dir',type=Path);parser.add_argument('--fail-once-symbol',default='');parser.add_argument('--delay-seconds',type=float,default=0);parser.add_argument('--draft-chars',type=int,default=0);args=parser.parse_args()
if not 0 <= args.delay_seconds <= 3 or not 0 <= args.draft_chars <= 12000:parser.error('invalid synthetic delay or draft length')
app=application(port=args.port,data_dir=args.data_dir,ui_dist=Path(__file__).resolve().parents[2]/'frontend/owner-ui/dist')
calls=[]
failed_symbols=set()
def synthetic_send(*values,**kwargs):
    calls.append({'host':values[0],'path':values[1]})
    (args.data_dir.parent/'calls.json').write_text(json.dumps(calls))
    if args.delay_seconds:time.sleep(args.delay_seconds)
    payload=json.loads(values[2]['messages'][-1]['content'])
    if args.fail_once_symbol:
        context=json.loads(payload.get('context') or '{}')
        symbol=context.get('symbol')
        if symbol==args.fail_once_symbol and symbol not in failed_symbols:
            failed_symbols.add(symbol)
            return {}
    if payload.get('task')=='research_synthesis':
        return {'done':True,'message':{'content':json.dumps({'decision_brief':'Synthetic research <script>window.synthesisExecuted=true</script>','why_now':'Synthetic new evidence','uncertainty':'Source remains unverified','decision_conditions':['Verify original source']})}}
    if values[0]=='api.deepseek.com':
        if values[2].get('thinking')!={'type':'disabled'}:return {'choices':[{'finish_reason':'length','message':{'role':'assistant','content':None,'reasoning_content':'Synthetic exhausted budget'}}]}
        return {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'连接成功。' if payload.get('task')=='connection_test' else 'Synthetic answer: '+payload['question']}}]}
    if values[0]=='api.openai.com':return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'连接成功。'}]}]}
    return {'done':True,'message':{'content':'Synthetic daily summary <script>window.untrustedExecuted=true</script>'+(' LONG_SEGMENT'*args.draft_chars)[:args.draft_chars]}}
app.connections.send=synthetic_send
with make_server('127.0.0.1',args.port,app,handler_class=QuietRequestHandler) as server:server.serve_forever()
