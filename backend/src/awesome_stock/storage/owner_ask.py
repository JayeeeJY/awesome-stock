"""Persist Ask Awesome questions and answers in the owner database.

Page material, ledger holdings, and provider keys are not stored. Callers may
pass in-memory secrets so a repeated key is redacted before the row is written.
"""
from datetime import datetime, timezone
import re
import uuid
from .local import Conflict
from .owner import identifier, text

FIELDS = {'id', 'conversation_id', 'question', 'answer', 'error', 'provider', 'model'}
PROVIDERS = {'openai', 'deepseek', 'ollama'}
MODEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}')
# Key-shaped text is removed even when this process has no provider key loaded.
KEY_SHAPED = re.compile(r'(?:sk|rk|pk)-(?:ant-|proj-|live-|test-|or-)?[A-Za-z0-9_\-]{16,}')
BEARER = re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]{20,}={0,2}')
REDACTED = '[已隐藏凭据]'


def _plain(value, limit):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError('invalid text')
    return value


def _known_secrets(secrets):
    return sorted((secret for secret in secrets if isinstance(secret, str) and len(secret) >= 12), key=len, reverse=True)


def _contains_secret(value, secrets):
    return bool(KEY_SHAPED.search(value) or BEARER.search(value) or any(secret in value for secret in _known_secrets(secrets)))


def _redact(value, secrets):
    for secret in _known_secrets(secrets):
        value = value.replace(secret, REDACTED)
    value = KEY_SHAPED.sub(REDACTED, value)
    return BEARER.sub(REDACTED, value)


def _turns(db, conversation_id):
    rows = db.execute('SELECT id,position,question,answer,error,provider,model,created_at FROM ask_turns WHERE conversation_id=? ORDER BY position', (conversation_id,))
    return [{'id': row[0], 'position': row[1], 'question': row[2], 'answer': row[3], 'error': row[4], 'provider': row[5], 'model': row[6], 'created_at': row[7]} for row in rows]


def _conversation(db, conversation_id):
    row = db.execute('SELECT id,title,created_at,updated_at FROM ask_conversations WHERE id=?', (conversation_id,)).fetchone()
    if row is None:
        raise ValueError('unknown conversation')
    return {'id': row[0], 'title': row[1], 'created_at': row[2], 'updated_at': row[3], 'turns': _turns(db, conversation_id)}


def list_conversations(store):
    with store.connection() as db:
        db.execute('BEGIN')
        rows = db.execute('''SELECT c.id,c.title,c.created_at,c.updated_at,(SELECT count(*) FROM ask_turns t WHERE t.conversation_id=c.id)
            FROM ask_conversations c ORDER BY c.updated_at DESC,c.id''')
        return {'conversations': [{'id': row[0], 'title': row[1], 'created_at': row[2], 'updated_at': row[3], 'turn_count': row[4]} for row in rows]}


def read_conversation(store, body):
    if not isinstance(body, dict) or set(body) != {'id'}:
        raise ValueError('invalid fields')
    identifier(body['id'])
    with store.connection() as db:
        db.execute('BEGIN')
        return _conversation(db, body['id'])


def save_turn(store, body, secrets=()):
    if not isinstance(body, dict) or set(body) != FIELDS:
        raise ValueError('invalid fields')
    if not isinstance(secrets, tuple):
        raise ValueError('invalid fields')
    turn_id = identifier(body['id'])
    conversation_id = body['conversation_id']
    if conversation_id is not None:
        identifier(conversation_id)
    question = _redact(text(body['question'], 4000), secrets)
    answer = _redact(_plain(body['answer'], 30000), secrets)
    error = _redact(_plain(body['error'], 4000), secrets)
    if not answer.strip() and not error.strip():
        raise ValueError('incomplete turn')
    provider, model = body['provider'], body['model']
    if provider not in PROVIDERS or not isinstance(model, str) or not MODEL.fullmatch(model):
        raise ValueError('invalid provider')
    if _contains_secret(provider, secrets) or _contains_secret(model, secrets):
        raise ValueError('invalid provider')
    now = datetime.now(timezone.utc).isoformat()
    with store.transaction() as db:
        existing = db.execute('SELECT conversation_id,question,answer,error,provider,model FROM ask_turns WHERE id=?', (turn_id,)).fetchone()
        if existing:
            same_conversation = conversation_id is None or conversation_id == existing[0]
            if not same_conversation or existing[1:] != (question, answer, error, provider, model):
                raise Conflict('turn changed')
            return _conversation(db, existing[0])
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
            title = ' '.join(question.split())[:80]
            db.execute('INSERT INTO ask_conversations VALUES (?,?,?,?)', (conversation_id, title, now, now))
        elif db.execute('SELECT 1 FROM ask_conversations WHERE id=?', (conversation_id,)).fetchone() is None:
            raise ValueError('unknown conversation')
        count = db.execute('SELECT count(*) FROM ask_turns WHERE conversation_id=?', (conversation_id,)).fetchone()[0]
        if count >= 10:
            raise ValueError('conversation full')
        position = db.execute('SELECT COALESCE(MAX(position),0)+1 FROM ask_turns WHERE conversation_id=?', (conversation_id,)).fetchone()[0]
        db.execute('INSERT INTO ask_turns VALUES (?,?,?,?,?,?,?,?,?)', (turn_id, conversation_id, position, question, answer, error, provider, model, now))
        db.execute('UPDATE ask_conversations SET updated_at=? WHERE id=?', (now, conversation_id))
        return _conversation(db, conversation_id)
