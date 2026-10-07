"""Cookie, CSRF, and credentialed CORS contracts."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hmac
from typing import Mapping
from urllib.parse import urlsplit

from awesome_stock.security.sessions import SessionTokens


ACCESS_COOKIE = "__Host-awesome_access"
REFRESH_COOKIE = "__Host-awesome_refresh"
CSRF_COOKIE = "__Host-awesome_csrf"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CsrfError(PermissionError):
    code = "csrf_rejected"

    def __init__(self) -> None:
        super().__init__("请求安全校验失败")


def _origin(value: object) -> str:
    normalized = value.strip().rstrip("/") if isinstance(value, str) else ""
    parsed = urlsplit(normalized)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    if (
        not normalized
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or not parsed.netloc
        or (parsed.scheme != "https" and not local_http)
    ):
        raise ValueError("origin must be HTTPS or an explicit loopback development origin")
    return normalized


@dataclass(frozen=True)
class CookieSpec:
    """Structured Set-Cookie data; adapters render framework-specific headers."""

    name: str
    value: str
    max_age: int
    secure: bool = True
    http_only: bool = True
    same_site: str = "Lax"
    path: str = "/"
    domain: None = None

    def __post_init__(self) -> None:
        if self.name not in {ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE}:
            raise ValueError("cookie name is not allowlisted")
        if not self.secure or self.path != "/" or self.domain is not None:
            raise ValueError("__Host- cookies require Secure, Path=/, and no Domain")
        if self.same_site not in {"Lax", "Strict"}:
            raise ValueError("session cookies cannot use SameSite=None")
        if not isinstance(self.max_age, int) or self.max_age < 0:
            raise ValueError("cookie max_age must be a non-negative integer")
        if self.name == CSRF_COOKIE and self.http_only:
            raise ValueError("double-submit CSRF cookie must be readable by the client")
        if self.name != CSRF_COOKIE and not self.http_only:
            raise ValueError("session token cookies must be HttpOnly")


def _seconds(until: datetime, now: datetime) -> int:
    if until.tzinfo is None or until.utcoffset() is None:
        raise ValueError("cookie expiry must be timezone-aware")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("current time must be timezone-aware")
    return max(0, int((until.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds()))


def session_cookies(
    tokens: SessionTokens, *, csrf_token: str, now: datetime
) -> tuple[CookieSpec, CookieSpec, CookieSpec]:
    """Issue host-only session cookies; raw token values are never put in JSON."""

    if not isinstance(csrf_token, str) or len(csrf_token) < 24:
        raise ValueError("csrf token must contain at least 24 characters")
    access_age = _seconds(tokens.access_expires_at, now)
    refresh_age = _seconds(tokens.refresh_expires_at, now)
    return (
        CookieSpec(ACCESS_COOKIE, tokens.access_token, access_age),
        CookieSpec(REFRESH_COOKIE, tokens.refresh_token, refresh_age),
        CookieSpec(CSRF_COOKIE, csrf_token, refresh_age, http_only=False),
    )


def clear_session_cookies() -> tuple[CookieSpec, CookieSpec, CookieSpec]:
    return (
        CookieSpec(ACCESS_COOKIE, "", 0),
        CookieSpec(REFRESH_COOKIE, "", 0),
        CookieSpec(CSRF_COOKIE, "", 0, http_only=False),
    )


def _header(headers: Mapping[str, str], name: str) -> str | None:
    lowered = name.casefold()
    return next((value for key, value in headers.items() if key.casefold() == lowered), None)


def validate_csrf(
    *,
    method: str,
    headers: Mapping[str, str],
    cookies: Mapping[str, str],
    allowed_origins: frozenset[str],
) -> None:
    """Require exact origin and double-submit token for every mutating request."""

    if method.upper() in SAFE_METHODS:
        return
    try:
        allowed = frozenset(_origin(item) for item in allowed_origins)
        request_origin = _origin(_header(headers, "Origin"))
    except ValueError as exc:
        raise CsrfError() from exc
    fetch_site = _header(headers, "Sec-Fetch-Site")
    if request_origin not in allowed or fetch_site == "cross-site":
        raise CsrfError()
    supplied = _header(headers, "X-CSRF-Token")
    stored = cookies.get(CSRF_COOKIE)
    if (
        not isinstance(supplied, str)
        or not isinstance(stored, str)
        or len(supplied) < 24
        or not hmac.compare_digest(supplied, stored)
    ):
        raise CsrfError()


def cors_headers(origin: str, *, allowed_origins: frozenset[str]) -> tuple[tuple[str, str], ...]:
    """Return credentialed CORS headers only for an exact allowlisted origin."""

    try:
        normalized = _origin(origin)
        allowed = frozenset(_origin(item) for item in allowed_origins)
    except ValueError:
        return ()
    if normalized not in allowed:
        return ()
    return (
        ("Access-Control-Allow-Origin", normalized),
        ("Access-Control-Allow-Credentials", "true"),
        ("Vary", "Origin"),
    )
