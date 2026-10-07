"""Manual decision reviews with frozen evidence. No inferred investment quality."""
from datetime import date, datetime, timezone
import hashlib
import json
import re
from .local import Conflict, _canonical


def evidence(store, db, ref):
    if not isinstance(ref, dict) or set(ref)!={'id','revision'}:raise ValueError('invalid decision reference')
    decision=store._document_version(db,ref['id'],ref['revision'])
    if decision['kind']!='decision' or decision['archived']:raise ValueError('not a decision version')
    research=store._document_version(db,**decision['research_ref']) if decision['research_ref'] else None
    rows=db.execute('SELECT t.payload,t.revision,l.revision,a.name,a.currency FROM trade_links l JOIN trades t ON t.id=l.trade_id JOIN accounts a ON a.id=t.account_id WHERE l.decision_id=? AND l.decision_revision=? ORDER BY t.sequence',(ref['id'],ref['revision'])).fetchall()
    trades=[{**json.loads(p),'revision':rev,'link_revision':lr,'account_name':name,'currency':currency} for p,rev,lr,name,currency in rows]
    result={'decision':decision,'research':research,'trades':trades}
    return result,hashlib.sha256(_canonical(result).encode()).hexdigest()


def workspace(store):
    with store.connection() as db:
        db.execute('BEGIN')
        current=[json.loads(row[0]) for row in db.execute('SELECT payload FROM documents ORDER BY id')]
        versions=[json.loads(row[0]) for row in db.execute('SELECT payload FROM document_versions ORDER BY id,revision')]
        candidates=[]
        for d in versions:
            if d['kind']=='decision' and not d['archived']:
                snapshot,fingerprint=evidence(store,db,{'id':d['id'],'revision':d['revision']})
                candidates.append({'ref':{'id':d['id'],'revision':d['revision']},'snapshot':snapshot,'fingerprint':fingerprint,'decision_archived':next(x['archived'] for x in current if x['id']==d['id'])})
        reviews=[]
        for review in current:
            if review['kind']!='review':continue
            _,fingerprint=evidence(store,db,review['decision_ref'])
            reviews.append({**review,'evidence_changed':fingerprint!=review['evidence_fingerprint']})
        daily_journal=sorted((d for d in current if d['kind']=='daily_brief' and not d['archived']),key=lambda d:(d['captured_at'],d['id']),reverse=True)
        return {'coach_journal':sorted((d for d in current if d['kind']=='coach_journal'),key=lambda d:(d['updated_at'],d['id']),reverse=True),'daily_journal':daily_journal,'candidates':candidates,'reviews':reviews,'versions':[v for v in versions if v['kind']=='review'],'manual_only':True,'performance_score':None}


def save_review(store,body,*,archive=False):
    from .owner import identifier,text
    common={'id','revision','operation_id'}
    fields={'decision_ref','expected_evidence','reviewed_on','process_status','process_note','outcome_status','outcome_note','next_step'}
    if not isinstance(body,dict) or set(body)!=(common if archive else common|fields):raise ValueError('invalid review fields')
    identifier(body['id']);store._revision(body['revision'])
    if not archive:
        if body['process_status'] not in ('followed','deviated','unclear'):raise ValueError('invalid process status')
        if body['outcome_status'] not in ('pending','observed'):raise ValueError('invalid outcome status')
        reviewed_on=text(body['reviewed_on'],10)
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',reviewed_on):raise ValueError('invalid date')
        date.fromisoformat(reviewed_on)
        if not isinstance(body['expected_evidence'],str) or not re.fullmatch(r'[0-9a-f]{64}',body['expected_evidence']):raise ValueError('invalid evidence fingerprint')
        outcome=body['outcome_note']
        if not isinstance(outcome,str) or len(outcome)>20000 or '\x00' in outcome:raise ValueError('invalid outcome note')
        if body['outcome_status']=='observed':outcome=text(outcome,20000)
        payload={'reviewed_on':reviewed_on,'process_status':body['process_status'],'process_note':text(body['process_note'],20000),'outcome_status':body['outcome_status'],'outcome_note':outcome.strip(),'next_step':text(body['next_step'],10000)}
    with store.transaction() as db:
        fp,old=store._operation(db,body,'review_archive' if archive else 'review_save')
        if old is not None:return old
        row=db.execute('SELECT payload,revision FROM documents WHERE id=?',(body['id'],)).fetchone()
        current=json.loads(row[0]) if row else None
        if (row[1] if row else 0)!=body['revision'] or (archive and not row):raise Conflict('review changed')
        if current and (current['kind']!='review' or current['archived']):raise Conflict('review unavailable')
        if archive:result={**current,'archived':True}
        else:
            if current:
                if body['decision_ref']!=current['decision_ref'] or body['expected_evidence']!=current['evidence_fingerprint']:raise Conflict('review evidence cannot change')
                snapshot=current['evidence'];fingerprint=current['evidence_fingerprint']
            else:
                snapshot,fingerprint=evidence(store,db,body['decision_ref'])
                if fingerprint!=body['expected_evidence']:raise Conflict('evidence changed before saving')
            result={**payload,'id':body['id'],'kind':'review','title':snapshot['decision']['title'],'symbol':snapshot['decision']['symbol'],'decision_ref':body['decision_ref'],'evidence':snapshot,'evidence_fingerprint':fingerprint,'archived':False}
        result['revision']=body['revision']+1
        result['updated_at']=datetime.now(timezone.utc).isoformat()
        encoded=_canonical(result)
        db.execute('INSERT INTO documents VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(body['id'],encoded,result['revision']))
        db.execute('INSERT INTO document_versions VALUES (?,?,?)',(body['id'],result['revision'],encoded))
        store._audit(db,'review_archived' if archive else 'review_saved',body['id'],current,result)
        return store._result(db,body,fp,result)
