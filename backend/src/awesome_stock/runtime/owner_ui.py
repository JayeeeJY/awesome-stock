"""Verified immutable Vue build snapshot. Never resolves user-supplied filesystem paths."""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROUTES={'/','/login','/cockpit','/portfolio','/portfolio/accounts','/portfolio/trades','/portfolio/cash','/research','/research/notes','/research/batch','/research/screening','/decisions','/plan','/plan/allocation','/plan/pre-trade','/plan/budget','/plan/build-up','/review','/review/rules','/review/diagnosis','/academy','/settings','/settings/account','/settings/appearance','/settings/connections','/settings/transfer'}
REDIRECTS={'/ledger':'/portfolio/trades','/cash':'/portfolio/cash','/plans':'/plan/build-up','/planning':'/plan/allocation','/evolve':'/review','/trends':'/review/rules','/screening':'/research/screening'}
TYPES={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'}
CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"

def safe_file(path):
    if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents):raise ValueError('unsafe UI build path')
    return path.read_bytes()

class OwnerUI:
    def __init__(self,directory):
        root=Path(directory).absolute();manifest=json.loads(safe_file(root/'UI_BUILD_MANIFEST.json'))
        if manifest.get('format')!='awesome-owner-ui-build-v1':raise ValueError('invalid UI build manifest')
        entries=manifest.get('assets')
        if not isinstance(entries,list) or not 1<=len(entries)<=512:raise ValueError('invalid UI asset count')
        self.assets={};total=0
        for row in entries:
            name=row['path'];p=PurePosixPath(name)
            if not isinstance(name,str) or p.is_absolute() or '..' in p.parts or str(p)!=name or '\\' in name or p.suffix not in TYPES or name in self.assets:raise ValueError('invalid UI asset')
            data=safe_file(root/name);total+=len(data)
            if total>20*1024*1024 or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('UI build hash or size mismatch')
            self.assets[name]=(data,TYPES[p.suffix])
        if 'index.html' not in self.assets:raise ValueError('missing UI index')
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='UI_BUILD_MANIFEST.json'}
        if actual!=set(self.assets):raise ValueError('unlisted UI build file')
        if any(p.is_symlink() for p in root.rglob('*')):raise ValueError('symlink UI asset')

    def serve(self,path,query,start):
        if path in REDIRECTS:
            location=REDIRECTS[path]+('?' + query if query else '')
            # Query is retained only if safe for a response header.
            if '\r' in location or '\n' in location:raise ValueError('invalid redirect query')
            start('302 Found',[('Location',location),('Cache-Control','no-store'),('Content-Length','0')]);return [b'']
        key='index.html' if path in ROUTES else path[1:] if path.startswith('/') else ''
        if key not in self.assets:return None
        data,mime=self.assets[key]
        start('200 OK',[('Content-Type',mime),('Content-Length',str(len(data))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),('Content-Security-Policy',CSP)])
        return [data]
