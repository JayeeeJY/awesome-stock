"""Source delivery is deterministic and excludes runtime state."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('owner_package',ROOT/'tools/package_owner.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


def test_reproducible_archive_and_manifest(tmp_path):
    first=tmp_path/'first.tar.gz';second=tmp_path/'second.tar.gz'
    assert package.build(first)['sha256']==package.build(second)['sha256']
    assert first.read_bytes()==second.read_bytes()
    assert package.build(first)['sha256']==package.build(second)['sha256']
    with tarfile.open(first) as tar:
        names=tar.getnames();manifest=json.load(tar.extractfile('awesome-stock-owner/PACKAGE_MANIFEST.json'))
        assert not manifest['includes_user_data'] and not manifest['public_release_approved']
        assert manifest['project_license']=='AGPL-3.0-only'
        assert manifest['project_license_choice_approved']
        assert not manifest['third_party_rights_review_complete']
        assert tar.extractfile('awesome-stock-owner/LICENSE').read()==(ROOT/'LICENSE').read_bytes()
        assert 'awesome-stock-owner/LICENSING.md' in names
        assert 'awesome-stock-owner/docs/OWNER_UI_NOTICE_DISCLOSURES.txt' in names
        assert all(not any(bad in n for bad in ['.owner-state','.env','qa/','.sqlite','.git/']) for n in names)
        assert 'awesome-stock-owner/start_owner.py' in names
        assert manifest['installation']=='native-source-only'
        assert manifest['product_version']=='1.0.0'
        assert manifest['supported_platforms']==['macOS Apple Silicon (arm64)']
        assert not manifest['container_installation_included']
        assert not any('/deploy/' in n or n.endswith('/start_owner_container.py') or n.endswith('/audit_owner_image.py') for n in names)
        import hashlib
        for row in manifest['files']:
            assert hashlib.sha256(tar.extractfile('awesome-stock-owner/'+row['path']).read()).hexdigest()==row['sha256']


def test_existing_output_is_never_overwritten(tmp_path):
    target=tmp_path/'already';target.write_bytes(b'keep')
    with pytest.raises(FileExistsError):package.build(target)
    assert target.read_bytes()==b'keep'


def test_symlink_output_is_rejected(tmp_path):
    target=tmp_path/'original';target.write_bytes(b'keep');link=tmp_path/'link';link.symlink_to(target)
    with pytest.raises(ValueError):package.build(link)
    assert target.read_bytes()==b'keep'


def test_altered_license_is_rejected_before_packaging(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'LICENSE').write_bytes((ROOT/'LICENSE').read_bytes()+b'\nAltered terms\n')
    with pytest.raises(ValueError,match='LICENSE differs'):
        package.build(tmp_path/'unsafe.tar.gz',root)
    assert not (tmp_path/'unsafe.tar.gz').exists()


def test_unknown_and_state_files_are_excluded(tmp_path):
    import shutil
    root=tmp_path/'source';root.mkdir()
    for name in package.STATIC+['frontend/owner.html','frontend/owner.css']:
        dst=root/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
    shutil.copytree(ROOT/'frontend/owner-ui',root/'frontend/owner-ui',ignore=shutil.ignore_patterns('node_modules'))
    for name in ['.env','.owner-state/owner.sqlite3','frontend/private-key.txt','backend/src/private.db','qa/screen.png','start_owner_container.py','deploy/owner-compose.yaml','deploy/owner.Dockerfile']:
        dst=root/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text('NEVER-PACKAGE-THIS-CANARY')
    out=tmp_path/'out.tar.gz';package.build(out,root)
    with tarfile.open(out) as tar:
        assert all(b'NEVER-PACKAGE-THIS-CANARY' not in tar.extractfile(m).read() for m in tar.getmembers())
    (root/'start_owner.py').unlink();(root/'start_owner.py').symlink_to(ROOT/'start_owner.py')
    with pytest.raises(ValueError):package.build(tmp_path/'unsafe.tar.gz',root)


def test_ui_sources_and_compiled_assets_are_included(tmp_path):
    archive=tmp_path/'ui.tar.gz';package.build(archive)
    with tarfile.open(archive) as tar:
        names=set(tar.getnames());prefix='awesome-stock-owner/frontend/owner-ui/'
        assert prefix+'src/main.ts' in names and prefix+'package-lock.json' in names
        assert prefix+'dist/index.html' in names and prefix+'dist/UI_BUILD_MANIFEST.json' in names
        assert not any('/node_modules/' in name for name in names)


def test_ui_stale_sources_or_added_files_are_rejected(tmp_path):
    import shutil
    root=tmp_path/'tree';shutil.copytree(ROOT/'frontend/owner-ui',root/'frontend/owner-ui',ignore=shutil.ignore_patterns('node_modules'))
    assert package.ui_files(root)
    source=root/'frontend/owner-ui/src/main.ts';source.write_text(source.read_text()+'\n// changed')
    with pytest.raises(ValueError,match='stale UI build'):package.ui_files(root)
    shutil.copyfile(ROOT/'frontend/owner-ui/src/main.ts',source)
    (root/'frontend/owner-ui/src/unbuilt.ts').write_text('// not built')
    with pytest.raises(ValueError,match='inventory changed'):package.ui_files(root)


def test_stale_disclosure_blocks_archive(tmp_path):
    import shutil
    root=tmp_path/'source'
    for name in ['LICENSE','docs/OWNER_UI_DEPENDENCIES.json','docs/OWNER_UI_NOTICE_DISCLOSURES.txt','frontend/owner-ui/package-lock.json']:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    with (root/'docs/OWNER_UI_NOTICE_DISCLOSURES.txt').open('a') as f:f.write('Changed disclosure\n')
    with pytest.raises(ValueError,match='stale notice disclosure'):
        package.build(tmp_path/'unsafe.tar.gz',root)
    assert not (tmp_path/'unsafe.tar.gz').exists()
