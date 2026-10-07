"""Authentication, session, and authorization contracts for Awesome Stock."""

from .access import (
    AccessScope,
    AuthorizationError,
    MembershipRole,
    UserPrincipal,
    WorkspaceGrant,
    authorize_scope,
)
from .auth import (
    AuthenticationError,
    PasswordCredential,
    UserRecord,
    UserStatus,
    authenticate,
    make_password_credential,
)
from .redirects import safe_return_path
from .rate_limit import LoginAttemptLimiter, RateLimitError
from .operations import (
    ReauthenticationGrant,
    SecurityEvent,
    SensitiveAction,
    SensitiveOperationError,
    authorize_sensitive_operation,
    build_identity_export,
)
from .sessions import (
    InMemorySessionRepository,
    SessionError,
    SessionService,
    SessionTokens,
)

__all__ = [
    "AccessScope",
    "AuthenticationError",
    "AuthorizationError",
    "InMemorySessionRepository",
    "LoginAttemptLimiter",
    "MembershipRole",
    "PasswordCredential",
    "RateLimitError",
    "ReauthenticationGrant",
    "SecurityEvent",
    "SessionError",
    "SessionService",
    "SessionTokens",
    "SensitiveAction",
    "SensitiveOperationError",
    "UserPrincipal",
    "UserRecord",
    "UserStatus",
    "WorkspaceGrant",
    "authenticate",
    "authorize_scope",
    "authorize_sensitive_operation",
    "build_identity_export",
    "make_password_credential",
    "safe_return_path",
]
