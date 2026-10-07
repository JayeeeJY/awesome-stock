"""The public review tree is isolated from private history and runtime state."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from prepare_owner_release import prepare


def test_review_tree_manifest_and_no_private_state(tmp_path):
    target=tmp_path/'review';result=prepare(target)
    data=json.loads((target/'RELEASE_TREE_MANIFEST.json').read_text())
    assert not data['public_release_approved'] and not data['git_initialized']
    assert result['files']==data['count']+1
    assert not (target/'.git').exists()
    assert data['installation']=='native-source-only'
    assert data['product_version']=='1.0.1'
    assert data['supported_platforms']==['macOS Apple Silicon (arm64)']
    assert not data['container_installation_included']
    assert not (target/'deploy').exists()
    assert not (target/'start_owner_container.py').exists()
    assert not (target/'backend/src/awesome_stock/runtime/owner_public_market.py').exists()
    assert not (target/'tools/audit_owner_image.py').exists()
    assert not (target/'tests/install/browser_owner_container.mjs').exists()
    assert (target/'LICENSE').read_bytes()==(ROOT/'LICENSE').read_bytes()
    assert (target/'LICENSING.md').is_file()
    assert data['project_license']=='AGPL-3.0-only'
    assert data['project_license_choice_approved']
    assert not data['license_approved'] and not data['third_party_rights_review_complete']
    assert not data['separate_commercial_license_offered']
    assert (target/'frontend/owner-shell.js').is_file()
    for row in data['files']:
        assert hashlib.sha256((target/row['path']).read_bytes()).hexdigest()==row['sha256']
        assert not any(part in {'.owner-state','.env','.git','private-rights','qa','__pycache__'} for part in Path(row['path']).parts)
    with pytest.raises(FileExistsError):prepare(target)
