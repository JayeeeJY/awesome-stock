"""Build a deterministic local Owner source archive, excluding all runtime state."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]
STATIC=['LICENSE','LICENSING.md','CHANGELOG.md','README.md','README.en.md','CONTRIBUTING.md','docs/PRODUCT_SCOPE.md','docs/QUICKSTART.md','docs/OPTIONAL_PROVIDERS.md','docs/DATA_AND_PRIVACY.md','docs/TROUBLESHOOTING.md','docs/VALIDATION.md','docs/RELEASE_SECURITY_REVIEW.md','docs/DEVELOPMENT.md','docs/screenshots/settings.png','docs/screenshots/portfolio.png','docs/screenshots/research.png','docs/screenshots/notes.png','docs/screenshots/plan.png','docs/screenshots/evolve-review.png','docs/screenshots/academy.png','docs/screenshots/ask-awesome.png','docs/screenshots/portfolio-mobile.png','docs/screenshots/login.png','docs/screenshots/cockpit.png','tools/audit_owner_package.py','start_owner.py','OWNER_INSTALL.md','SECURITY.md','OWNER_SUPPLY_CHAIN.json','docs/OWNER_UI_DEPENDENCIES.json','docs/OWNER_UI_UPSTREAM_NOTICES.json','docs/OWNER_UI_NOTICE_DISCLOSURES.txt','docs/OWNER_UI_SBOM.cdx.json','docs/OWNER_UI_THIRD_PARTY_LICENSES.txt','tools/inventory_owner_ui.py','docs/THIRD_PARTY_NOTICES_CANDIDATE.md','tools/package_owner.py']

UI_CONFIG={'package.json','package-lock.json','vite.config.ts','tsconfig.json','index.html','write-build-manifest.mjs'}

FIRST_RELEASE_SCOPE = {'product_version': '1.0.1', 'installation': 'native-source-only', 'supported_platforms': ['macOS Apple Silicon (arm64)'], 'container_installation_included': False, 'prebuilt_container_image_distributed': False}

PROJECT_LICENSE = 'AGPL-3.0-only'
OFFICIAL_LICENSE_SHA256 = '0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0'


def project_license_metadata(root):
    # Owner selection approved on 2026-10-06. This is not third-party clearance.
    license_path = root / 'LICENSE'
    if license_path.is_symlink() or any(p.is_symlink() for p in license_path.parents):
        raise ValueError('unsafe project license')
    if hashlib.sha256(license_path.read_bytes()).hexdigest() != OFFICIAL_LICENSE_SHA256:
        raise ValueError('project LICENSE differs from approved official text')
    return {'project_license': PROJECT_LICENSE,
            'project_copyright': 'Copyright (c) 2026 Evan',
            'project_license_choice_approved': True,
            'third_party_rights_review_complete': False,
            'separate_commercial_license_offered': False}


def content_mtime(data):
    # Docker's local-context cache can retain old bytes when a rebuilt archive
    # extracts files with the same size and the same fixed timestamp.
    return int.from_bytes(hashlib.sha256(data).digest()[:4],'big') & 0x7fffffff

def ui_files(root):
    ui=root/'frontend/owner-ui';dist=ui/'dist';manifest_path=dist/'UI_BUILD_MANIFEST.json'
    if manifest_path.is_symlink() or any(p.is_symlink() for p in manifest_path.parents):raise ValueError('unsafe UI manifest')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('format')!='awesome-owner-ui-build-v1':raise ValueError('unsupported UI manifest')
    result=['frontend/owner-ui/dist/UI_BUILD_MANIFEST.json']
    for category,base in [('sources',ui),('assets',dist)]:
        rows=manifest.get(category)
        if not isinstance(rows,list) or not rows or len(rows)>512:raise ValueError('invalid UI inventory')
        declared=set()
        for row in rows:
            name=row['path'];parts=Path(name).parts
            if not isinstance(name,str) or Path(name).is_absolute() or '..' in parts or Path(name).as_posix()!=name or '\\' in name or name in declared:raise ValueError('unsafe UI member')
            if category=='sources':
                if name not in UI_CONFIG and not (parts[0] in {'src','public'} and Path(name).suffix in {'.vue','.ts','.scss','.css','.svg','.json'}):raise ValueError('unexpected UI source')
            elif Path(name).suffix not in {'.html','.js','.css','.svg'}:raise ValueError('unexpected UI asset')
            p=base/name
            if p.is_symlink() or any(x.is_symlink() for x in p.parents) or not p.is_file():raise ValueError('unsafe UI file')
            if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('stale UI build; rebuild before packaging')
            declared.add(name);result.append(p.relative_to(root).as_posix())
        actual=({p.relative_to(ui).as_posix() for folder in ['src','public'] for p in (ui/folder).rglob('*') if p.is_file()}|UI_CONFIG) if category=='sources' else {p.relative_to(dist).as_posix() for p in dist.rglob('*') if p.is_file() and p.name!='UI_BUILD_MANIFEST.json'}
        if actual!=declared:raise ValueError('UI file inventory changed; rebuild before packaging')
        if category=='assets' and 'index.html' not in declared:raise ValueError('missing UI index')
    return result

def build(output,root=ROOT):
    licensing=project_license_metadata(root)
    dependency_inventory=json.loads((root/'docs/OWNER_UI_DEPENDENCIES.json').read_text())
    if dependency_inventory.get('lock_sha256')!=hashlib.sha256((root/'frontend/owner-ui/package-lock.json').read_bytes()).hexdigest():raise ValueError('stale dependency inventory; regenerate before packaging')
    for component in dependency_inventory['components']:
        disclosure=component.get('notice_disclosure')
        if disclosure and (disclosure['file']!='docs/OWNER_UI_NOTICE_DISCLOSURES.txt' or disclosure['sha256']!=hashlib.sha256((root/disclosure['file']).read_bytes()).hexdigest()):raise ValueError('stale notice disclosure; regenerate inventory before packaging')
    files=sorted(set(ui_files(root)+STATIC+[p.relative_to(root).as_posix() for p in (root/'backend/src').rglob('*.py')]+[p.relative_to(root).as_posix() for p in (root/'frontend').glob('owner*.js')]+['frontend/owner.html','frontend/owner.css']))
    payloads={}
    for name in files:
        path=root/name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():raise ValueError('unsafe package input')
        payloads[name]=path.read_bytes()
    manifest={**licensing,**FIRST_RELEASE_SCOPE,'format':'awesome-stock-owner-source','runtime':'Python >=3.10 standard library + prebuilt Vue browser assets','ui_source_and_build_included':True,'ui_build_requires':'Node >=22.12 with locked npm dependencies','files':[{'path':name,'sha256':hashlib.sha256(data).hexdigest()} for name,data in payloads.items()],'includes_user_data':False,'public_release_approved':False}
    payloads['PACKAGE_MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for name,data in sorted(payloads.items()):
            info=tarfile.TarInfo('awesome-stock-owner/'+name);info.size=len(data);info.mode=0o644;info.mtime=content_mtime(data);tar.addfile(info,io.BytesIO(data))
    buffer=io.BytesIO()
    with gzip.GzipFile(fileobj=buffer,mode='wb',filename='',mtime=0) as archive:archive.write(raw.getvalue())
    data=buffer.getvalue();output=Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.absolute().parents):raise ValueError("unsafe package output")
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        if output.read_bytes()!=data:raise FileExistsError('different output already exists; choose a new filename')
    else:
        with output.open('xb') as f:f.write(data)
    return {'file':str(output),'sha256':hashlib.sha256(data).hexdigest(),'files':len(payloads)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args();print(json.dumps(build(args.output)))
