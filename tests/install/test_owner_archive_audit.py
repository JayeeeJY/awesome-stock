import importlib.util
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from audit_owner_package import inspect_bytes,inspect_ui_payload,audit
from package_owner import build,content_mtime


def test_source_archive_integrity_and_import_boundary(tmp_path):
    out=tmp_path/'owner.tar.gz';build(out);result=audit(out)
    assert result['passed'] and result['files_checked']>0
    assert result['unclassified_python_imports']==[]


def test_secret_patterns_redact_values():
    token=b'ghp_'+b'A'*36;data=b'line one\n'+token
    result=inspect_bytes('synthetic.py',data)
    assert result==[{'path':'synthetic.py','rule':'github_token','line':2}]
    assert token.decode() not in str(result)


def test_manifest_tampering_fails(tmp_path):
    import tarfile,io
    original=tmp_path/'original.tar.gz';build(original);changed=tmp_path/'changed.tar.gz'
    with tarfile.open(original) as source,tarfile.open(changed,'w:gz') as target:
        for member in source:
            data=source.extractfile(member).read()
            if member.name.endswith('/start_owner.py'):data+=b'\n# unauthorized change\n'
            member.size=len(data);target.addfile(member,io.BytesIO(data))
    result=audit(changed)
    assert not result['passed'] and any('hash mismatch' in x for x in result['integrity_errors'])


def test_same_size_build_change_gets_new_archive_timestamp():
    assert content_mtime(b'build-A')!=content_mtime(b'build-B')


def test_ui_index_must_reference_packaged_assets(tmp_path):
    import tarfile
    out=tmp_path/'owner.tar.gz';build(out)
    with tarfile.open(out) as archive:
        contents={m.name:archive.extractfile(m).read() for m in archive}
    index='awesome-stock-owner/frontend/owner-ui/dist/index.html'
    contents[index]=contents[index].replace(b'/assets/index-',b'/assets/absent-',1)
    assert any('references missing asset' in error for error in inspect_ui_payload(contents))
