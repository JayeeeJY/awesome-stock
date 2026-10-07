import json
import pytest
from dataclasses import asdict
from awesome_stock.academy import build_academy_library
from test_owner_api import app, request, login


@pytest.mark.parametrize('path',['academy','settings'])
def test_info_requires_owner_and_is_read_only(app,path):
    url='/api/v1/owner/'+path
    assert request(app,url)['status']==401
    auth=login(app)
    assert request(app,url,**auth)['status']==200
    assert request(app,url,'POST',{},**auth)['status']==404
    assert request(app,url,'DELETE',{},**auth)['status']==404
    assert request(app,url,**(auth|{'origin':'https://evil.example'}))['status']==403
    assert request(app,url,cookie=auth['cookie'].replace('awesome_owner_','awesome_'))['status']==401


def test_academy_preserves_reviewed_content_without_ledger_changes(app):
    before=app.store.path.read_bytes()
    result=request(app,'/api/v1/owner/academy',**login(app))['body']
    expected=json.loads(json.dumps([asdict(d) for d in build_academy_library().documents]))
    assert result['documents']==expected
    assert len(result['documents'])==8 and result['learning_progress_saved'] is False
    assert app.store.path.read_bytes()==before
    assert not (app.store.directory/'backups').exists()


def test_settings_actual_custom_directory_and_no_credentials(app):
    auth=login(app);before=app.store.path.read_bytes()
    result=request(app,'/api/v1/owner/settings',**auth)['body']
    assert set(result)=={'username','mode','schema_version','data_directory','database_file','backup_directory','backup_encrypted','restore_to_new_directory_only','external_connections'}
    assert result['username']=='tester' and result['schema_version']==5
    assert result['database_file']==str(app.store.path)
    assert result['backup_directory']==str(app.store.directory/'backups')
    assert result['backup_encrypted'] is result['external_connections'] is False
    assert app.store.owner().credential.digest_hex not in json.dumps(result)
    assert app.store.path.read_bytes()==before
    assert not (app.store.directory/'backups').exists()
    assert request(app,'/api/v1/owner/backup','POST',{},**auth)['status']==200
    assert (app.store.directory/'backups').is_dir()
    assert request(app,'/api/v1/owner/settings',**auth)['body']==result
    request(app,'/api/v1/auth/logout','POST',{},**auth)
    assert request(app,'/api/v1/owner/settings',**auth)['status']==401
