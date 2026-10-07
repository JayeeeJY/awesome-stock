"""Explicit logical data reset. Existing backups/exports are separate copies."""
import hashlib
import json
import re
import secrets
from pathlib import Path
from .local import Conflict, _canonical

TABLES=('trade_links','cash_flows','cash_flow_versions','ledger_events','trades','accounts','documents','document_versions','operations','audit')

def preview_db(db):
    counts={name:db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in TABLES}
    facts={name:list(db.execute('SELECT * FROM '+name+' ORDER BY rowid')) for name in TABLES}
    epoch=db.execute("SELECT value FROM metadata WHERE key='data_epoch'").fetchone()
    return {'counts':counts,'token':hashlib.sha256(_canonical({'tables':facts,'epoch':epoch}).encode()).hexdigest(),'retains_account':True,'deletes_backups':False,'physical_erasure_guaranteed':False}

def preview(store):
    with store.connection() as db:
        db.execute('BEGIN');return preview_db(db)

def reset(store,body,expected_digest):
    if not isinstance(body,dict) or set(body)!={'token','confirmation','current_password'} or body['confirmation']!='清空当前业务数据':raise ValueError('explicit confirmation required')
    with store.transaction() as db:
        if json.loads(db.execute('SELECT credential FROM owner').fetchone()[0])['digest_hex']!=expected_digest:raise Conflict('password changed')
        if preview_db(db)['token']!=body['token']:raise Conflict('reset preview stale')
        db.execute('PRAGMA secure_delete=ON')
        for name in TABLES:db.execute('DELETE FROM '+name)
        db.execute("INSERT INTO metadata VALUES ('data_epoch',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(secrets.token_hex(32),))
    # No automatic backup: that would silently retain another copy of data requested for deletion.
    return {'reset':True,'retains_account':True,'backups_retained':True,'reauthentication_required':True,'physical_erasure_guaranteed':False}

def backup_list(store):
    root=store.directory/'backups';rows=[]
    if root.is_symlink():raise ValueError('symlink backups')
    if root.exists():
        for p in sorted(root.iterdir()):
            if not re.fullmatch(r'backup-\d{8}T\d{6}Z-[a-f0-9]{8}',p.name) or p.is_symlink() or not p.is_dir():continue
            files=list(p.iterdir())
            if {x.name for x in files}!={'manifest.json','owner.sqlite3'} or any(x.is_symlink() or not x.is_file() for x in files):continue
            data=(p/'owner.sqlite3').read_bytes();manifest=(p/'manifest.json').read_bytes()
            rows.append({'name':p.name,'bytes':len(data),'token':hashlib.sha256(data+manifest).hexdigest()})
    return {'backups':rows,'external_copies_included':False}

def delete_backup(store,body):
    if not isinstance(body,dict) or set(body)!={'name','token','confirmation','current_password'} or body['confirmation']!='删除此备份':raise ValueError('explicit backup confirmation required')
    match=next((r for r in backup_list(store)['backups'] if r['name']==body['name']),None)
    if match is None or match['token']!=body['token']:raise Conflict('backup changed')
    p=store.directory/'backups'/match['name']
    # Only the two recognized files of this exact private backup; no recursive deletion.
    (p/'owner.sqlite3').unlink();(p/'manifest.json').unlink();p.rmdir()
    return {'deleted':True,'name':match['name'],'external_copies_deleted':False}
