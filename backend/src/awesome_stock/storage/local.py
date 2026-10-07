"""Single-workspace synthetic snapshots and versioned drafts. No live trading."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

APPLICATION_ID = 0x41535031
SCHEMA_VERSION = 1
WORKSPACE = 'community-demo'
KINDS = frozenset({'research_note', 'plan_draft', 'review_note'})

class Conflict(ValueError):
    pass


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _private_directory(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink data directories are unsupported')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_mode & 0o077:
        raise ValueError('data directory must be private (0700)')
    return path


def _check(db):
    if db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
        raise ValueError('unrecognized database')
    if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
        raise ValueError('unsupported schema version; database was not migrated')
    if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
        raise ValueError('database integrity check failed')
    if db.execute('SELECT value FROM metadata WHERE key=?', ('mode',)).fetchone() != ('synthetic_local',):
        raise ValueError('only synthetic local databases are supported')
    db.execute('SELECT id, workspace, kind, title, content, revision, updated_at FROM drafts LIMIT 0')
    if db.execute('SELECT count(*) FROM snapshots WHERE workspace=?', (WORKSPACE,)).fetchone()[0] != 1:
        raise ValueError('synthetic snapshot is missing')


class LocalStore:
    validate = staticmethod(_check)
    storage_mode = "synthetic_local"
    schema_version = SCHEMA_VERSION

    def __init__(self, directory, seed_rows):
        self.directory = _private_directory(directory)
        self.path = self.directory / 'community.sqlite3'
        if self.path.is_symlink():
            raise ValueError('symlink database is unsupported')
        if self.path.exists():
            if self.path.stat().st_mode & 0o077:
                raise ValueError('database must be private (0600)')
            with self.connection() as db:
                _check(db)
        else:
            # Initialize off-path, then atomically publish only a complete database.
            temporary = self.directory / ('.initializing-' + uuid.uuid4().hex)
            fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            try:
                with sqlite3.connect(temporary) as db:
                    db.execute('BEGIN IMMEDIATE')
                    db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                    db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                    db.execute('INSERT INTO metadata VALUES (?,?)', ('mode', 'synthetic_local'))
                    db.execute('CREATE TABLE snapshots (workspace TEXT PRIMARY KEY, payload TEXT NOT NULL)')
                    db.execute('INSERT INTO snapshots VALUES (?,?)', (WORKSPACE, _canonical(list(seed_rows))))
                    db.execute('CREATE TABLE drafts (id TEXT PRIMARY KEY, workspace TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL)')
                    db.execute('CREATE TABLE operations (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL)')
                os.link(temporary, self.path)  # refuses racing initialization/overwrite
            finally:
                temporary.unlink(missing_ok=True)

    @contextmanager
    def connection(self):
        # mode=rw avoids recreating a deleted/corrupt active database silently.
        db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5)
        try:
            db.execute('PRAGMA synchronous=FULL')
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def snapshot(self):
        with self.connection() as db:
            return tuple(json.loads(db.execute('SELECT payload FROM snapshots WHERE workspace=?', (WORKSPACE,)).fetchone()[0]))

    def list_drafts(self):
        with self.connection() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute('SELECT id,kind,title,content,revision,updated_at FROM drafts WHERE workspace=? ORDER BY updated_at DESC,id', (WORKSPACE,))]

    def mutate(self, payload, *, delete=False):
        if not isinstance(payload, dict) or set(payload) != ({'id', 'revision', 'operation_id'} if delete else {'id', 'revision', 'operation_id', 'kind', 'title', 'content'}):
            raise ValueError('invalid fields')
        for key in ('id', 'operation_id'):
            if not isinstance(payload[key], str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,64}', payload[key]):
                raise ValueError('invalid identifier')
        revision = payload['revision']
        if type(revision) is not int or not 0 <= revision <= 2**31-1 or (delete and revision == 0):
            raise ValueError('invalid revision')
        if not delete:
            if payload['kind'] not in KINDS:
                raise ValueError('invalid kind')
            for key, limit in [('title', 120), ('content', 20000)]:
                if not isinstance(payload[key], str) or not payload[key].strip() or len(payload[key]) > limit or '\x00' in payload[key]:
                    raise ValueError('invalid text')
        fingerprint = hashlib.sha256(_canonical({'delete':delete,'payload':payload}).encode()).hexdigest()
        with self.transaction() as db:
            previous = db.execute('SELECT fingerprint,result FROM operations WHERE id=?', (payload['operation_id'],)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise Conflict('operation ID already used')
                return json.loads(previous[1])
            current = db.execute('SELECT revision FROM drafts WHERE id=? AND workspace=?', (payload['id'], WORKSPACE)).fetchone()
            if (current[0] if current else 0) != revision:
                raise Conflict('draft changed; reload before saving')
            if delete:
                db.execute('DELETE FROM drafts WHERE id=? AND workspace=?', (payload['id'],WORKSPACE))
                result = {'id':payload['id'],'deleted':True}
            else:
                updated = datetime.now(timezone.utc).isoformat()
                db.execute('INSERT INTO drafts VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,title=excluded.title,content=excluded.content,revision=excluded.revision,updated_at=excluded.updated_at', (payload['id'],WORKSPACE,payload['kind'],payload['title'],payload['content'],revision+1,updated))
                result = {'id':payload['id'],'revision':revision+1,'updated_at':updated}
            db.execute('INSERT INTO operations VALUES (?,?,?)', (payload['operation_id'],fingerprint,_canonical(result)))
            return result

    def backup(self):
        root = _private_directory(self.directory / 'backups')
        name = 'backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        target = root / name
        target.mkdir(mode=0o700)
        path = target / self.path.name
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd)
        try:
            with self.connection() as src:
                dst = sqlite3.connect(path)
                try:
                    src.backup(dst)
                    self.validate(dst)
                finally:
                    dst.close()
            manifest = {'schema_version':self.schema_version,'mode':self.storage_mode,'file':self.path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            manifest_path = target / 'manifest.json'
            fd = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd,'w') as f:
                f.write(_canonical(manifest)+'\n');f.flush();os.fsync(f.fileno())
            return {'name':name,'sha256':manifest['sha256'],'schema_version':self.schema_version}
        except BaseException:
            path.unlink(missing_ok=True)
            (target/'manifest.json').unlink(missing_ok=True)
            target.rmdir()
            raise


def restore(backup_directory, destination, *, validator=_check, schema_version=SCHEMA_VERSION, mode="synthetic_local", filename="community.sqlite3"):
    """Restore to a new, absent directory. Never overwrite or hot-swap live data."""
    source = Path(backup_directory).absolute(); dest = Path(destination).absolute()
    if any(p.is_symlink() for p in (source, *source.parents)):
        raise ValueError('symlink backup directory is unsupported')
    if dest.exists() or dest.is_symlink():
        raise ValueError('restore destination must not exist')
    if any(p.is_symlink() for p in (dest.parent, *dest.parents)):
        raise ValueError('symlink restore parent is unsupported')
    dest.parent.mkdir(parents=True, exist_ok=True)
    db_path = source/filename; manifest_path = source/'manifest.json'
    if db_path.is_symlink() or manifest_path.is_symlink():
        raise ValueError('symlink backup files are unsupported')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema_version') != schema_version or manifest.get('mode') != mode or manifest.get('file') != filename:
        raise ValueError('unsupported backup manifest')
    # Check and copy the same bytes: source mutation cannot change the restored payload.
    data = db_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest.get('sha256'):
        raise ValueError('backup checksum mismatch')
    staging = dest.parent / ('.restore-' + uuid.uuid4().hex)
    staging.mkdir(mode=0o700)
    try:
        p = staging/filename
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
        try:validator(db)
        finally:db.close()
        # Exclusive destination creation prevents overwriting an unexpected directory.
        dest.mkdir(mode=0o700)
        try:os.link(p,dest/filename)
        except BaseException:
            dest.rmdir();raise
    finally:
        (staging/filename).unlink(missing_ok=True);staging.rmdir()
    return dest
