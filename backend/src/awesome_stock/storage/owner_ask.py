"""Persist Ask Awesome questions and answers in the owner database.

Page material, ledger holdings, and provider keys are not stored. Keys are
memory-only, so a restart cannot reload them. Each configured key is recorded
as HMAC-SHA256 under a per-install random secret, and Ask writes redact any
substring with a stored digest plus key-shaped tokens.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import re
import secrets
import uuid
from .local import Conflict
from .owner import identifier, text

FIELDS = {'id', 'conversation_id', 'question', 'answer', 'error', 'provider', 'model'}
PROVIDERS = {'openai', 'deepseek', 'ollama'}
MODEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}')
ASCII_RUN = re.compile(r'[!-~]+')
# Prefix shapes, including short sk- tokens and case variants. The tail is at
# least 8 characters so a bare "sk-" in prose is left alone.
PREFIX_KEY = re.compile(r'(?:sk|rk|pk)[-_](?:ant-|proj-|live-|test-|or-)?[A-Za-z0-9_\-]{8,}', re.I)
BEARER = re.compile(r'bearer\s+[A-Za-z0-9\-._~+/]{8,}={0,2}', re.I)
# Exactly 16 uppercase letters/digits. Callers require both a letter and a digit
# so tickers, ISINs, and long numbers do not match.
AV_KEY = re.compile(r'(?<![A-Z0-9])[A-Z0-9]{16}(?![A-Z0-9])')
# token.digits with a letter in the token, so prices such as 178.32 do not match.
# EODHD keys look like hex.digits; the letter requirement also rejects long numeric prices.
EODHD_KEY = re.compile(r'(?<![A-Za-z0-9])(?=[0-9A-Za-z]*[A-Za-z])[0-9A-Za-z]{8,}\.[0-9]{4,}(?![A-Za-z0-9])')
# 32 hex digits, a dot, then a secret that contains a letter (GLM-style).
GLM_KEY = re.compile(r'(?<![A-Za-z0-9])[0-9A-Fa-f]{32}\.(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{8,}(?![A-Za-z0-9])')
REDACTED = '[已隐藏凭据]'
HMAC_METADATA = 'ask_key_hmac_secret'


def _plain(value, limit):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError('invalid text')
    return value


def _known_secrets(secrets):
    return sorted((secret for secret in secrets if isinstance(secret, str) and secret), key=len, reverse=True)


def _shape_spans(value):
    spans = [match.span() for pattern in (PREFIX_KEY, BEARER, EODHD_KEY, GLM_KEY) for match in pattern.finditer(value)]
    for match in AV_KEY.finditer(value):
        token = match.group()
        if any(character.isalpha() for character in token) and any(character.isdigit() for character in token):
            spans.append(match.span())
    return spans


def _digest(secret, value):
    return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()


def _install_secret(store):
    with store.transaction() as db:
        row = db.execute('SELECT value FROM metadata WHERE key=?', (HMAC_METADATA,)).fetchone()
        if row:
            return bytes.fromhex(row[0])
        secret = secrets.token_bytes(32)
        db.execute('INSERT INTO metadata VALUES (?,?)', (HMAC_METADATA, secret.hex()))
        return secret


def _stored_digests(store):
    with store.connection() as db:
        db.execute('BEGIN')
        return [(row[0], row[1]) for row in db.execute('SELECT length,digest FROM ask_seen_key_digests')]


def remember_key(store, key):
    if not isinstance(key, str) or not key or len(key) > 512 or '\x00' in key:
        return
    secret = _install_secret(store)
    digest = _digest(secret, key)
    with store.transaction() as db:
        db.execute('INSERT INTO ask_seen_key_digests(length,digest) VALUES (?,?) ON CONFLICT DO NOTHING', (len(key), digest))


def _digest_spans(value, secret, digests):
    if not digests:
        return []
    by_length = {}
    for length, digest in digests:
        if isinstance(length, int) and length > 0:
            by_length.setdefault(length, set()).add(digest)
    spans = []
    for run in ASCII_RUN.finditer(value):
        token = run.group()
        origin = run.start()
        for length, hashes in by_length.items():
            if len(token) < length:
                continue
            for index in range(len(token) - length + 1):
                piece = token[index:index + length]
                if _digest(secret, piece) in hashes:
                    spans.append((origin + index, origin + index + length))
    return spans


def _apply(value, spans):
    if not spans:
        return value
    spans = sorted(spans)
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append([start, end])
    parts = []
    cursor = 0
    for start, end in merged:
        if start < cursor:
            continue
        parts.append(value[cursor:start])
        parts.append(REDACTED)
        cursor = end
    parts.append(value[cursor:])
    return ''.join(parts)


def _redact(value, secrets, store):
    for secret in _known_secrets(secrets):
        remember_key(store, secret)
    spans = []
    for secret in _known_secrets(secrets):
        start = 0
        while True:
            found = value.find(secret, start)
            if found < 0:
                break
            spans.append((found, found + len(secret)))
            start = found + len(secret)
    spans.extend(_shape_spans(value))
    spans.extend(_digest_spans(value, _install_secret(store), _stored_digests(store)))
    return _apply(value, spans)


def _contains_secret(value, secrets, store):
    return _redact(value, secrets, store) != value


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
    question = _redact(text(body['question'], 4000), secrets, store)
    answer = _redact(_plain(body['answer'], 30000), secrets, store)
    error = _redact(_plain(body['error'], 4000), secrets, store)
    if not answer.strip() and not error.strip():
        raise ValueError('incomplete turn')
    provider, model = body['provider'], body['model']
    if provider not in PROVIDERS or not isinstance(model, str) or not MODEL.fullmatch(model):
        raise ValueError('invalid provider')
    if _contains_secret(provider, secrets, store) or _contains_secret(model, secrets, store):
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
