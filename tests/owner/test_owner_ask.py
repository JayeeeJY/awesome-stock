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
        assert db.execute('PRAGMA user_version').fetchone()[0] == 8
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
        assert db.execute('PRAGMA user_version').fetchone()[0] == 8
    restart = application(port=4322, data_dir=data)
    restored = request(restart, '/api/v1/owner/ask-conversation', 'POST', {'id': conversation}, **login(restart))
    assert restored['status'] == 200
    assert [item['question'] for item in restored['body']['turns']] == ['升级前保存的问题', FOLLOWUP]
    backup = reopened.backup()
    assert backup['schema_version'] == 8
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
CANARY_OPENAI = 'sk-' + ('B' * 40) + '12345678'
CANARY_BEARER = ('C' * 48) + '1234567890'


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


# Shape rules still catch these without the key being configured.
SHAPE_CANARIES = {
    'sk-ant-VERA': 'sk-ant-VERA-CANARY-abcdefghijklmnop',
    'sk-proj-VERA': 'sk-proj-VERACANARYabcdefghijklmnop0123',
    'Bearer': 'Bearer xyzVERACANARY1234567890abcd',
    'bearer(lower)': 'bearer xyzVERACANARYlower1234567890',
    'sk_live_(underscore)': 'sk_live_VERACANARY1234567890abcd',
    'DeepSeek key(configured pre)': 'sk-ve7a0c1d2e3f4a5b6c7d8e9f0a1b2c3d',
}
# Hyphenated or short tails. Redacted only after that exact key was configured.
CONFIGURED_ONLY_CANARIES = {
    'sk-VERA': 'sk-VERA-CANARY-123456',
    'rk-VERA': 'rk-VERA-CANARY-1234567890',
    'pk-VERA': 'pk-VERA-CANARY-1234567890',
    'SK-(upper)': 'SK-VERA-CANARY-UPPER-123456',
    'sk-short(<16)': 'sk-VERA12345',
}
GATE_CANARIES = {
    **SHAPE_CANARIES,
    **CONFIGURED_ONLY_CANARIES,
    'AV bare(configured pre)': 'VERA7Z1D2D74NVWM',
    'EODHD bare(configured pre)': '65e1ve7a0b9c42.71828182',
}
UNCONFIGURED_SHAPES = {
    'AV bare(never configured)': 'QX9VERA2D74NVWMZ',
    'EODHD bare(never configured)': '15d3ve7a4de049.03453438',
    'GLM-style id.secret': '0f1e2d3c4b5a69788796a5b4c3d2e1f0.VeRaCaNaRy123456',
}
SAFE_TEXT = ('AAPL', '0700.HK', 'BRK.B', '600519.SS', 'US0378331005', '178.32', '2026-01-01', 'operation-1234567890', '1234567890123456')
SHORT_KEY = 'k9x2'


def configure_key(app, auth, body):
    result = request(app, '/api/v1/owner/connections', 'POST', body, **auth)
    assert result['status'] == 200, result['body']


def test_restart_redacts_every_provider_key_shape_and_keeps_ordinary_text(tmp_path):
    data = tmp_path.resolve() / 'gate-canary'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    auth = login(app)
    configure_key(app, auth, {'kind': 'ai', 'provider': 'deepseek', 'model': 'deepseek-flash', 'key': GATE_CANARIES['DeepSeek key(configured pre)'], 'enabled': True})
    for canary in CONFIGURED_ONLY_CANARIES.values():
        configure_key(app, auth, {'kind': 'ai', 'provider': 'deepseek', 'model': 'deepseek-flash', 'key': canary, 'enabled': True})
    configure_key(app, auth, {'kind': 'data', 'provider': 'alphavantage', 'model': '', 'key': GATE_CANARIES['AV bare(configured pre)'], 'enabled': True})
    configure_key(app, auth, {'kind': 'data_hk', 'provider': 'eodhd', 'model': '', 'key': GATE_CANARIES['EODHD bare(configured pre)'], 'enabled': True})
    restart = application(port=4322, data_dir=data)
    assert restart.connections.config == {}
    auth = login(restart)
    for name, canary in GATE_CANARIES.items():
        saved = save(restart, auth, turn(question=f'POST Q {canary} 市盈率?', answer=f'POST A {canary}', error=f'POST E {canary}', provider='deepseek', model='deepseek-flash'))
        assert saved['status'] == 200, (name, saved['body'])
        row = saved['body']['turns'][0]
        assert canary not in row['question'] and canary not in row['answer'] and canary not in row['error']
        assert canary not in saved['body']['title']
        if ' ' not in canary:
            poisoned = save(restart, auth, turn(question='model probe', answer='plain answer', provider='deepseek', model=canary))
            assert poisoned['status'] == 400, name
    for name, canary in UNCONFIGURED_SHAPES.items():
        saved = save(restart, auth, turn(question=f'POST Q {canary} 市盈率?', answer=f'POST A {canary}', error=f'POST E {canary}', provider='deepseek', model='deepseek-flash'))
        assert saved['status'] == 200, name
        row = saved['body']['turns'][0]
        assert row['question'] == f'POST Q {canary} 市盈率?' and row['answer'] == f'POST A {canary}' and row['error'] == f'POST E {canary}'
    ordinary = ' '.join(SAFE_TEXT) + ' ' + SHORT_KEY
    kept = save(restart, auth, turn(question=ordinary, answer=ordinary, error='still ' + ordinary, provider='deepseek', model='deepseek-flash'))
    assert kept['status'] == 200
    assert kept['body']['turns'][0]['question'] == ordinary
    blob = database_bytes(restart.store)
    for canary in GATE_CANARIES.values():
        assert canary.encode() not in blob, canary
    for token in (*SAFE_TEXT, SHORT_KEY, *UNCONFIGURED_SHAPES.values()):
        assert token.encode() in blob, token


FALSE_POSITIVES = (
    'risk-adjusted',
    'risk-management',
    'desk-research',
    'task-oriented',
    'SK-Hynix',
    'SK-Hynix-2025',
    'SK-Hynix-Q3-2025-earnings',
    'pk-2026-review',
    'rk-model-v2-final',
    'sk-2025-plan',
    'bearer instruments',
    'Bearer certificates',
    '1234567890123456',
    'trade 4829103756182934',
    'TRD4829103756182934',
    'report20261101.1234',
    'democracy',
    'sk-VERA12345',
)


def test_shape_rules_do_not_rewrite_ordinary_text(tmp_path):
    data = tmp_path.resolve() / 'ordinary'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    auth = login(app)
    configure_key(app, auth, {'kind': 'data', 'provider': 'alphavantage', 'model': '', 'key': 'demo', 'enabled': True})
    for phrase in FALSE_POSITIVES:
        saved = save(app, auth, turn(question=phrase, answer=phrase, error=phrase))
        assert saved['status'] == 200, phrase
        row = saved['body']['turns'][0]
        assert row['question'] == phrase and row['answer'] == phrase and row['error'] == phrase and saved['body']['title'] == phrase
        assert phrase.encode() in database_bytes(app.store)
    # In-process exact match of a short key stays on token boundaries.
    bordered = save(app, auth, turn(question='democracy uses demo today', answer='k9x2board', error=''))
    assert bordered['status'] == 200
    assert bordered['body']['turns'][0]['question'] == 'democracy uses [已隐藏凭据] today'
    assert bordered['body']['turns'][0]['answer'] == 'k9x2board'


def test_disabled_connection_and_short_keys_do_not_grow_the_digest_table(tmp_path):
    from awesome_stock.storage.owner_ask import SEEN_KEY_DIGEST_CAP, remember_key
    data = tmp_path.resolve() / 'cap'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    auth = login(app)
    disabled = request(app, '/api/v1/owner/connections', 'POST', {'kind': 'ai', 'provider': 'deepseek', 'model': 'deepseek-flash', 'key': 'sk-disabled-key-1234567890', 'enabled': False}, **auth)
    assert disabled['status'] == 200
    with app.store.connection() as db:
        assert db.execute('SELECT count(*) FROM ask_seen_key_digests').fetchone()[0] == 0
    configure_key(app, auth, {'kind': 'ai', 'provider': 'deepseek', 'model': 'deepseek-flash', 'key': 'k3Y', 'enabled': True})
    with app.store.connection() as db:
        assert db.execute('SELECT count(*) FROM ask_seen_key_digests').fetchone()[0] == 0
    first = 'sk-oldest-key-' + ('a' * 20)
    remember_key(app.store, first)
    for index in range(SEEN_KEY_DIGEST_CAP):
        remember_key(app.store, f'sk-cap-{index:02d}-' + ('b' * 20))
    with app.store.connection() as db:
        assert db.execute('SELECT count(*) FROM ask_seen_key_digests').fetchone()[0] == SEEN_KEY_DIGEST_CAP
    blob = database_bytes(app.store)
    assert first.encode() not in blob
    saved = save(app, auth, turn(question='still ' + first, answer='ok', error=''))
    assert saved['status'] == 200
    assert first in saved['body']['turns'][0]['question']


def test_reset_forgets_seen_key_digests(tmp_path):
    data = tmp_path.resolve() / 'reset-keys'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    auth = login(app)
    configure_key(app, auth, {'kind': 'data', 'provider': 'alphavantage', 'model': '', 'key': 'VERA7Z1D2D74NVWM', 'enabled': True})
    before = preview(app.store)
    assert before['counts']['ask_seen_key_digests'] == 1
    reset(app.store, {'token': before['token'], 'confirmation': '清空当前业务数据', 'current_password': PASSWORD}, app.store.owner().credential.digest_hex)
    with app.store.connection() as db:
        assert db.execute('SELECT count(*) FROM ask_seen_key_digests').fetchone()[0] == 0
        assert db.execute("SELECT 1 FROM metadata WHERE key='ask_key_hmac_secret'").fetchone() is None
    restart = application(port=4322, data_dir=data)
    saved = save(restart, login(restart), turn(question='after reset VERA7Z1D2D74NVWM', answer='kept', error=''))
    assert saved['body']['turns'][0]['question'] == 'after reset VERA7Z1D2D74NVWM'


GLUED_KEYS = {
    'av': 'VERA7Z1D2D74NVWM',
    'eod': '65e1ve7a0b9c42.71828182',
    'sk': 'sk-VERA-CANARY-123456',
    'rk': 'rk-VERA-CANARY-1234567890',
    'pk': 'pk-VERA-CANARY-1234567890',
}


def _assert_chinese_glue_redacted(target):
    auth = login(target)
    for key in GLUED_KEYS.values():
        question = f'我的密钥是{key}谢谢'
        answer = f'回答{key}完毕'
        error = f'报错{key}结束'
        saved = save(target, auth, turn(question=question, answer=answer, error=error, provider='deepseek', model='deepseek-flash'))
        assert saved['status'] == 200, saved['body']
        row = saved['body']['turns'][0]
        assert key not in row['question'] and key not in row['answer'] and key not in row['error']
        assert key not in saved['body']['title']
        assert '我的密钥是' in row['question'] and '谢谢' in row['question']
        assert '回答' in row['answer'] and '完毕' in row['answer']
        assert '报错' in row['error'] and '结束' in row['error']
    blob = database_bytes(target.store)
    for key in GLUED_KEYS.values():
        assert key.encode() not in blob


def test_configured_key_glued_to_chinese_is_redacted_before_and_after_restart(tmp_path):
    data = tmp_path.resolve() / 'chinese-glue'
    app = application(port=4322, data_dir=data)
    assert request(app, '/api/v1/owner/setup', 'POST', {'username': 'tester', 'password': PASSWORD})['status'] == 200
    auth = login(app)
    configure_key(app, auth, {'kind': 'ai', 'provider': 'deepseek', 'model': 'deepseek-flash', 'key': GLUED_KEYS['sk'], 'enabled': True})
    configure_key(app, auth, {'kind': 'ai', 'provider': 'deepseek', 'model': 'deepseek-flash', 'key': GLUED_KEYS['rk'], 'enabled': True})
    configure_key(app, auth, {'kind': 'ai', 'provider': 'deepseek', 'model': 'deepseek-flash', 'key': GLUED_KEYS['pk'], 'enabled': True})
    configure_key(app, auth, {'kind': 'data', 'provider': 'alphavantage', 'model': '', 'key': GLUED_KEYS['av'], 'enabled': True})
    configure_key(app, auth, {'kind': 'data_hk', 'provider': 'eodhd', 'model': '', 'key': GLUED_KEYS['eod'], 'enabled': True})
    _assert_chinese_glue_redacted(app)
    restart = application(port=4322, data_dir=data)
    assert restart.connections.config == {}
    _assert_chinese_glue_redacted(restart)


def test_duplicate_turn_conflict_uses_storage_guard(app):
    # The HTTP conflict above covers the route. This guards a direct storage mismatch too.
    from awesome_stock.storage.owner_ask import save_turn
    saved = save_turn(app.store, turn())
    with pytest.raises(Conflict):
        save_turn(app.store, turn(id=saved['turns'][0]['id'], answer='changed'))
