"""Prepare a new review-only GitHub source tree; never creates Git history or publishes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from package_owner import ROOT,build,project_license_metadata,FIRST_RELEASE_SCOPE

EXTRA=['.gitignore','.gitattributes','CONTRIBUTING.md','package.json','package-lock.json','requirements-dev.txt',
       'tools/audit_owner_package.py','tools/prepare_owner_release.py','tools/merge_preview_ui.py',
       'tests/install/test_owner_package.py','tests/install/test_owner_archive_audit.py',
       'tests/install/test_owner_release_tree.py','tests/install/verify_owner_delivery.py',
       '.github/workflows/checks.yml',
       '.github/ISSUE_TEMPLATE/bug_report.yml','.github/ISSUE_TEMPLATE/feature_request.yml',
       '.github/ISSUE_TEMPLATE/config.yml']

def prepare(output,root=ROOT):
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise FileExistsError('review directory must not exist')
    if any(p.is_symlink() for p in output.parents):raise ValueError('symlink output parent')
    paths=EXTRA+[p.relative_to(root).as_posix() for p in (root/'tests/owner').glob('*') if p.suffix in ['.py','.mjs']]
    for name in paths:
        p=root/name
        if not p.is_file() or p.is_symlink() or any(x.is_symlink() for x in p.parents):raise ValueError('unsafe input: '+name)
    with tempfile.TemporaryDirectory(prefix='owner-release-') as temporary:
        archive=Path(temporary).resolve()/'source.tar.gz';build(archive,root)
        output.mkdir(parents=True)
        with tarfile.open(archive) as tar:
            for member in tar:
                name=member.name.removeprefix('awesome-stock-owner/')
                if name=='PACKAGE_MANIFEST.json':continue
                if not member.isfile() or '..' in Path(name).parts or Path(name).is_absolute():raise ValueError('unsafe generated archive')
                target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
    for name in paths:
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
    files=[{'path':p.relative_to(output).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(output.rglob('*')) if p.is_file()]
    manifest={**project_license_metadata(root),**FIRST_RELEASE_SCOPE,'format':'awesome-stock-owner-github-review-tree','files':files,'count':len(files),'contains_private_history':False,'contains_user_data':False,'git_initialized':False,'license_approved':False,'public_release_approved':False}
    (output/'RELEASE_TREE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return {'directory':str(output),'files':len(files)+1,'public_release_approved':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(json.dumps(prepare(args.output)))
