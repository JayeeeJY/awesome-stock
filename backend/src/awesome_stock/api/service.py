"""Framework-neutral API facade over the fact and security contracts."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Mapping

from awesome_stock.core.imports import ImportScope, TradeRecord
from awesome_stock.security.access import UserPrincipal, WorkspaceGrant, authorize_scope
from awesome_stock.security.auth import UserRecord, authenticate
from awesome_stock.security.sessions import SessionService

from .contracts import ApiResponse, CapabilityError, problem_from_exception
from .cookies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    clear_session_cookies,
    session_cookies,
    validate_csrf,
)
from .legacy import LegacyReadAdapter, LegacySnapshotStatus


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return value


def _record(record: TradeRecord) -> dict[str, object]:
    return {
        "workspace_id": record.workspace_id,
        "account_id": record.account_id,
        "symbol": record.symbol,
        "currency": record.currency,
        "source": record.source,
        "external_id": record.external_id,
        "executed_at": _json_value(record.executed_at),
        "sequence": record.sequence,
        "side": _json_value(record.trade.side),
        "quantity": _json_value(record.trade.quantity),
        "price": _json_value(record.trade.price),
        "fee": _json_value(record.trade.fee),
        "read_only": True,
    }


class CommunityApi:
    """Explicit application boundary; web-framework adapters may call these methods."""

    def __init__(
        self,
        *,
        sessions: SessionService,
        user_lookup: Callable[[str], UserRecord | None],
        legacy: LegacyReadAdapter,
        clock: Callable[[], datetime],
        csrf_factory: Callable[[], str],
        allowed_origins: frozenset[str],
    ) -> None:
        self._sessions = sessions
        self._user_lookup = user_lookup
        self._legacy = legacy
        self._clock = clock
        self._csrf_factory = csrf_factory
        self._allowed_origins = allowed_origins

    def login(self, *, username: str, password: str, request_id: object = None) -> ApiResponse:
        try:
            user = self._user_lookup(username.strip().casefold())
            user_id = authenticate(user, password)
            tokens = self._sessions.create(user_id)
            cookies = session_cookies(
                tokens,
                csrf_token=self._csrf_factory(),
                now=self._clock(),
            )
            return ApiResponse(200, data={"authenticated": True, "user_id": user_id}, cookies=cookies)
        except Exception as error:
            return ApiResponse.failure(problem_from_exception(error, request_id=request_id))

    def refresh(
        self,
        *,
        method: str,
        headers: Mapping[str, str],
        cookies: Mapping[str, str],
        request_id: object = None,
    ) -> ApiResponse:
        try:
            validate_csrf(
                method=method,
                headers=headers,
                cookies=cookies,
                allowed_origins=self._allowed_origins,
            )
            tokens = self._sessions.refresh(cookies.get(REFRESH_COOKIE, ""))
            issued = session_cookies(
                tokens,
                csrf_token=self._csrf_factory(),
                now=self._clock(),
            )
            return ApiResponse(200, data={"authenticated": True}, cookies=issued)
        except Exception as error:
            return ApiResponse.failure(problem_from_exception(error, request_id=request_id))

    def logout(
        self,
        *,
        method: str,
        headers: Mapping[str, str],
        cookies: Mapping[str, str],
        request_id: object = None,
    ) -> ApiResponse:
        try:
            validate_csrf(
                method=method,
                headers=headers,
                cookies=cookies,
                allowed_origins=self._allowed_origins,
            )
            self._sessions.logout(cookies.get(ACCESS_COOKIE, ""))
            return ApiResponse(200, data={"authenticated": False}, cookies=clear_session_cookies())
        except Exception as error:
            return ApiResponse.failure(problem_from_exception(error, request_id=request_id))

    def list_legacy_trades(
        self,
        *,
        access_token: str,
        grant: WorkspaceGrant | None,
        workspace_id: str,
        account_id: str | None = None,
        request_id: object = None,
    ) -> ApiResponse:
        try:
            user_id = self._sessions.validate_access(access_token)
            principal = UserPrincipal(user_id)
            scope = authorize_scope(
                principal,
                grant,
                workspace_id=workspace_id,
                account_id=account_id,
            )
            account_ids = (
                frozenset({scope.account_id})
                if scope.account_id is not None
                else grant.account_ids
            )
            snapshot = self._legacy.read(
                scope=ImportScope(scope.workspace_id, account_ids)
            )
            if snapshot.status is LegacySnapshotStatus.UNAVAILABLE:
                raise CapabilityError("unavailable", code="legacy_data_unavailable")
            return ApiResponse(
                200,
                data={
                    "data_status": snapshot.status.value,
                    "records": tuple(_record(record) for record in snapshot.records),
                    "issues": tuple(
                        {"row": issue.row, "code": issue.code, "fields": issue.fields}
                        for issue in snapshot.issues
                    ),
                },
            )
        except Exception as error:
            return ApiResponse.failure(problem_from_exception(error, request_id=request_id))
