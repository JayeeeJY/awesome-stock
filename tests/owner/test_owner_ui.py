import hashlib
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
import pytest
from awesome_stock.runtime.owner import application
from awesome_stock.runtime.owner_ui import OwnerUI


def build(tmp_path):
    root=tmp_path.resolve()/'ui';(root/'assets').mkdir(parents=True)
    files={'index.html':b'<html><script src="/assets/app.js"></script></html>','assets/app.js':b'/* synthetic UI */'}
    for name,data in files.items():(root/name).write_bytes(data)
    (root/'UI_BUILD_MANIFEST.json').write_text(json.dumps({'format':'awesome-owner-ui-build-v1','assets':[{'path':n,'sha256':hashlib.sha256(d).hexdigest()} for n,d in files.items()]}))
    return root


def call(app,path,**extra):
    env={'REQUEST_METHOD':'GET','PATH_INFO':path,'HTTP_HOST':'127.0.0.1:4322','wsgi.input':BytesIO(),**extra};result={}
    def start(status,headers):result.update(status=int(status.split()[0]),headers=dict(headers))
    result['body']=b''.join(app(env,start));return result


def test_verified_assets_routes_security_headers_and_immutable_snapshot(tmp_path):
    root=build(tmp_path);a=application(port=4322,data_dir=tmp_path.resolve()/'data',ui_dist=root)
    response=call(a,'/settings/connections')
    assert response['status']==200 and b'<html>' in response['body']
    assert call(a,'/settings/appearance')['status']==200
    csp=response['headers']['Content-Security-Policy'];assert "script-src 'self'" in csp and "connect-src 'self'" in csp and 'unsafe-eval' not in csp
    (root/'assets/app.js').write_text('changed after startup')
    assert call(a,'/assets/app.js')['body']==b'/* synthetic UI */'
    for path in ['/../index.html','/UI_BUILD_MANIFEST.json','/assets/owner.js','/missing','/owner.sqlite3']:
        assert call(a,path)['status']==404
    assert call(a,'/plans',QUERY_STRING='id=synthetic')['headers']['Location']=='/plan/build-up?id=synthetic'
    assert call(a,'/login',HTTP_HOST='evil.example')['status']==403
    assert call(a,'/login',HTTP_ORIGIN='https://evil.example')['status']==403
    assert call(a,'/assets/app.js',HTTP_SEC_FETCH_SITE='cross-site')['status']==403


@pytest.mark.parametrize('change',['hash','extra','symlink','traversal','duplicate','missing'])
def test_unsafe_or_incomplete_build_fails_before_database_creation(tmp_path,change):
    root=build(tmp_path);manifest=root/'UI_BUILD_MANIFEST.json';data=json.loads(manifest.read_text())
    if change=='hash':(root/'index.html').write_text('modified')
    elif change=='extra':(root/'private.json').write_text('do not serve')
    elif change=='symlink':
        (root/'assets/app.js').unlink();(root/'assets/app.js').symlink_to(root/'index.html')
    elif change=='traversal':data['assets'][0]['path']='../index.html';manifest.write_text(json.dumps(data))
    elif change=='duplicate':data['assets'].append(data['assets'][0]);manifest.write_text(json.dumps(data))
    elif change=='missing':manifest.unlink()
    directory=tmp_path.resolve()/'data'
    with pytest.raises((ValueError,FileNotFoundError)):application(port=4322,data_dir=directory,ui_dist=root)
    assert not directory.exists()


def test_local_review_snapshot_retains_previous_route_chunk_without_changing_clean_dist(tmp_path):
    root=build(tmp_path)
    first=tmp_path/'first'
    script=Path(__file__).resolve().parents[2]/'tools/merge_preview_ui.py'
    subprocess.run([sys.executable,str(script),str(root),str(first)],check=True)
    old_chunk=first/'assets/old-route.js';old_chunk.write_bytes(b'/* previous route */')
    manifest=json.loads((first/'UI_BUILD_MANIFEST.json').read_text())
    manifest['assets'].append({'path':'assets/old-route.js','sha256':hashlib.sha256(old_chunk.read_bytes()).hexdigest()})
    (first/'UI_BUILD_MANIFEST.json').write_text(json.dumps(manifest))
    second=tmp_path/'second'
    subprocess.run([sys.executable,str(script),str(root),str(second),'--previous',str(first)],check=True)
    assert 'assets/old-route.js' in OwnerUI(second).assets
    app=application(port=4322,data_dir=tmp_path/'review-data',ui_dist=second)
    assert call(app,'/assets/old-route.js')['body']==b'/* previous route */'
    assert not (root/'assets/old-route.js').exists()
