"""Read-only views of one consistent manual ledger snapshot, without quotes or FX."""
from decimal import Decimal, localcontext


def project(ledger):
    accounts=ledger['accounts']
    currencies={}
    positions=[]
    recent=[]
    with localcontext() as ctx:
        ctx.prec=60
        for a in accounts:
            totals=currencies.setdefault(a['currency'],{'currency':a['currency'],'cash':Decimal(0),'open_cost':Decimal(0),'realized_pnl':Decimal(0),'account_count':0})
            totals['account_count']+=1
            totals['cash']+=Decimal(a['cash'])
            for h in a['holdings']:
                totals['open_cost']+=Decimal(h['open_cost'])
                totals['realized_pnl']+=Decimal(h['realized_pnl'])
                if Decimal(h['quantity'])>0:
                    positions.append({**h,'account_id':a['id'],'account_name':a['name'],'currency':a['currency']})
            recent.extend({**t,'account_name':a['name'],'currency':a['currency']} for t in a['trades'])
        balances=[{k:format(v,'f') if isinstance(v,Decimal) else v for k,v in row.items()} for _,row in sorted(currencies.items())]
    recent.sort(key=lambda t:(t['executed_at'],t['sequence'],t['id']),reverse=True)
    gaps=[]
    if not accounts:gaps.append({'code':'no_accounts','text':'还没有资金账户。先建立账户和期初现金。','href':'/ledger'})
    elif not recent:gaps.append({'code':'no_trades','text':'账本中还没有交易记录。现金来自期初余额及已记录的出入金。','href':'/ledger'})
    if positions:gaps.append({'code':'missing_quotes','text':f'{len(positions)} 个账户持仓缺少行情，市值、未实现损益和资产配置比例暂不可用。','href':'/portfolio'})
    if len(currencies)>1:gaps.append({'code':'missing_fx','text':'多个币种分别展示，尚无汇率，不计算跨币种总资产。','href':'/portfolio'})
    return {'accounts':[{'id':a['id'],'name':a['name'],'currency':a['currency']} for a in accounts],'source':'owner_manual_ledger','account_count':len(accounts),'trade_count':len(recent),'open_position_count':len(positions),'currency_balances':balances,'positions':positions,'recent_trades':recent[:10],'data_gaps':gaps,'cross_currency_total':None,'market_value':None,'unrealized_pnl':None,'allocation':None,'live_quotes':False,'last_executed_at':recent[0]['executed_at'] if recent else None}
