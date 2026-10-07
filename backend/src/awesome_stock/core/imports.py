"""Deterministic, scoped reconciliation for imported trade facts."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .ledger import FactValidationError, Trade


class ImportScopeError(FactValidationError):
    """Raised when an import is missing or crosses its authorized scope."""


class ReadOnlyFactError(FactValidationError):
    """Raised when a source-owned fact is edited as if it were user data."""


def _required_text(value: object, field: str) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    if not normalized:
        raise FactValidationError(f"{field} is required")
    return normalized


def _currency(value: object) -> str:
    normalized = _required_text(value, "currency").upper()
    if len(normalized) != 3 or not normalized.isascii() or not normalized.isalpha():
        raise FactValidationError("currency must be a three-letter code")
    return normalized


def _moment(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise FactValidationError("executed_at must be a valid ISO datetime") from exc
    else:
        raise FactValidationError("executed_at must be a valid ISO datetime")
    if result.tzinfo is None or result.utcoffset() is None:
        raise FactValidationError("executed_at must include a timezone")
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class ImportScope:
    """Workspace and account boundary established by a trusted caller."""

    workspace_id: str
    allowed_account_ids: frozenset[str]

    def __post_init__(self) -> None:
        workspace = _required_text(self.workspace_id, "workspace_id")
        accounts = frozenset(
            _required_text(item, "account_id") for item in self.allowed_account_ids
        )
        if not accounts:
            raise ImportScopeError("at least one allowed account is required")
        object.__setattr__(self, "workspace_id", workspace)
        object.__setattr__(self, "allowed_account_ids", accounts)

    def validate(self, record: "TradeRecord") -> None:
        if record.workspace_id != self.workspace_id:
            raise ImportScopeError("trade workspace is outside the import scope")
        if record.account_id not in self.allowed_account_ids:
            raise ImportScopeError("trade account is outside the import scope")


@dataclass(frozen=True)
class TradeRecord:
    """Source-attributed trade fact with a stable import identity."""

    workspace_id: str
    account_id: str
    symbol: str
    currency: str
    source: str
    external_id: str
    executed_at: datetime | str
    trade: Trade | Mapping[str, object]
    sequence: int = 0
    read_only: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 0:
            raise FactValidationError("sequence must be a non-negative integer")
        if not isinstance(self.read_only, bool):
            raise FactValidationError("read_only must be a boolean")
        normalized_trade = self.trade if isinstance(self.trade, Trade) else Trade(**self.trade)
        object.__setattr__(self, "workspace_id", _required_text(self.workspace_id, "workspace_id"))
        object.__setattr__(self, "account_id", _required_text(self.account_id, "account_id"))
        object.__setattr__(self, "symbol", _required_text(self.symbol, "symbol").upper())
        object.__setattr__(self, "currency", _currency(self.currency))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "external_id", _required_text(self.external_id, "external_id"))
        object.__setattr__(self, "executed_at", _moment(self.executed_at))
        object.__setattr__(self, "trade", normalized_trade)

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return self.workspace_id, self.account_id, self.source, self.external_id

    @property
    def fact_signature(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.currency,
            self.executed_at,
            self.sequence,
            self.trade.side,
            self.trade.quantity,
            self.trade.price,
            self.trade.fee,
            self.read_only,
        )

    @property
    def sort_key(self) -> tuple[object, ...]:
        return (
            self.executed_at,
            self.sequence,
            self.account_id,
            self.source,
            self.external_id,
        )


@dataclass(frozen=True)
class ImportConflict:
    """Two different facts claiming the same stable source identity."""

    identity: tuple[str, str, str, str]
    existing: TradeRecord
    incoming: TradeRecord


@dataclass(frozen=True)
class ImportResult:
    """Complete reconciliation result; conflicts never enter the ledger."""

    ledger: tuple[TradeRecord, ...]
    accepted: tuple[TradeRecord, ...]
    duplicates: tuple[TradeRecord, ...]
    conflicts: tuple[ImportConflict, ...]


def reconcile_import(
    existing: Iterable[TradeRecord],
    incoming: Iterable[TradeRecord],
    *,
    scope: ImportScope,
) -> ImportResult:
    """Reconcile an import without mutating the prior ledger."""

    if not isinstance(scope, ImportScope):
        raise ImportScopeError("validated import scope is required")
    ledger_by_id: dict[tuple[str, str, str, str], TradeRecord] = {}
    for item in existing:
        record = item if isinstance(item, TradeRecord) else TradeRecord(**item)
        scope.validate(record)
        previous = ledger_by_id.get(record.identity)
        if previous is not None and previous.fact_signature != record.fact_signature:
            raise FactValidationError("existing ledger contains an identity conflict")
        ledger_by_id[record.identity] = record

    accepted: list[TradeRecord] = []
    duplicates: list[TradeRecord] = []
    conflicts: list[ImportConflict] = []
    for item in incoming:
        record = item if isinstance(item, TradeRecord) else TradeRecord(**item)
        scope.validate(record)
        previous = ledger_by_id.get(record.identity)
        if previous is None:
            ledger_by_id[record.identity] = record
            accepted.append(record)
        elif previous.fact_signature == record.fact_signature:
            duplicates.append(record)
        else:
            conflicts.append(ImportConflict(record.identity, previous, record))

    return ImportResult(
        ledger=tuple(sorted(ledger_by_id.values(), key=lambda item: item.sort_key)),
        accepted=tuple(sorted(accepted, key=lambda item: item.sort_key)),
        duplicates=tuple(sorted(duplicates, key=lambda item: item.sort_key)),
        conflicts=tuple(sorted(conflicts, key=lambda item: item.incoming.sort_key)),
    )


def replace_record(record: TradeRecord, **changes: object) -> TradeRecord:
    """Return an edited manual record; source-owned records stay immutable."""

    if record.read_only:
        raise ReadOnlyFactError("source-owned trade facts cannot be edited")
    return replace(record, **changes)


def rollback_import(
    ledger: Iterable[TradeRecord], accepted: Iterable[TradeRecord]
) -> tuple[TradeRecord, ...]:
    """Return a prior view without changing any imported fact object."""

    accepted_ids = {record.identity for record in accepted}
    return tuple(record for record in ledger if record.identity not in accepted_ids)
