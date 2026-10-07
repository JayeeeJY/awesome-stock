"""Read-only proposals from explicitly saved supplier sources. Never fetch providers."""
from . import owner_business as b,owner_company as company,owner_research_news as news
from . import owner_diagnosis_scope as scopes


def proposal(db,symbol):
    c=company.latest(db,symbol)
    if c is None:return None
    n=news.latest(db,symbol,b.now().date().isoformat())
    evidence={'verification':'supplier_unverified','company':{'id':c['id'],'revision':c['revision'],'digest':b.digest(c),'retrieved_at':c['retrieved_at']},'news':None}
    classification='unavailable';observed=c['retrieved_at'][:10]
    if n:
        observed=n['article']['published_at'][:10]
        classification=(n.get('sentiment') or {}).get('normalized') or 'unavailable'
        evidence['news']={'id':n['source_id'],'revision':n['source_revision'],'digest':n['source_digest'],'article':n['article']}
    return {'company':c['company']['name'],'news':classification,'as_of':observed,
            'source':'已保存供应商资料（未人工核验）：公司 '+c['id']+' v'+str(c['revision'])+('; 新闻 '+n['source_id']+' v'+str(n['source_revision']) if n else '; 未提供新闻'),
            'source_evidence':evidence}


def read(store,body):
    b.fields(body,'account_id symbol');scopes.scope_id(body['account_id']);symbol=body['symbol']
    if not isinstance(symbol,str):raise ValueError('invalid position key')
    with store.connection() as db:
        db.execute('BEGIN')
        account=scopes.resolve(store,db,body['account_id'])
        position=next((p for p in account['positions'] if p['symbol']==symbol),None)
        if position is None:raise ValueError('position missing')
        # Saved supplier adapters currently identify US tickers/USD only.
        value=proposal(db,position.get('ticker',symbol)) if position.get('source_currency',account['currency'])=='USD' else None
        return {'symbol':symbol,'context':value,'notice':'仅采用已确认保存的美国市场来源，不联网。供应商分类未人工核验；新闻仍按诊断三日有效期检查，缺失不补中性。公司资料获取日不等于财务截止日。'}
