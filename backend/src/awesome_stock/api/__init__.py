"""Framework-neutral public API contracts for Awesome Stock."""

from .contracts import ApiProblem, ApiResponse, CapabilityError, problem_from_exception
from .cookies import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    CookieSpec,
    CsrfError,
    clear_session_cookies,
    cors_headers,
    session_cookies,
    validate_csrf,
)
from .legacy import (
    LegacyIssue,
    LegacyReadAdapter,
    LegacySnapshot,
    LegacySnapshotStatus,
)
from .service import CommunityApi

__all__ = [
    "ACCESS_COOKIE",
    "CSRF_COOKIE",
    "REFRESH_COOKIE",
    "ApiProblem",
    "ApiResponse",
    "CapabilityError",
    "CommunityApi",
    "CookieSpec",
    "CsrfError",
    "LegacyIssue",
    "LegacyReadAdapter",
    "LegacySnapshot",
    "LegacySnapshotStatus",
    "clear_session_cookies",
    "cors_headers",
    "problem_from_exception",
    "session_cookies",
    "validate_csrf",
]
