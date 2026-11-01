"""Ask Awesome conversations persist in the owner database under --data-dir."""
import json
import sqlite3
import uuid
import pytest
from awesome_stock.storage.local import Conflict
from awesome_stock.storage.owner import OwnerStore, restore_owner
from awesome_stock.storage.owner_privacy import preview, reset
from awesome_stock.storage.owner_transfer import export_data
from test_owner_api import PASSWORD, application, login, request
from test_owner_store import account, trade

HOLDING = 'ZXQHOLD'
QUANTITY = '17.125'
SECRET = 'sk-synthetic-ask-secret-9f3a'
QUESTION = '什么是市盈率的局限？'
FOLLOWUP = '继续追问：上一答里的不确定项是什么？'
MATERIAL = '页面材料不应写入对话库 ' + HOLDING + ' ' + QUANTITY


def turn(**changes):
    body = {
        'id': str(uuid.uuid4()),
        'conversation_id': None,
        'question': QUESTION,
        'answer': '合成回答：市盈率只是一个比率，不是买入建议。',
        'error': '',
        'provider': 'ollama',
        'model': 'synthetic-model',
    }
    body.update(changes)
    return body


def save(app, auth, body):
    return request(app, '/api/v1/owner/ask-turns', 'POST', body, **auth)


def ask_rows(store):
    with store.connection() as db:
        conversations = db.execute('SELECT id,title,created_at,updated_at FROM ask_conversations ORDER BY id').fetchall()
        turns = db.execute('SELECT id,conversation_id,position,question,answer,error,provider,model,created_at FROM ask_turns ORDER BY conversation_id,position').fetchall()
    return conversations, turns


def test_multi_turn_conversation_restores_from_data_dir_after_restart(tmp_path):
    data = tmp_path.resolve() / 'Awesome-Stock-Data'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    auth = login(app)
    assert request(app, '/api/v1/owner/ask-conversations', **auth)['body'] == {'conversations': []}
    first = save(app, auth, turn(question='第一问：解释市盈率', answer='第一答'))
    assert first['status'] == 200, first['body']
    conversation = first['body']['id']
    second = save(app, auth, turn(conversation_id=conversation, question=FOLLOWUP, answer='第二答：上一答没有核实个股事实。'))
    assert second['status'] == 200
    assert [item['question'] for item in second['body']['turns']] == ['第一问：解释市盈率', FOLLOWUP]
    assert [item['answer'] for item in second['body']['turns']] == ['第一答', '第二答：上一答没有核实个股事实。']
    assert all('context' not in item and 'payload' not in item and 'material' not in item for item in second['body']['turns'])
    assert app.store.path == data / 'owner.sqlite3'
    assert app.store.path.is_file()
    assert list(data.glob('*.sqlite3')) == [app.store.path]

    restart = application(port=4322, data_dir=data)
    assert restart.store.path == data / 'owner.sqlite3'
    restored = request(restart, '/api/v1/owner/ask-conversation', 'POST', {'id': conversation}, **login(restart))
    assert restored['status'] == 200
    assert restored['body']['turns'] == second['body']['turns']
    listed = request(restart, '/api/v1/owner/ask-conversations', **login(restart))['body']['conversations']
    assert [item['id'] for item in listed] == [conversation]
    assert listed[0]['turn_count'] == 2
    other = save(restart, login(restart), turn(question='另一段对话'))
    assert other['status'] == 200 and other['body']['id'] != conversation
    chosen = request(restart, '/api/v1/owner/ask-conversation', 'POST', {'id': conversation}, **login(restart))['body']
    assert FOLLOWUP in [item['question'] for item in chosen['turns']]
    assert all(item['question'] != '另一段对话' for item in chosen['turns'])


def test_saved_ask_excludes_holdings_api_keys_material_and_logs(tmp_path, capsys):
    data = tmp_path.resolve() / 'private-ledger'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    app.store.add_account(account())
    app.store.trade(trade(symbol=HOLDING, quantity=QUANTITY, price='9.5'))
    auth = login(app)
    app.connections.configure({'kind': 'ai', 'provider': 'openai', 'model': 'gpt-test', 'key': SECRET, 'enabled': True})
    rejected = save(app, auth, turn(context=MATERIAL, key=SECRET))
    assert rejected['status'] == 400
    with app.store.connection() as db:
        assert db.execute('SELECT count(*) FROM ask_turns').fetchone()[0] == 0
    body = turn(question=QUESTION, answer='模型把凭据复读为 ' + SECRET, provider='openai', model='gpt-test')
    saved = save(app, auth, body)
    assert saved['status'] == 200
    assert SECRET not in saved['body']['turns'][0]['answer']
    assert '[已隐藏凭据]' in saved['body']['turns'][0]['answer']
    conversations, turns = ask_rows(app.store)
    dumped = json.dumps({'conversations': conversations, 'turns': turns}, ensure_ascii=False)
    assert HOLDING not in dumped and QUANTITY not in dumped and SECRET not in dumped and MATERIAL not in dumped
    assert SECRET.encode() not in app.store.path.read_bytes()
    exported = json.dumps(export_data(app.store), ensure_ascii=False)
    assert QUESTION not in exported and SECRET not in exported
    with app.store.connection() as db:
        audit = json.dumps(db.execute('SELECT action,before_value,after_value FROM audit').fetchall(), ensure_ascii=False)
    assert QUESTION not in audit and SECRET not in audit
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err
    assert HOLDING not in captured.out + captured.err
    assert QUANTITY not in captured.out + captured.err


def test_upgrade_and_reopen_keep_saved_conversations(tmp_path):
    data = tmp_path.resolve() / 'upgrade-ledger'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    app.store.add_account(account())
    before = app.store.ledger()
    with app.store.transaction() as db:
        db.execute('DROP TABLE ask_turns')
        db.execute('DROP TABLE ask_conversations')
        db.execute('PRAGMA user_version=5')
    upgraded = OwnerStore(data)
    assert upgraded.ledger() == before
    with upgraded.connection() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 6
        assert db.execute("SELECT 1 FROM sqlite_master WHERE name='ask_turns'").fetchone()
    auth = login(app)
    first = save(app, auth, turn(question='升级前保存的问题', answer='升级前保存的回答'))
    assert first['status'] == 200
    conversation = first['body']['id']
    second = save(app, auth, turn(conversation_id=conversation, question=FOLLOWUP, answer='升级前的追问回答'))
    assert second['status'] == 200
    with upgraded.transaction() as db:
        db.execute('PRAGMA user_version=5')
    reopened = OwnerStore(data)
    assert reopened.ledger() == before
    with reopened.connection() as db:
        assert db.execute('SELECT question FROM ask_turns ORDER BY position').fetchall() == [('升级前保存的问题',), (FOLLOWUP,)]
        assert db.execute('PRAGMA user_version').fetchone()[0] == 6
    restart = application(port=4322, data_dir=data)
    restored = request(restart, '/api/v1/owner/ask-conversation', 'POST', {'id': conversation}, **login(restart))
    assert restored['status'] == 200
    assert [item['question'] for item in restored['body']['turns']] == ['升级前保存的问题', FOLLOWUP]
    backup = reopened.backup()
    assert backup['schema_version'] == 6
    target = tmp_path.resolve() / 'restored-ledger'
    restore_owner(data / 'backups' / backup['name'], target)
    assert OwnerStore(target).ledger() == before
    with sqlite3.connect(target / 'owner.sqlite3') as db:
        assert db.execute('SELECT question FROM ask_turns ORDER BY position').fetchall() == [('升级前保存的问题',), (FOLLOWUP,)]


def test_reset_clears_ask_and_export_omits_it(tmp_path):
    data = tmp_path.resolve() / 'reset-ledger'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    saved = save(app, login(app), turn())
    assert saved['status'] == 200
    before = preview(app.store)
    assert before['counts']['ask_turns'] == 1 and before['counts']['ask_conversations'] == 1
    reset(app.store, {'token': before['token'], 'confirmation': '清空当前业务数据', 'current_password': PASSWORD}, app.store.owner().credential.digest_hex)
    after = preview(app.store)
    assert after['counts']['ask_turns'] == 0 and after['counts']['ask_conversations'] == 0
    assert app.store.owner() is not None
    with app.store.connection() as db:
        assert db.execute('SELECT count(*) FROM ask_turns').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM ask_conversations').fetchone()[0] == 0


def test_ask_requires_auth_and_rejects_invalid_turns(app):
    assert request(app, '/api/v1/owner/ask-conversations')['status'] == 401
    assert request(app, '/api/v1/owner/ask-turns', 'POST', turn())['status'] == 401
    auth = login(app)
    assert save(app, auth, turn(answer='', error=''))['status'] == 400
    kept = save(app, auth, turn())
    assert kept['status'] == 200
    replay = save(app, auth, {**turn(id=kept['body']['turns'][0]['id'], conversation_id=kept['body']['id']), 'question': QUESTION, 'answer': kept['body']['turns'][0]['answer']})
    assert replay['status'] == 200 and len(replay['body']['turns']) == 1
    clash = save(app, auth, turn(id=kept['body']['turns'][0]['id'], conversation_id=kept['body']['id'], answer='不同回答'))
    assert clash['status'] == 409
    current = kept['body']['id']
    for index in range(9):
        assert save(app, auth, turn(conversation_id=current, question=f'追问{index}', answer=f'回答{index}'))['status'] == 200
    overflow = save(app, auth, turn(conversation_id=current, question='第11次', answer='不应保存'))
    assert overflow['status'] == 400
    listed = request(app, '/api/v1/owner/ask-conversation', 'POST', {'id': current}, **auth)['body']['turns']
    assert len(listed) == 10 and all(item['question'] != '第11次' for item in listed)


@pytest.fixture
def app(tmp_path):
    created = application(port=4322, data_dir=tmp_path.resolve() / 'owner')
    assert request(created, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    return created


CANARY_ANTHROPIC = 'sk-ant-api03-' + ('A' * 48)
CANARY_OPENAI = 'sk-' + ('B' * 48)
CANARY_BEARER = 'C' * 64


def database_bytes(store):
    blob = store.path.read_bytes()
    for suffix in ('-wal', '-shm', '-journal'):
        extra = store.path.parent / (store.path.name + suffix)
        if extra.is_file():
            blob += extra.read_bytes()
    return blob


def test_restart_without_loaded_key_does_not_store_pasted_key(tmp_path):
    data = tmp_path.resolve() / 'canary-ledger'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    login(app)
    app.connections.configure({'kind': 'ai', 'provider': 'openai', 'model': 'gpt-test', 'key': 'sk-configured-' + ('D' * 40), 'enabled': True})
    restart = application(port=4322, data_dir=data)
    assert restart.connections.config == {}
    question = CANARY_ANTHROPIC + ' 请解释市盈率'
    answer = '模型复读 ' + CANARY_OPENAI
    error = '失败 Bearer ' + CANARY_BEARER
    saved = save(restart, login(restart), turn(question=question, answer=answer, error=error, provider='openai', model='gpt-test'))
    assert saved['status'] == 200, saved['body']
    row = saved['body']['turns'][0]
    assert '请解释市盈率' in row['question'] and CANARY_ANTHROPIC not in row['question']
    assert CANARY_OPENAI not in row['answer'] and CANARY_BEARER not in row['error']
    assert CANARY_ANTHROPIC not in saved['body']['title']
    blob = database_bytes(restart.store)
    for canary in (CANARY_ANTHROPIC, CANARY_OPENAI, CANARY_BEARER):
        assert canary.encode() not in blob
    poisoned = save(restart, login(restart), turn(question='普通问题', answer='普通回答', provider='openai', model=CANARY_OPENAI))
    assert poisoned['status'] == 400
    assert CANARY_OPENAI.encode() not in database_bytes(restart.store)


def test_cleared_connection_redacts_previously_configured_key(tmp_path):
    key = 'plain-provider-key-77'
    data = tmp_path.resolve() / 'rotated-key'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    auth = login(app)
    app.connections.configure({'kind': 'ai', 'provider': 'openai', 'model': 'gpt-test', 'key': key, 'enabled': True})
    app.connections.clear()
    assert app.connections.config == {}
    saved = save(app, auth, turn(question='请忽略 ' + key, answer='没有密钥'))
    assert saved['status'] == 200
    assert key not in saved['body']['turns'][0]['question'] and key not in saved['body']['title']
    assert '请忽略' in saved['body']['turns'][0]['question']
    assert key.encode() not in database_bytes(app.store)


def test_failed_turn_is_saved_without_material(app):
    saved = save(app, login(app), turn(question='失败的问题', answer='', error='服务没有返回完整答案。'))
    assert saved['status'] == 200
    row = saved['body']['turns'][0]
    assert row['answer'] == '' and row['error'] == '服务没有返回完整答案。'
    assert 'context' not in row and 'payload' not in row and 'material' not in row


def test_duplicate_turn_conflict_uses_storage_guard(app):
    # The HTTP conflict above covers the route. This guards a direct storage mismatch too.
    from awesome_stock.storage.owner_ask import save_turn
    saved = save_turn(app.store, turn())
    with pytest.raises(Conflict):
        save_turn(app.store, turn(id=saved['turns'][0]['id'], answer='changed'))
