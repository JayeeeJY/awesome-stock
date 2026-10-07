"""Privacy-conscious login attempt throttling with injected time."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from threading import Lock
from typing import Callable


class RateLimitError(PermissionError):
    """Generic retry response shared by known and unknown identities."""

    code = "too_many_attempts"

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__("尝试次数过多，请稍后重试")


@dataclass(frozen=True)
class _AttemptState:
    failures: tuple[datetime, ...]
    blocked_until: datetime | None = None


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _privacy_key(identifier: object, key_secret: bytes) -> str:
    normalized = identifier.strip().casefold() if isinstance(identifier, str) else ""
    if not normalized:
        normalized = "<missing>"
    return hmac.new(key_secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


class LoginAttemptLimiter:
    """Replaceable in-memory limiter that never stores a raw login identifier."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime],
        key_secret: bytes,
        max_failures: int = 5,
        window: timedelta = timedelta(minutes=15),
        lockout: timedelta = timedelta(minutes=15),
    ) -> None:
        if isinstance(max_failures, bool) or max_failures < 1:
            raise ValueError("max_failures must be positive")
        if window <= timedelta(0) or lockout <= timedelta(0):
            raise ValueError("rate limit durations must be positive")
        if not isinstance(key_secret, bytes) or len(key_secret) < 32:
            raise ValueError("key_secret must contain at least 32 bytes")
        self._clock = clock
        self._key_secret = key_secret
        self._max_failures = max_failures
        self._window = window
        self._lockout = lockout
        self._states: dict[str, _AttemptState] = {}
        self._lock = Lock()

    def _retry_after(self, blocked_until: datetime, now: datetime) -> int:
        remaining = (blocked_until - now).total_seconds()
        return max(1, int(remaining + 0.999))

    def check(self, identifier: object) -> None:
        now = _utc(self._clock())
        key = _privacy_key(identifier, self._key_secret)
        with self._lock:
            state = self._states.get(key)
            if state and state.blocked_until and state.blocked_until > now:
                raise RateLimitError(self._retry_after(state.blocked_until, now))

    def record_failure(self, identifier: object) -> None:
        now = _utc(self._clock())
        key = _privacy_key(identifier, self._key_secret)
        with self._lock:
            state = self._states.get(key, _AttemptState(()))
            if state.blocked_until and state.blocked_until > now:
                raise RateLimitError(self._retry_after(state.blocked_until, now))
            threshold = now - self._window
            failures = tuple(item for item in state.failures if item > threshold) + (now,)
            blocked_until = now + self._lockout if len(failures) >= self._max_failures else None
            self._states[key] = _AttemptState(failures, blocked_until)
            if blocked_until is not None:
                raise RateLimitError(self._retry_after(blocked_until, now))

    def record_success(self, identifier: object) -> None:
        with self._lock:
            self._states.pop(_privacy_key(identifier, self._key_secret), None)

    def stored_keys(self) -> tuple[str, ...]:
        """Expose only digests for contract inspection, never raw identifiers."""

        with self._lock:
            return tuple(sorted(self._states))
