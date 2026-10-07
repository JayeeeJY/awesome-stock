"""Deterministic position rebuilds from an explicit opening baseline."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from .imports import ImportScope, ImportScopeError, TradeRecord, reconcile_import
from .ledger import CostMethod, FactValidationError, OpeningPosition, PositionFacts, calculate_position


def _cutoff(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise FactValidationError("cutoff must be a valid ISO datetime") from exc
    else:
        raise FactValidationError("cutoff must be a valid ISO datetime")
    if result.tzinfo is None or result.utcoffset() is None:
        raise FactValidationError("cutoff must include a timezone")
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class PositionBaseline:
    """Opening facts for exactly one scoped account, symbol, and currency."""

    workspace_id: str
    account_id: str
    symbol: str
    currency: str
    cutoff: datetime | str
    opening: OpeningPosition

    def __post_init__(self) -> None:
        workspace = self.workspace_id.strip() if isinstance(self.workspace_id, str) else ""
        account = self.account_id.strip() if isinstance(self.account_id, str) else ""
        symbol = self.symbol.strip().upper() if isinstance(self.symbol, str) else ""
        currency = self.currency.strip().upper() if isinstance(self.currency, str) else ""
        if not workspace or not account or not symbol:
            raise FactValidationError("baseline workspace, account, and symbol are required")
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise FactValidationError("currency must be a three-letter code")
        opening = (
            self.opening
            if isinstance(self.opening, OpeningPosition)
            else OpeningPosition(**self.opening)
        )
        object.__setattr__(self, "workspace_id", workspace)
        object.__setattr__(self, "account_id", account)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "cutoff", _cutoff(self.cutoff))
        object.__setattr__(self, "opening", opening)


@dataclass(frozen=True)
class BaselineResult:
    """Position result with an explicit record of cutoff exclusions."""

    position: PositionFacts
    applied_ids: tuple[str, ...]
    excluded_at_or_before_cutoff_ids: tuple[str, ...]


def rebuild_from_baseline(
    baseline: PositionBaseline,
    records: Iterable[TradeRecord],
    *,
    quote: Decimal | str | int | float | None,
    method: CostMethod | str,
    scope: ImportScope,
) -> BaselineResult:
    """Apply only matching, post-cutoff facts in stable ledger order."""

    if not isinstance(scope, ImportScope):
        raise ImportScopeError("validated import scope is required")
    if baseline.workspace_id != scope.workspace_id or baseline.account_id not in scope.allowed_account_ids:
        raise ImportScopeError("baseline is outside the rebuild scope")

    reconciled = reconcile_import((), records, scope=scope)
    if reconciled.conflicts:
        raise FactValidationError("baseline input contains an identity conflict")

    applied: list[TradeRecord] = []
    excluded: list[TradeRecord] = []
    for record in reconciled.ledger:
        if record.account_id != baseline.account_id:
            raise ImportScopeError("record account does not match baseline account")
        if record.symbol != baseline.symbol or record.currency != baseline.currency:
            raise FactValidationError("record symbol and currency must match baseline")
        if record.executed_at <= baseline.cutoff:
            excluded.append(record)
        else:
            applied.append(record)

    applied.sort(key=lambda item: item.sort_key)
    excluded.sort(key=lambda item: item.sort_key)
    position = calculate_position(
        (item.trade for item in applied),
        quote=quote,
        method=method,
        currency=baseline.currency,
        opening=baseline.opening,
    )
    return BaselineResult(
        position=position,
        applied_ids=tuple(item.external_id for item in applied),
        excluded_at_or_before_cutoff_ids=tuple(item.external_id for item in excluded),
    )
