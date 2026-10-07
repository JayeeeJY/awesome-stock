"""Isolated synthetic data provider, never a shipped entrypoint."""
import argparse,json,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from wsgiref.simple_server import make_server
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend/src'))
from awesome_stock.runtime.owner import application
from awesome_stock.runtime.server import QuietRequestHandler
p=argparse.ArgumentParser();p.add_argument('--port',type=int);p.add_argument('--data-dir',type=Path);p.add_argument('--flat',action='store_true');args=p.parse_args()
app=application(port=args.port,data_dir=args.data_dir,ui_dist=Path(__file__).resolve().parents[2]/'frontend/owner-ui/dist')
calls=[]
def send(host,path,body,**kwargs):
    q=parse_qs(urlsplit(path).query);calls.append({'host':host,'function':q.get('function'),'symbol':q.get('symbol')})
    (args.data_dir.parent/'calls.json').write_text(json.dumps(calls))
    if host=='eodhd.com':
        if '/exchange-symbol-list/' in path:
            return [{'Code':q['symbols'][0],'Name':'Synthetic HK Company','Currency':'HKD','Exchange':'HK','Type':'Common Stock'}]
        end=datetime.fromisoformat(q['to'][0]).date();start=datetime.fromisoformat(q['from'][0]).date()
        span=(end-start).days;count=300 if span>200 else 90 if span>30 else 20
        return [{'date':(end-timedelta(days=count-1-i)).isoformat(),'open':400-count+i,'high':403-count+i,'low':398-count+i,'close':401-count+i,'adjusted_close':1,'volume':10000+i} for i in range(count)]
    if q['function'][0]=='GLOBAL_QUOTE':
        return {'Global Quote':{'01. symbol':q['symbol'][0],'05. price':'20','07. latest trading day':datetime.now(timezone.utc).date().isoformat(),'08. previous close':'18'}}
    if q['function'][0]=='NEWS_SENTIMENT':
        return {'feed':[{'title':'Synthetic company event','summary':'Synthetic <script>window.newsExecuted=true</script>','url':'https://example.com/synthetic-news','source':'Synthetic publisher','time_published':(datetime.now(timezone.utc)-timedelta(hours=1)).strftime('%Y%m%dT%H%M%S'),'ticker_sentiment':[{'ticker':q['tickers'][0],'ticker_sentiment_label':'Somewhat-Bearish','ticker_sentiment_score':'-0.2'}]}]}
    if q['function'][0]=='OVERVIEW':
        return {'Symbol':q['symbol'][0],'Currency':'USD','Name':'Synthetic Company','Description':'Synthetic <script>window.companyExecuted=true</script>','Sector':'Technology','Industry':'Software','LatestQuarter':'2026-03-31','PERatio':'None','PriceToBookRatio':'2.5','MarketCapitalization':'3500000000000','ReturnOnEquityTTM':'0.1234','QuarterlyRevenueGrowthYOY':'-0.012','QuarterlyEarningsGrowthYOY':'0'}
    today=datetime.now(timezone.utc).date()
    series={}
    count=300 if q.get('outputsize')==['full'] else 90
    for i in range(count):
        value=100 if args.flat else 100+i;series[(today-timedelta(days=count-1-i)).isoformat()]={'1. open':str(value),'2. high':str(value+2),'3. low':str(value-2),'4. close':str(value+1),'5. volume':str(10000+i)}
    return {'Meta Data':{'2. Symbol':q['symbol'][0]},'Time Series (Daily)':series}

app.connections.send=send
with make_server('127.0.0.1',args.port,app,handler_class=QuietRequestHandler) as server:server.serve_forever()
