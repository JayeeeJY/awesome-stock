"""Opaque, revocable sessions over a replaceable atomic repository."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
from threading import Lock
from typing import Callable, Protocol


class SessionError(PermissionError):
    """A terminal session error; callers must not retry indefinitely."""

    def __init__(self, code: str = "invalid_session") -> None:
        self.code = code
        super().__init__("会话已失效，请重新登录")


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"


class RotationStatus(str, Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    EXPIRED = "expired"
    REUSED = "reused"


def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _digest(token: str) -> str:
    if not isinstance(token, str) or not token:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SessionTokens:
    """Opaque values returned once to the authenticated client."""

    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


@dataclass(frozen=True)
class SessionRecord:
    """Repository form: token digests only, never raw tokens."""

    session_id: str
    family_id: str
    user_id: str
    access_digest: str
    refresh_digest: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    status: SessionStatus = SessionStatus.ACTIVE


class SessionRepository(Protocol):
    """Atomic storage boundary replaceable by a persistent F3 adapter."""

    def put(self, record: SessionRecord) -> None: ...

    def find_by_access_digest(self, digest: str) -> SessionRecord | None: ...

    def rotate(
        self, refresh_digest: str, successor: SessionRecord, now: datetime
    ) -> RotationStatus: ...

    def revoke_family(self, family_id: str) -> None: ...

    def revoke_user(self, user_id: str) -> None: ...

    def snapshot(self) -> tuple[SessionRecord, ...]: ...


class InMemorySessionRepository:
    """Thread-safe synthetic adapter for contract tests, not production persistence."""

    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}
        self._lock = Lock()

    def put(self, record: SessionRecord) -> None:
        with self._lock:
            if record.session_id in self._records:
                raise ValueError("session id already exists")
            self._records[record.session_id] = record

    def find_by_access_digest(self, digest: str) -> SessionRecord | None:
        with self._lock:
            return next(
                (item for item in self._records.values() if item.access_digest == digest),
                None,
            )

    def rotate(
        self, refresh_digest: str, successor: SessionRecord, now: datetime
    ) -> RotationStatus:
        checked_at = _utc(now, "now")
        with self._lock:
            current = next(
                (item for item in self._records.values() if item.refresh_digest == refresh_digest),
                None,
            )
            if current is None:
                return RotationStatus.NOT_FOUND
            if current.status is not SessionStatus.ACTIVE:
                self._revoke_family_unlocked(current.family_id)
                return RotationStatus.REUSED
            if current.refresh_expires_at <= checked_at:
                self._records[current.session_id] = replace(current, status=SessionStatus.REVOKED)
                return RotationStatus.EXPIRED
            self._records[current.session_id] = replace(current, status=SessionStatus.ROTATED)
            self._records[successor.session_id] = successor
            return RotationStatus.SUCCESS

    def _revoke_family_unlocked(self, family_id: str) -> None:
        for session_id, record in tuple(self._records.items()):
            if record.family_id == family_id and record.status is not SessionStatus.REVOKED:
                self._records[session_id] = replace(record, status=SessionStatus.REVOKED)

    def revoke_family(self, family_id: str) -> None:
        with self._lock:
            self._revoke_family_unlocked(family_id)

    def revoke_user(self, user_id: str) -> None:
        with self._lock:
            for session_id, record in tuple(self._records.items()):
                if record.user_id == user_id and record.status is not SessionStatus.REVOKED:
                    self._records[session_id] = replace(record, status=SessionStatus.REVOKED)

    def snapshot(self) -> tuple[SessionRecord, ...]:
        with self._lock:
            return tuple(sorted(self._records.values(), key=lambda item: item.session_id))


class SessionService:
    """Session lifecycle with injected time, entropy, storage, and user status."""

    def __init__(
        self,
        repository: SessionRepository,
        *,
        clock: Callable[[], datetime],
        token_factory: Callable[[], str],
        is_user_active: Callable[[str], bool],
        access_lifetime: timedelta = timedelta(minutes=15),
        refresh_lifetime: timedelta = timedelta(days=14),
    ) -> None:
        if access_lifetime <= timedelta(0) or refresh_lifetime <= access_lifetime:
            raise ValueError("session lifetimes are invalid")
        self._repository = repository
        self._clock = clock
        self._token_factory = token_factory
        self._is_user_active = is_user_active
        self._access_lifetime = access_lifetime
        self._refresh_lifetime = refresh_lifetime

    def _new_value(self, field: str) -> str:
        value = self._token_factory()
        if not isinstance(value, str) or len(value) < 24:
            raise ValueError(f"token_factory returned an invalid {field}")
        return value

    def _issue(self, user_id: str, family_id: str | None = None) -> tuple[SessionTokens, SessionRecord]:
        now = _utc(self._clock(), "clock")
        session_id = self._new_value("session id")
        family = family_id or self._new_value("family id")
        access = self._new_value("access token")
        refresh = self._new_value("refresh token")
        tokens = SessionTokens(
            access,
            refresh,
            now + self._access_lifetime,
            now + self._refresh_lifetime,
        )
        record = SessionRecord(
            session_id,
            family,
            user_id,
            _digest(access),
            _digest(refresh),
            tokens.access_expires_at,
            tokens.refresh_expires_at,
        )
        return tokens, record

    def create(self, user_id: str) -> SessionTokens:
        if not isinstance(user_id, str) or not user_id.strip() or not self._is_user_active(user_id):
            raise SessionError()
        tokens, record = self._issue(user_id.strip())
        self._repository.put(record)
        return tokens

    def validate_access(self, access_token: str) -> str:
        now = _utc(self._clock(), "clock")
        record = self._repository.find_by_access_digest(_digest(access_token))
        active_user = record is not None and self._is_user_active(record.user_id)
        if (
            record is None
            or record.status is not SessionStatus.ACTIVE
            or record.access_expires_at <= now
            or not active_user
        ):
            if record is not None and not active_user:
                self._repository.revoke_family(record.family_id)
            raise SessionError()
        return record.user_id

    def refresh(self, refresh_token: str) -> SessionTokens:
        now = _utc(self._clock(), "clock")
        existing = next(
            (
                item
                for item in self._repository.snapshot()
                if item.refresh_digest == _digest(refresh_token)
            ),
            None,
        )
        if existing is None or not self._is_user_active(existing.user_id):
            if existing is not None:
                self._repository.revoke_family(existing.family_id)
            raise SessionError()
        tokens, successor = self._issue(existing.user_id, existing.family_id)
        status = self._repository.rotate(_digest(refresh_token), successor, now)
        if status is RotationStatus.SUCCESS:
            return tokens
        code = "refresh_reused_family_revoked" if status is RotationStatus.REUSED else "invalid_session"
        raise SessionError(code)

    def logout(self, access_token: str) -> None:
        record = self._repository.find_by_access_digest(_digest(access_token))
        if record is not None:
            self._repository.revoke_family(record.family_id)

    def revoke_user(self, user_id: str) -> None:
        self._repository.revoke_user(user_id)
