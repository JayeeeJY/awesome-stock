"""Isolated browser transport fixture. Never used by the production launcher."""
import argparse
from datetime import datetime, timezone
from wsgiref.simple_server import make_server
from awesome_stock.runtime.owner import application
from awesome_stock.runtime.server import QuietRequestHandler
p=argparse.ArgumentParser();p.add_argument('--port',type=int);p.add_argument('--data-dir');args=p.parse_args()
app=application(port=args.port,data_dir=args.data_dir)
def fixture(host,path,body,key='',local=False):
    if host=='www.alphavantage.co':return {'Global Quote':{'01. symbol':'TEST','05. price':'20','07. latest trading day':datetime.now(timezone.utc).date().isoformat()}}
    text='[离线浏览器测试替身] 事实：仅依据用户选择的合成上下文。推断：待核验。用户规则：无。下一步：核对证据。不确定性：无外部验证。'
    if local:return {'done':True,'message':{'content':text}}
    return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':text}]}]}
app.connections.send=fixture
with make_server('127.0.0.1',args.port,app,handler_class=QuietRequestHandler) as server:server.serve_forever()
