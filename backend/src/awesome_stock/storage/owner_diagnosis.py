"""Owner diagnosis facts; source formulas adapted from portfolio_automation_service.

A recorded diagnostic is immutable and is not a forecast or trade instruction.
Missing inputs never become zero-loss observations or a completed overall score.
"""
from decimal import Decimal, localcontext
from datetime import date
from . import owner_business as business
from .owner import identifier, number, text
from .local import Conflict
from . import owner_diagnosis_scope as scopes
from awesome_stock.research.market_identity import china_day

D=Decimal
FORMULA='selfuse-five-dimensions-owner-v1'
NAMES={'concentration':'集中度','profitability':'浮盈持仓比例','diversification':'分散度','position_size':'仓位大小','discipline':'纪律信号'}


def policy(raw):
    business.fields(raw,'warning_percent max_percent shock_percent custom_rules')
    warning=D(number(raw['warning_percent'],positive=True));maximum=D(number(raw['max_percent'],positive=True));shock=D(number(raw['shock_percent'],positive=True))
    if not warning<maximum<=100 or shock>100:raise ValueError('invalid thresholds')
    if not isinstance(raw['custom_rules'],list) or len(raw['custom_rules'])>20:raise ValueError('invalid custom rules')
    rules=[]
    for r in raw['custom_rules']:
        business.fields(r,'name metric operator threshold severity')
        if r['metric'] not in {'position_percent','unrealized_pnl_percent'} or r['operator'] not in {'gt','gte','lt','lte'} or r['severity'] not in {'critical','watch'}:raise ValueError('invalid custom rule')
        rules.append({**r,'name':text(r['name'],120),'threshold':business.signed(r['threshold'])})
    return {**raw,'warning_percent':str(warning),'max_percent':str(maximum),'shock_percent':str(shock),'custom_rules':rules}


def context(raw,positions,db=None,currency=None):
    if not isinstance(raw,dict) or set(raw)-{p['symbol'] for p in positions}:raise ValueError('unknown context symbol')
    result={}
    for sy,r in raw.items():
        business.fields(r,'company news source as_of'+(' source_evidence' if 'source_evidence' in r else ''))
        if 'source_evidence' in r:
            from .owner_diagnosis_sources import proposal
            position=next(p for p in positions if p['symbol']==sy)
            source_currency=position.get('source_currency',currency)
            if db is None or source_currency!='USD' or r!=proposal(db,position.get('ticker',sy)):raise Conflict('saved diagnostic sources changed; review again')
        if r['news'] not in {'positive','negative','neutral','unavailable'}:raise ValueError('invalid news observation')
        observed=business.day(r['as_of'])
        if observed>business.now().date().isoformat():raise ValueError('future observation')
        result[sy]={'company':text(r['company'],200),'news':r['news'],'source':text(r['source'],500),'as_of':observed}
        if 'source_evidence' in r:result[sy]['source_evidence']=r['source_evidence']
    return result


def _calculate(store,db,body):
    if not isinstance(body,dict):raise ValueError('invalid diagnostic input')
    business.fields(body,'account_id policy holding_context'+(' constitution_revision' if 'constitution_revision' in body else ''))
    scopes.scope_id(body['account_id']);rules=policy(body['policy'])
    constitution=None
    if 'constitution_revision' in body:
        import json
        from .owner_constitution import ID
        revision=body['constitution_revision']
        if type(revision) is not int or revision<1:raise ValueError('invalid constitution revision')
        row=db.execute('SELECT payload FROM document_versions WHERE id=? AND revision=?',(ID,revision)).fetchone()
        if row is None:raise ValueError('constitution version missing')
        constitution=json.loads(row[0])
        if rules!=constitution['config']['policy']:raise ValueError('policy does not match constitution')
    account=scopes.resolve(store,db,body['account_id'])
    positions=account['positions'];observations=context(body['holding_context'],positions,db,account['currency'])
    report={'formula':FORMULA+('-portfolio-usd-v1' if account['id']==scopes.ALL else ''),'account_id':account['id'],'currency':account['currency'],'generated_at':business.now().isoformat(),'policy':rules,'holding_context':observations,'account_evidence':account,'score':None,'grade':None,'dimensions':{},'impacts':[],'position_count':len(positions),'scope':'current open positions; excludes cash from position weights','executes_trades':False}
    if constitution is not None:report['constitution_evidence']=constitution
    missing=[]
    if not positions:missing.append('没有当前持仓')
    if not account['valuation_complete']:missing.append('持仓价格或折算汇率缺失或过期' if account['id']==scopes.ALL else '持仓价格缺失或过期')
    if missing:return {**report,'status':'unavailable','missing':missing,'total_value':None}
    with localcontext() as ctx:
        ctx.prec=60
        total=sum((D(p['market_value']) for p in positions),D(0))
        if total<=0:return {**report,'status':'unavailable','missing':['持仓总市值非正'],'total_value':str(total)}
        warning=D(rules['warning_percent']);maximum=D(rules['max_percent']);shock=D(rules['shock_percent'])
        weights={p['symbol']:D(p['market_value'])/total*100 for p in positions}
        concentration=D(100);size_alerts=scopes.size_alerts(db,account);breaches=[];companies=[];complete=True
        for p in positions:
            sy=p['symbol'];weight=weights[sy];observation=observations.get(sy);reason=[]
            severity='critical' if weight>maximum else 'watch' if weight>warning else None
            if severity:concentration-=40 if severity=='critical' else 20;reason.append({'code':'position_weight','severity':severity,'current':str(weight),'limit':str(maximum if severity=='critical' else warning)})
            if weight<1:size_alerts.append(sy+' 持仓占比低于1%')
            fresh=observation is not None and (business.now().date()-date.fromisoformat(observation['as_of'])).days<=3
            if not fresh or observation['news']=='unavailable':complete=False;missing.append(sy+' 新闻观察缺失或过期')
            elif observation['news']=='negative' and weight>=warning:reason.append({'code':'negative_news_on_large_position','severity':'watch'})
            if observation:companies.append(observation['company'])
            else:complete=False;missing.append(sy+' 公司归属待补')
            pnl_pct=D(p['unrealized_pnl'])/D(p['open_cost'])*100 if D(p['open_cost'])>0 else None
            for rule in rules['custom_rules']:
                value=weight if rule['metric']=='position_percent' else pnl_pct
                if value is None:complete=False;missing.append(sy+' 自定义规则收益率依据不可用');continue
                threshold=D(rule['threshold']);matched={'gt':value>threshold,'gte':value>=threshold,'lt':value<threshold,'lte':value<=threshold}[rule['operator']]
                if matched:reason.append({'code':'custom_rule','severity':rule['severity'],'name':rule['name'],'current':str(value),'limit':str(threshold)})
            loss=-D(p['market_value'])*shock/100;projected_total=total+loss
            report['impacts'].append({'symbol':sy,'position_percent':str(weight),'scenario_move_percent':str(-shock),'scenario_pnl':str(loss),'projected_position_percent':str((D(p['market_value'])+loss)/projected_total*100) if projected_total>0 else None,'breaches':reason})
            breaches.extend(reason)
        count=len(positions);positive=sum(D(p['unrealized_pnl'])>0 for p in positions)
        diversity=D(20 if count<3 else 60 if count<=5 else 80 if count<=10 else 100)
        companies_complete=len(companies)==count
        if count>1 and companies_complete and len(set(companies))==1:diversity-=20
        discipline=D(100)-sum(16 if b['severity']=='critical' else 6 for b in breaches)
        clamp=lambda value:format(max(D(0),min(D(100),value)),'.2f')
        report['dimensions']={key:{'name':NAMES[key],'score':clamp(value) if available else None} for key,value,available in [('concentration',concentration,True),('profitability',D(positive)/count*100,True),('diversification',diversity,companies_complete),('position_size',D(100)-len(size_alerts)*15,True),('discipline',discipline,complete)]}
        report.update(total_value=str(total),unrealized_pnl=str(sum((D(p['unrealized_pnl']) for p in positions),D(0))),position_size_alerts=size_alerts,missing=list(dict.fromkeys(missing)),status='complete' if complete and companies_complete else 'partial')
        if report['status']=='complete':
            score=sum(D(report['dimensions'][key]['score'])*weight for key,weight in [('concentration',D('.25')),('profitability',D('.30')),('diversification',D('.15')),('position_size',D('.15')),('discipline',D('.15'))])
            report['score']=clamp(score);report['grade']=next(grade for threshold,grade in [(80,'A'),(65,'B'),(50,'C'),(35,'D'),(0,'F')] if D(report['score'])>=threshold)
        return report


def calculate(store,db,body):
    report=_calculate(store,db,body)
    return {**report,'intelligence':intelligence(report)}


def intelligence(report):
    """Original deterministic impact ranking; missing facts remain explicitly partial."""
    impacts=[]
    with localcontext() as ctx:
        ctx.prec=60
        for impact in report['impacts']:
            breaches=impact['breaches']
            score=min(35,round(D(impact['position_percent'])*D('.8')))
            score=min(100,max(0,score+sum(18 if b['severity']=='critical' else 8 if b['severity']=='watch' else 2 for b in breaches)))
            level=next(level for threshold,level in [(70,'critical'),(45,'high'),(20,'watch'),(0,'low')] if score>=threshold)
            actions=['review_position_size'] if any(b['code']=='position_weight' and b['severity']=='critical' for b in breaches) else ['maintain_and_monitor']
            if report['status']!='complete':actions.append('complete_evidence')
            fact={'formula':'selfuse-impact-v1','account_id':report['account_id'],'currency':report['currency'],
                  'policy':report['policy'],'holding_context':report['holding_context'].get(impact['symbol']),
                  'account_evidence':report['account_evidence'],'impact':impact,'data_status':report['status']}
            impacts.append({**impact,'risk_score':score,'risk_level':level,'review_actions':actions,
                            'fact_hash':business.digest(fact)})
        impacts.sort(key=lambda i:(-i['risk_score'],-D(i['position_percent']),i['symbol']))
    return {'formula':'selfuse-impact-v1','status':report['status'],'position_count':report['position_count'],
            'high_impact_count':sum(i['risk_level'] in {'high','critical'} for i in impacts) if impacts else None,
            'rule_breach_count':sum(len(i['breaches']) for i in impacts) if impacts else None,
            'top_impacts':impacts[:10],'coverage_count':len(impacts),'missing':report['missing']}


def evidence_token(store,db):
    return business.digest({'snapshot':business.snapshot_token(store,db),'day':business.now().date().isoformat(),'china_day':china_day(business.now()).isoformat()})


def preview(store,body):
    with store.connection() as db:
        db.execute('BEGIN');return {'report':calculate(store,db,body),'token':evidence_token(store,db)}


def save(store,body):
    business.fields(body,'id operation_id input expected_token');identifier(body['id'])
    with store.transaction() as db:
        fp,old=store._operation(db,body,'diagnosis_save')
        if old is not None:return old
        if db.execute('SELECT 1 FROM documents WHERE id=?',(body['id'],)).fetchone():raise Conflict('diagnosis immutable')
        if body['expected_token']!=evidence_token(store,db):raise Conflict('diagnostic evidence changed')
        report=calculate(store,db,body['input'])
        result=business._put(store,db,{'id':body['id'],'revision':0},{'kind':'diagnosis','title':'组合诊断','account_id':body['input']['account_id'],'report':report,'input':body['input']})
        return store._result(db,body,fp,result)


def history(store,account_id):
    scopes.scope_id(account_id)
    with store.connection() as db:
        db.execute('BEGIN')
        reports=sorted((r for r in business.records(db,'diagnosis') if r['account_id']==account_id),key=lambda r:(r['updated_at'],r['id']),reverse=True)
        comparison=None
        if len(reports)>1:
            current,previous=(r['report'] for r in reports[:2])
            with localcontext() as ctx:
                ctx.prec=60
                comparable=current['formula']==previous['formula'] and current['policy']==previous['policy']
                delta=lambda a,b:None if a is None or b is None else str(D(a)-D(b))
                comparison={'current_id':reports[0]['id'],'previous_id':reports[1]['id'],'policy_comparable':comparable,'score_delta':delta(current['score'],previous['score']) if comparable else None,'total_value_delta':delta(current['total_value'],previous['total_value']),'dimension_deltas':{key:delta(current['dimensions'].get(key,{}).get('score'),previous['dimensions'].get(key,{}).get('score')) if comparable else None for key in NAMES}}
        return {'reports':reports,'comparison':comparison,'account_id':account_id}
