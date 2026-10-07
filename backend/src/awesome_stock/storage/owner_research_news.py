"""Latest explicitly saved article and supplied classification, not a fact verdict."""
from datetime import date
from . import owner_business as b


def latest(db,symbol,evaluated_on):
    candidates=[]
    for source in b.records(db,'news_snapshot'):
        if source['symbol']!=symbol:continue
        for article in source['articles']:candidates.append((article,source))
    if not candidates:return None
    article,source=max(candidates,key=lambda pair:(pair[0]['published_at'],pair[1]['updated_at'],pair[1]['id'],pair[0]['id']))
    age=(date.fromisoformat(evaluated_on)-date.fromisoformat(article['published_at'][:10])).days
    sentiment=article.get('sentiment')
    return {'article':article,'source_id':source['id'],'source_revision':source['revision'],'source_digest':b.digest(source),'evaluated_on':evaluated_on,
            'freshness':'fresh' if 0<=age<=14 else 'stale','sentiment':sentiment,'notice':'最新已保存新闻的供应商分类，不是事实核验或投资结论；超过14个UTC日期日不生成当前负面提示。缺分类不填中性，不回退到更旧的负面新闻。'}
