"""Frozen period rollups of unique decision trades, with explicit missing coverage."""
from collections import Counter
from datetime import date, timezone
from decimal import Decimal, localcontext
from . import owner_coach as coach, owner_business as b
from .owner import identifier
from .local import Conflict


def conclusions(summary):
    strengths=[];risks=[];actions=[]
    patterns=summary['patterns'];count=summary['scored_count']
    labels={'missing_reason':'缺少决策依据','overtrading':'14日内交易频率','rapid_reversal':'7日内方向反转','chasing':'买价上涨后加仓','averaged_down_unreviewed':'降价加仓缺更新理由'}
    if count:
        strengths.append({'text':'完整评分样本均保留明确决策关联。','basis':{'scored_count':count}})
        if not patterns.get('rapid_reversal'):
            strengths.append({'text':'完整评分样本未命中7日方向反转规则；不涵盖被排除样本。','basis':{'scored_count':count,'rapid_reversal':0}})
    for code,n in sorted(patterns.items(),key=lambda item:(-item[1],item[0]))[:5]:
        risks.append({'text':labels.get(code,code)+'：'+str(n)+'次。','basis':{'pattern':code,'count':n}})
    if summary['stale_count'] or summary['incomplete_count']:
        risks.append({'text':'部分依据已变化或不完整，不能据此评价全部决策。','basis':{'stale_count':summary['stale_count'],'incomplete_count':summary['incomplete_count']}})
        actions.append('先核对变化与缺失依据，再重新生成相关教练报告。')
    if patterns.get('missing_reason'):actions.append('在下次决策复核中补充可证伪的理由与证据。')
    if patterns.get('overtrading') or patterns.get('rapid_reversal'):actions.append('复核同标的密集操作与反转的原因，检查是否需要冷静期。')
    if not actions:actions.append('没有完整样本，先补齐决策与历史依据。' if not count else '独立复核结果证据，不用短期盈亏反过来改写原过程记录。')
    return {'method':'deterministic-rules-v1','strengths':strengths,'risks':risks,'next_actions':actions,
            'scope':'仅覆盖完整且依据未变化的规则样本，不代表投资质量认可。'}


def calculate(store, db, body):
    b.fields(body,'start end')
    start=date.fromisoformat(b.day(body['start']));end=date.fromisoformat(b.day(body['end']))
    if not 0 <= (end-start).days <= 366:raise ValueError('invalid report range')
    reports=sorted(b.records(db,'coach_report'),key=lambda r:(r['updated_at'],r['id']))
    annotations={r['report_id']:r for r in b.records(db,'coach_annotation')}
    latest={}
    for r in reports:
        try:current,token=coach.evidence(store,db,r['input'])
        except ValueError:current,token={},None
        trades={t['id']:t for t in r['report']['evidence']['decision_evidence']['trades']}
        for check in r['report']['checks']:
            trade=trades[check['trade_id']]
            latest[trade['id']]={'trade':trade,'check':check,'report_id':r['id'],'report_revision':r['revision'],
                                 'stale':current.get('process_evidence_token')!=r['report'].get('process_evidence_token',r['evidence_token']), 'outcome_stale':token!=r['evidence_token'],'annotation':annotations.get(r['id'])}
    within=lambda t:start<=coach.instant(t['executed_at']).astimezone(timezone.utc).date()<=end
    entries=[row for _,row in sorted(latest.items()) if within(row['trade'])]
    def rollup(rows):
        valid=[r for r in rows if not r['stale'] and r['check']['process_score'] is not None]
        outcomes=[r for r in rows if not r['outcome_stale'] and r['check'].get('outcome_score') is not None]
        with localcontext() as ctx:
            ctx.prec=60
            score=format(sum(Decimal(r['check']['process_score']) for r in valid)/len(valid),'.2f') if valid else None
            outcome_score=format(sum(Decimal(r['check']['outcome_score']) for r in outcomes)/len(outcomes),'.2f') if outcomes else None
        counts=Counter(p['code'] for r in valid for p in r['check']['patterns'])
        return {'unique_trade_count':len(rows),'scored_count':len(valid),'stale_count':sum(r['stale'] for r in rows),
                'incomplete_count':sum(not r['stale'] and r['check']['process_score'] is None for r in rows),
                'process_score':score,'outcome_score':outcome_score,
                'outcome_scored_count':len(outcomes),
                'outcome_stale_count':sum(r['outcome_stale'] for r in rows),
                'outcome_pending_count':sum(not r['outcome_stale'] and r['check'].get('outcome_score') is None for r in rows),'patterns':dict(sorted(counts.items())),
                'reviewed_count':sum(bool(r['annotation'] and r['annotation']['status'] in {'reviewed','journaled'}) for r in rows)}
    months={}
    for r in entries:
        month=coach.instant(r['trade']['executed_at']).astimezone(timezone.utc).strftime('%Y-%m')
        months.setdefault(month,[]).append(r)
    active=[t for a in b.ledger_snapshot(store,db) for t in a['trades'] if within(t)]
    linked={r[0] for r in db.execute('SELECT trade_id FROM trade_links WHERE decision_id IS NOT NULL')}
    from . import owner_trade_context
    important={t['id'] for t in active if owner_trade_context.snapshot(db,t['id'])['qualification']=='required_without_context'}
    result={'start':start.isoformat(),'end':end.isoformat(),'date_basis':'UTC trade timestamp',
            'summary':rollup(entries),'months':[{'month':m,**rollup(rows)} for m,rows in sorted(months.items())],
            'ordinary_trade_count':sum(t['id'] not in linked and t['id'] not in important for t in active),
            'important_without_report_count':sum(t['id'] in important and t['id'] not in latest for t in active),
            'linked_without_report_count':sum(t['id'] in linked and t['id'] not in latest for t in active),
            'entries':entries,'formula':'coach-period-v2','executes_trades':False}
    result['conclusions']=conclusions(result['summary'])
    # New reports and review annotations change the packet; saved period snapshots do not.
    return result,b.digest(result)


def preview(store,body):
    with store.connection() as db:
        db.execute('BEGIN');report,token=calculate(store,db,body)
        return {'report':report,'token':token}


def save(store,body):
    b.fields(body,'id operation_id input expected_token');identifier(body['id'])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'coach_period_save')
        if old is not None:return old
        if db.execute('SELECT 1 FROM documents WHERE id=?',(body['id'],)).fetchone():raise Conflict('period report immutable')
        report,token=calculate(store,db,body['input'])
        if token!=body['expected_token']:raise Conflict('period evidence changed')
        result=b._put(store,db,{'id':body['id'],'revision':0},
            {'kind':'coach_period_report','title':'教练周期复盘 '+body['input']['start']+'—'+body['input']['end'],
             'input':body['input'],'report':report,'evidence_token':token})
        return store._result(db,body,fp,result)


def history(store):
    with store.connection() as db:
        return {'reports':sorted(b.records(db,'coach_period_report'),key=lambda r:(r['updated_at'],r['id']),reverse=True)}
