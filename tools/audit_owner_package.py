"""Offline source archive integrity and high-confidence secret-pattern checks.
Never prints matched values. This is not a complete secret or vulnerability scanner.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

RULES={
 'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
 'github_token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
 'aws_access_id':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 'openai_style_key':re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b'),
}

def inspect_bytes(name,data):
    return [{'path':name,'rule':rule,'line':data[:m.start()].count(b'\n')+1} for rule,pattern in RULES.items() for m in pattern.finditer(data)]

def inspect_ui_payload(contents):
    prefix='awesome-stock-owner/'
    base=prefix+'frontend/owner-ui/'
    try:
        manifest=json.loads(contents[base+'dist/UI_BUILD_MANIFEST.json'])
        if manifest.get('format')!='awesome-owner-ui-build-v1':raise ValueError('unsupported format')
        errors=[]
        for category,folder in [('sources',''),('assets','dist/')]:
            rows=manifest[category]
            declared={row['path']:row['sha256'] for row in rows}
            if len(declared)!=len(rows):errors.append('duplicate UI '+category)
            actual={name.removeprefix(base+folder) for name in contents if name.startswith(base+folder) and (category=='sources' and not name.startswith(base+'dist/') or category=='assets' and name!=base+'dist/UI_BUILD_MANIFEST.json')}
            if set(declared)!=actual:errors.append('UI '+category+' file set mismatch')
            for name,expected in declared.items():
                payload=contents.get(base+folder+name)
                if payload is None or hashlib.sha256(payload).hexdigest()!=expected:errors.append('UI '+category+' hash mismatch: '+name)
        index=contents[base+'dist/index.html']
        references={name.decode() for name in re.findall(rb'(?:src|href)="/(assets/[^"?#]+)',index)}
        if not references:errors.append('UI index has no asset references')
        for name in references:
            if base+'dist/'+name not in contents:errors.append('UI index references missing asset: '+name)
        return errors
    except (KeyError,TypeError,ValueError,UnicodeDecodeError) as exc:
        return ['invalid UI build payload: '+type(exc).__name__]

def audit(path):
    contents={};errors=[];findings=[];imports=set();total=0
    with tarfile.open(path,'r:gz') as archive:
        for member in archive:
            total+=member.size
            if len(contents)>=512 or total>16*1024*1024:raise ValueError("archive exceeds audit size limit")
            p=PurePosixPath(member.name)
            if not member.isfile() or member.size>4*1024*1024 or not member.name.startswith('awesome-stock-owner/') or '..' in p.parts or member.name in contents:
                raise ValueError('unsafe archive member')
            contents[member.name]=archive.extractfile(member).read()
    prefix='awesome-stock-owner/'
    manifest=json.loads(contents.pop(prefix+'PACKAGE_MANIFEST.json'))
    rows=manifest['files'];declared={prefix+r['path']:r['sha256'] for r in rows}
    if len(declared)!=len(rows) or set(declared)!=set(contents):errors.append('manifest file set mismatch')
    for name,data in contents.items():
        if hashlib.sha256(data).hexdigest()!=declared.get(name):errors.append('hash mismatch: '+name)
        if any(x in PurePosixPath(name).parts for x in ['.owner-state','.git','qa','backups','.env']) or name.endswith(('.sqlite3','.db','.pem','.key')):errors.append('excluded state file: '+name)
        findings.extend(inspect_bytes(name,data))
        if name.endswith('.py'):
            tree=ast.parse(data,filename=name)
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.update(a.name.split('.')[0] for a in node.names)
                elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module:imports.add(node.module.split('.')[0])
    errors.extend(inspect_ui_payload(contents))
    external=sorted(imports-set(sys.stdlib_module_names)-{'awesome_stock','audit_owner_package'})
    if external:errors.append('unclassified absolute imports')
    return {'archive_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'files_checked':len(contents),'integrity_errors':errors,'secret_pattern_findings':findings,'unclassified_python_imports':external,'passed':not errors and not findings,'scope':'archive only; no Git history, entropy analysis, vulnerability database or legal review; no matched values emitted'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);args=p.parse_args();r=audit(args.archive);print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['passed'] else 1)
