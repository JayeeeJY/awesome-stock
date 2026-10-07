"""Recent reauthentication, minimal export, and safe security events."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable

from .access import UserPrincipal, WorkspaceGrant
from .auth import UserRecord


class SensitiveOperationError(PermissionError):
    """Fail-closed sensitive-operation response without private details."""

    code = "reauthentication_required"

    def __init__(self) -> None:
        super().__init__("请重新验证身份后继续")


class SensitiveAction(str, Enum):
    CHANGE_PASSWORD = "change_password"
    EXPORT_DATA = "export_data"
    DELETE_ACCOUNT = "delete_account"


class SecurityEventCode(str, Enum):
    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_FAILED = "login_failed"
    SESSION_REVOKED = "session_revoked"
    ACCESS_DENIED = "access_denied"
    SENSITIVE_ACTION = "sensitive_action"


@dataclass(frozen=True)
class ReauthenticationGrant:
    """Short-lived proof created only after a fresh credential check."""

    user_id: str
    authenticated_at: datetime

    def __post_init__(self) -> None:
        user_id = self.user_id.strip() if isinstance(self.user_id, str) else ""
        if not user_id:
            raise ValueError("user_id is required")
        if self.authenticated_at.tzinfo is None or self.authenticated_at.utcoffset() is None:
            raise ValueError("authenticated_at must include a timezone")
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "authenticated_at", self.authenticated_at.astimezone(timezone.utc))


@dataclass(frozen=True)
class SensitiveAuthorization:
    user_id: str
    action: SensitiveAction


def authorize_sensitive_operation(
    principal: UserPrincipal | None,
    grant: ReauthenticationGrant | None,
    *,
    action: SensitiveAction | str,
    now: datetime,
    expected_confirmation: str | None = None,
    provided_confirmation: str | None = None,
    max_age: timedelta = timedelta(minutes=5),
) -> SensitiveAuthorization:
    """Require recent reauthentication and exact destructive confirmation."""

    if principal is None or grant is None or max_age <= timedelta(0):
        raise SensitiveOperationError()
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone")
    try:
        normalized_action = action if isinstance(action, SensitiveAction) else SensitiveAction(action)
    except ValueError as exc:
        raise SensitiveOperationError() from exc
    age = now.astimezone(timezone.utc) - grant.authenticated_at
    if principal.user_id != grant.user_id or age < timedelta(0) or age > max_age:
        raise SensitiveOperationError()
    if normalized_action is SensitiveAction.DELETE_ACCOUNT:
        if not expected_confirmation or provided_confirmation != expected_confirmation:
            raise SensitiveOperationError()
    return SensitiveAuthorization(principal.user_id, normalized_action)


@dataclass(frozen=True)
class ExportMembership:
    workspace_id: str
    role: str
    account_ids: tuple[str, ...]


@dataclass(frozen=True)
class IdentityExport:
    """Explicit allowlist export; credentials and sessions have no fields here."""

    user_id: str
    username: str
    status: str
    memberships: tuple[ExportMembership, ...]


def build_identity_export(
    user: UserRecord, grants: Iterable[WorkspaceGrant]
) -> IdentityExport:
    """Build the safe identity portion of a user export from allowlisted fields."""

    memberships = tuple(
        sorted(
            (
                ExportMembership(item.workspace_id, item.role.value, tuple(sorted(item.account_ids)))
                for item in grants
                if item.user_id == user.user_id
            ),
            key=lambda item: item.workspace_id,
        )
    )
    return IdentityExport(user.user_id, user.username, user.status.value, memberships)


@dataclass(frozen=True)
class SecurityEvent:
    """Allowlisted audit shape with no password, token, or arbitrary payload field."""

    request_id: str
    code: SecurityEventCode | str
    outcome: str
    user_id: str | None = None

    def __post_init__(self) -> None:
        request_id = self.request_id.strip() if isinstance(self.request_id, str) else ""
        if not request_id:
            raise ValueError("request_id is required")
        try:
            code = self.code if isinstance(self.code, SecurityEventCode) else SecurityEventCode(self.code)
        except ValueError as exc:
            raise ValueError("unsupported security event code") from exc
        if self.outcome not in {"allowed", "denied"}:
            raise ValueError("security event outcome must be allowed or denied")
        user_id = self.user_id.strip() if isinstance(self.user_id, str) else None
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "user_id", user_id or None)
