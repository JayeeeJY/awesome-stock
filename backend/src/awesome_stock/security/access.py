"""Fail-closed workspace and investment-account authorization."""

from dataclasses import dataclass
from enum import Enum


class AuthorizationError(PermissionError):
    """Authorization failure with no cross-tenant detail disclosure."""

    code = "access_denied"

    def __init__(self) -> None:
        super().__init__("无权访问该资源")


class MembershipRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"
    READ_ONLY = "read_only"


def _required(value: object, field: str) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


@dataclass(frozen=True)
class UserPrincipal:
    """Identity established by a validated server session."""

    user_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_id", _required(self.user_id, "user_id"))


@dataclass(frozen=True)
class WorkspaceGrant:
    """Server-owned membership and explicit account allowlist."""

    user_id: str
    workspace_id: str
    role: MembershipRole | str
    account_ids: frozenset[str]

    def __post_init__(self) -> None:
        try:
            role = self.role if isinstance(self.role, MembershipRole) else MembershipRole(self.role)
        except ValueError as exc:
            raise ValueError("unsupported membership role") from exc
        accounts = frozenset(_required(item, "account_id") for item in self.account_ids)
        object.__setattr__(self, "user_id", _required(self.user_id, "user_id"))
        object.__setattr__(self, "workspace_id", _required(self.workspace_id, "workspace_id"))
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "account_ids", accounts)


@dataclass(frozen=True)
class AccessScope:
    """Authorized scope passed to downstream services instead of client claims."""

    user_id: str
    workspace_id: str
    account_id: str | None
    role: MembershipRole


def authorize_scope(
    principal: UserPrincipal | None,
    grant: WorkspaceGrant | None,
    *,
    workspace_id: str,
    account_id: str | None = None,
    require_write: bool = False,
    require_owner: bool = False,
) -> AccessScope:
    """Authorize one explicit scope; missing and mismatched ownership always fail."""

    if principal is None or grant is None:
        raise AuthorizationError()
    requested_workspace = _required(workspace_id, "workspace_id")
    requested_account = None if account_id is None else _required(account_id, "account_id")
    if principal.user_id != grant.user_id or requested_workspace != grant.workspace_id:
        raise AuthorizationError()
    if requested_account is not None and requested_account not in grant.account_ids:
        raise AuthorizationError()
    if require_write and grant.role is MembershipRole.READ_ONLY:
        raise AuthorizationError()
    if require_owner and grant.role is not MembershipRole.OWNER:
        raise AuthorizationError()
    return AccessScope(principal.user_id, requested_workspace, requested_account, grant.role)
