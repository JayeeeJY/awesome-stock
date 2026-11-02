"""Persist Ask Awesome questions and answers in the owner database.

Page material, ledger holdings, and provider keys are not stored. Keys are
memory-only, so a restart cannot reload the raw value. A key that was enabled
and is at least MIN_REMEMBERED_KEY characters is recorded as HMAC-SHA256 under
a per-install random secret. Ask writes redact that exact key, including when
Chinese text is glued to either side, plus a narrow set of key-shaped tokens.
The public demo value is not a secret. A short key is recorded only when it
was already in the live config from before the length rule.
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
# Left boundary so "risk-adjusted" is not read as a key. The explicit
# ant-/proj-/live-/test-/or- forms stay. A plain tail is one contiguous
# [A-Za-z0-9_] run of at least 20 characters with both a letter and a digit,
# and it must end at a right boundary so "SK-Hynix-2025" is left alone.
PREFIX_KEY = re.compile(
    r'(?<![A-Za-z0-9])(?:sk|rk|pk)[-_](?:(?:ant-|proj-|live-|test-|or-)[A-Za-z0-9_\-]{8,}|(?=[A-Za-z0-9_]*[A-Za-z])(?=[A-Za-z0-9_]*[0-9])[A-Za-z0-9_]{20,}(?![A-Za-z0-9_\-]))',
    re.I)
# "bearer instruments" has no digit. A real bearer token is long and contains one.
BEARER = re.compile(r'(?<![A-Za-z0-9])bearer\s+(?=[A-Za-z0-9\-._~+/]*[0-9])[A-Za-z0-9\-._~+/]{16,}={0,2}', re.I)
REDACTED = '[已隐藏凭据]'
HMAC_METADATA = 'ask_key_hmac_secret'
SEEN_KEY_DIGEST_CAP = 32
MIN_REMEMBERED_KEY = 12
# Public demonstration value. Exact, case-sensitive match. Not a secret.
PUBLIC_DEMO_KEY = 'demo'


def _plain(value, limit):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError('invalid text')
    return value


def _known_secrets(secrets):
    return sorted((secret for secret in secrets if isinstance(secret, str) and secret and secret != PUBLIC_DEMO_KEY), key=len, reverse=True)


def _shape_spans(value):
    return [match.span() for pattern in (PREFIX_KEY, BEARER) for match in pattern.finditer(value)]


def _ascii_alnum(character):
    # str.isalnum() treats Han characters as alphanumeric, so a key glued to
    # Chinese would look like the middle of a larger token and be kept.
    return '0' <= character <= '9' or 'A' <= character <= 'Z' or 'a' <= character <= 'z'


def _bounded(value, secret):
    spans = []
    start = 0
    size = len(secret)
    while True:
        found = value.find(secret, start)
        if found < 0:
            break
        before = found == 0 or not _ascii_alnum(value[found - 1])
        end = found + size
        after = end == len(value) or not _ascii_alnum(value[end])
        if before and after:
            spans.append((found, end))
        start = found + 1
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


def _store_digest(store, key):
    secret = _install_secret(store)
    digest = _digest(secret, key)
    with store.transaction() as db:
        seq = db.execute('SELECT COALESCE(MAX(seen_seq),0)+1 FROM ask_seen_key_digests').fetchone()[0]
        db.execute('INSERT INTO ask_seen_key_digests(digest,length,seen_seq) VALUES (?,?,?) ON CONFLICT(digest) DO UPDATE SET seen_seq=excluded.seen_seq,length=excluded.length', (digest, len(key), seq))
        db.execute('DELETE FROM ask_seen_key_digests WHERE digest NOT IN (SELECT digest FROM ask_seen_key_digests ORDER BY seen_seq DESC LIMIT ?)', (SEEN_KEY_DIGEST_CAP,))


def remember_key(store, key):
    # Newly entered keys shorter than the minimum are rejected at configure
    # time and are not recorded here. Recording them would keep matching
    # ordinary short tokens after restart.
    if not isinstance(key, str) or len(key) < MIN_REMEMBERED_KEY or len(key) > 512 or '\x00' in key or key == PUBLIC_DEMO_KEY:
        return
    _store_digest(store, key)


def remember_legacy_short_key(store, key):
    # A short key that v1.1.0 already held in the live config. The raw value
    # stays in memory only; the digest lets a later restart strip it.
    if not isinstance(key, str) or key == PUBLIC_DEMO_KEY or '\x00' in key or not 1 <= len(key) < MIN_REMEMBERED_KEY:
        return
    _store_digest(store, key)


def is_legacy_short_key(store, key):
    if not isinstance(key, str) or key == PUBLIC_DEMO_KEY or '\x00' in key or not 1 <= len(key) < MIN_REMEMBERED_KEY:
        return False
    with store.connection() as db:
        db.execute('BEGIN')
        row = db.execute('SELECT value FROM metadata WHERE key=?', (HMAC_METADATA,)).fetchone()
        if row is None:
            return False
        digest = _digest(bytes.fromhex(row[0]), key)
        return db.execute('SELECT 1 FROM ask_seen_key_digests WHERE digest=? AND length=?', (digest, len(key))).fetchone() is not None


def adopt_configured_keys(store, connections):
    """Fold keys still sitting in the live config into the in-memory matcher.

    v1.1.0 never wrote API keys to the data directory. After a real restart the
    config is empty and there is nothing to adopt. When this process still has
    the old config, a short key is hashed so the next restart can strip it.
    """
    config = getattr(connections, 'config', {}) or {}
    seen = getattr(connections, 'seen_secrets', None)
    for kind in ('ai', 'data', 'data_hk'):
        current = config.get(kind) or {}
        key = current.get('key') if isinstance(current, dict) else ''
        if not isinstance(key, str) or not key or key == PUBLIC_DEMO_KEY:
            continue
        if isinstance(seen, set):
            seen.add(key)
        if len(key) < MIN_REMEMBERED_KEY:
            remember_legacy_short_key(store, key)
        else:
            remember_key(store, key)


def _digest_spans(value, secret, digests):
    by_length = {}
    for length, digest in digests:
        if isinstance(length, int) and 1 <= length <= 512:
            by_length.setdefault(length, set()).add(digest)
    if not by_length:
        return []
    spans = []
    size = len(value)
    for index in range(size):
        if index and _ascii_alnum(value[index - 1]):
            continue
        for length, hashes in by_length.items():
            end = index + length
            if end > size or (end < size and _ascii_alnum(value[end])):
                continue
            if _digest(secret, value[index:end]) in hashes:
                spans.append((index, end))
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
    known = _known_secrets(secrets)
    for secret in known:
        if len(secret) < MIN_REMEMBERED_KEY:
            remember_legacy_short_key(store, secret)
        else:
            remember_key(store, secret)
    spans = []
    for secret in known:
        spans.extend(_bounded(value, secret))
    spans.extend(_shape_spans(value))
    digests = _stored_digests(store)
    if digests:
        spans.extend(_digest_spans(value, _install_secret(store), digests))
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
