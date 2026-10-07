"""Source-derived research event index. No invented thesis, news or calendar."""
import json
from datetime import date,datetime,timezone
from . import owner_business as b
from . import owner_research_earnings as earnings


def diagnostic_symbol(record, symbol):
    # Current research suppliers use US/USD tickers. A qualified HKD/CNY key
    # must not leak into the same-named US security's research timeline.
    return 'USD:' + symbol if record.get('account_id') == 'portfolio:all' else symbol


def calculate(db,symbol,evaluated_on):
    today=date.fromisoformat(evaluated_on);events=[]
    def add(record,event_type,quality,occurred,title,collection='documents',metadata=None):
        try:
            observed=datetime.fromisoformat(occurred.replace('Z','+00:00')) if len(occurred)>10 else datetime.combine(date.fromisoformat(occurred),datetime.min.time(),timezone.utc)
            observed=observed.replace(tzinfo=timezone.utc) if observed.tzinfo is None else observed.astimezone(timezone.utc)
        except (ValueError,TypeError,AttributeError):return
        age=(today-observed.date()).days
        if age<0:return
        events.append({'event_key':collection+':'+record['id']+(':v'+str(record['revision']) if collection=='document_versions' else ''),'event_type':event_type,'source_collection':collection,'source_id':record['id'],'source_revision':record['revision'],'source_digest':b.digest(record),'occurred_at':observed.isoformat(),'title':title,'evidence_quality':quality,'freshness':'fresh' if age<=14 else 'aging' if age<=60 else 'stale',**(metadata or {})})
    for r in b.records(db):
        kind=r['kind']
        if kind=='research_report' and r['packet']['symbol']==symbol:add(r,'analysis_report','medium',r['updated_at'],r['title'])
        elif kind=='decision' and r.get('symbol')==symbol:add(r,'decision_ticket','high',r['updated_at'],r['title'])
        elif kind=='review' and r.get('symbol')==symbol:add(r,'journal','high',r['reviewed_on'],r['title'])
        elif kind=='daily_brief' and diagnostic_symbol(r,symbol) in r.get('journal',{}).get('tickers',[]):add(r,'journal','high',r['captured_at'],r['title'])
        elif kind=='diagnosis' and any(p['symbol']==diagnostic_symbol(r,symbol) for p in r.get('report',{}).get('impacts',[])):add(r,'portfolio_impact','high',r['report']['generated_at'],r['title'])
        elif kind=='coach_journal':
            evidence=r.get('report',{}).get('evidence',{}).get('decision_evidence',{})
            if (evidence.get('decision') or {}).get('symbol')==symbol or any(t.get('symbol')==symbol for t in evidence.get('trades',[])):add(r,'journal','high',r['updated_at'],r['title'])
    seen_news=set()
    for snapshot in sorted(b.records(db,'news_snapshot'),key=lambda r:(r['updated_at'],r['id']),reverse=True):
        if snapshot['symbol']!=symbol:continue
        for article in snapshot['articles']:
            if article['id'] in seen_news:continue
            seen_news.add(article['id'])
            add(snapshot,'news','medium',article['published_at'],article['title'],metadata={
                'event_key':'news:'+symbol+':'+article['id'],'news_article':article,'verification':'supplier_unverified'})
    # Each explicit handling is an event. Resolve its immutable source version,
    # never the current symbol/title or the current due queue.
    for state in b.records(db,'action_state'):
        for payload, in db.execute('SELECT payload FROM document_versions WHERE id=? ORDER BY revision',(state['id'],)):
            r=json.loads(payload)
            if r.get('archived'):continue
            source_id,separator,revision=r.get('action_id','').rpartition('-v')
            if not separator or not revision.isdigit():continue
            source_row=db.execute('SELECT payload FROM document_versions WHERE id=? AND revision=?',(source_id,int(revision))).fetchone()
            if not source_row:continue
            source=json.loads(source_row[0])
            matched=source.get('kind') in {'decision','plan','candidate'} and source.get('symbol')==symbol
            matched=matched or source.get('kind')=='daily_brief' and diagnostic_symbol(source,symbol) in source.get('journal',{}).get('tickers',[])
            if not matched:continue
            labels={'confirmed':'已确认','snoozed':'已延后','resolved':'已解决','ignored':'已忽略','pending':'恢复待处理'}
            add(r,'reminder_action','high',r['updated_at'],'提醒'+labels.get(r['status'],r['status'])+' · '+source['title'],'document_versions',{
                'action':{'status':r['status'],'reason':r['reason'],'snooze_until':r['snooze_until']},
                'linked_source':{'id':source_id,'revision':int(revision),'title':source['title'],'digest':b.digest(source)}})
    for payload,revision in db.execute('SELECT payload,revision FROM trades'):
        r=json.loads(payload);r['revision']=revision
        if r['symbol']==symbol:add(r,'trade','high',r['executed_at'],r['side']+' '+r['quantity']+' @ '+r['price'],'trades')
    events.sort(key=lambda e:(e['occurred_at'],e['event_key']),reverse=True);total=len(events);selected=events[:40]
    counts={k:sum(e.get('evidence_quality')==k or e.get('freshness')==k for e in selected) for k in ['high','medium','low','fresh','aging','stale']}
    quality=round((counts['high']*100+counts['medium']*65+counts['low']*30)/len(selected)) if selected else None
    freshness=round((counts['fresh']*100+counts['aging']*55+counts['stale']*15)/len(selected)) if selected else None
    types={e['event_type'] for e in selected}
    if quality is not None:
        if not {'analysis_report','news'}&types:quality=min(quality,60)
        if not {'analysis_report','news','decision_ticket','trade','journal'}&types:quality=min(quality,35)
    earnings_window=earnings.calculate(db,symbol,evaluated_on)
    gaps=[label for kind,label in [('analysis_report','尚无固定研究报告来源'),('news','尚无已保存的匹配新闻来源'),('earnings','仅有推算窗口，尚无公司公告日期来源' if earnings_window else '尚无可推算财季或公司公告日期来源')] if kind not in types]
    return {'formula':'native-memory-record-scores-owner-v2','evaluated_on':evaluated_on,'symbol':symbol,'thesis':None,'latest_delta':None,'earnings_window':earnings_window,'quality_score':quality,'freshness_score':freshness,'counts':counts,'event_count':total,'scored_event_count':len(selected),'timeline':selected[:12],'coverage_gaps':gaps,'pending_questions':gaps,'scope':'按发生时间取最近40条评分、展示前12条；当前未归档记录与现存成交；提醒处理保留其未归档记录的各次版本，关联当时来源。不计未来日期记录，不是全部业务的历史版本账本。','notice':'分级权重来自原版来源类型；高等级表示有明确来源记录，不代表事实正确、投资价值或结论置信度。时效按当前UTC日期重新计算；缺失新闻/事件不补造。'}


def read(store,body):
    b.fields(body,'symbol');symbol=b.symbol(body['symbol'])
    with store.connection() as db:
        db.execute('BEGIN');return calculate(db,symbol,b.now().date().isoformat())
