"""Fail-closed, read-only adaptation of explicitly supplied legacy rows."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Mapping

from awesome_stock.core.imports import ImportScope, TradeRecord
from awesome_stock.core.ledger import FactValidationError, Trade


ALIASES = {
    "workspace_id": ("workspace_id", "workspace"),
    "account_id": ("account_id", "account"),
    "symbol": ("symbol", "ticker"),
    "currency": ("currency", "ccy"),
    "source": ("source", "provider"),
    "external_id": ("external_id", "source_id"),
    "executed_at": ("executed_at", "trade_time"),
    "side": ("side", "trade_type"),
    "quantity": ("quantity", "shares"),
    "price": ("price", "trade_price"),
    "fee": ("fee", "commission"),
    "sequence": ("sequence",),
}
SIDE_VALUES = {
    "b": "buy",
    "buy": "buy",
    "买入": "buy",
    "s": "sell",
    "sell": "sell",
    "卖出": "sell",
}


class LegacySnapshotStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class LegacyIssue:
    row: int | None
    code: str
    fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.code not in {
            "source_unavailable",
            "row_not_mapping",
            "missing_field",
            "ambiguous_field",
            "invalid_field",
            "defaulted_optional_field",
            "outside_scope",
        }:
            raise ValueError("unsupported legacy issue code")


@dataclass(frozen=True)
class LegacySnapshot:
    status: LegacySnapshotStatus
    records: tuple[TradeRecord, ...]
    issues: tuple[LegacyIssue, ...]

    def __post_init__(self) -> None:
        expected = (
            LegacySnapshotStatus.COMPLETE
            if not self.issues
            else LegacySnapshotStatus.PARTIAL
            if self.records
            else LegacySnapshotStatus.UNAVAILABLE
        )
        if self.status is not expected:
            raise ValueError("snapshot status does not match records and issues")


def _same(left: object, right: object) -> bool:
    return str(left).strip().casefold() == str(right).strip().casefold()


def _value(row: Mapping[str, object], field: str) -> tuple[object | None, str | None]:
    values = [(name, row[name]) for name in ALIASES[field] if name in row and row[name] is not None]
    if not values:
        return None, "missing_field"
    first = values[0][1]
    if any(not _same(first, value) for _name, value in values[1:]):
        return None, "ambiguous_field"
    return first, None


class LegacyReadAdapter:
    """Read legacy rows through an injected function; no write operation exists."""

    def __init__(
        self,
        reader: Callable[[str, tuple[str, ...]], Iterable[Mapping[str, object]]],
    ) -> None:
        if not callable(reader):
            raise TypeError("reader must be callable")
        self._reader = reader

    def read(self, *, scope: ImportScope) -> LegacySnapshot:
        if not isinstance(scope, ImportScope):
            raise FactValidationError("validated import scope is required")
        account_ids = tuple(sorted(scope.allowed_account_ids))
        try:
            rows = tuple(self._reader(scope.workspace_id, account_ids))
        except Exception:
            return LegacySnapshot(
                LegacySnapshotStatus.UNAVAILABLE,
                (),
                (LegacyIssue(None, "source_unavailable"),),
            )

        records: list[TradeRecord] = []
        issues: list[LegacyIssue] = []
        required = tuple(name for name in ALIASES if name not in {"fee", "sequence"})
        for index, raw_row in enumerate(rows):
            if not isinstance(raw_row, Mapping):
                issues.append(LegacyIssue(index, "row_not_mapping"))
                continue
            values: dict[str, object] = {}
            rejected = False
            for field in required:
                value, error = _value(raw_row, field)
                if error:
                    issues.append(LegacyIssue(index, error, (field,)))
                    rejected = True
                else:
                    values[field] = value
            for field, fallback in (("fee", "0"), ("sequence", 0)):
                value, error = _value(raw_row, field)
                if error == "ambiguous_field":
                    issues.append(LegacyIssue(index, error, (field,)))
                    rejected = True
                elif error == "missing_field":
                    values[field] = fallback
                    issues.append(LegacyIssue(index, "defaulted_optional_field", (field,)))
                else:
                    values[field] = value
            if rejected:
                continue
            normalized_side = SIDE_VALUES.get(str(values["side"]).strip().casefold())
            if normalized_side is None:
                issues.append(LegacyIssue(index, "invalid_field", ("side",)))
                continue
            try:
                record = TradeRecord(
                    workspace_id=values["workspace_id"],
                    account_id=values["account_id"],
                    symbol=values["symbol"],
                    currency=values["currency"],
                    source=values["source"],
                    external_id=values["external_id"],
                    executed_at=values["executed_at"],
                    sequence=values["sequence"],
                    trade=Trade(
                        normalized_side,
                        values["quantity"],
                        values["price"],
                        values["fee"],
                    ),
                    read_only=True,
                )
                scope.validate(record)
            except FactValidationError as error:
                code = "outside_scope" if "outside" in str(error) else "invalid_field"
                issues.append(LegacyIssue(index, code))
                continue
            records.append(record)
        status = (
            LegacySnapshotStatus.COMPLETE
            if not issues
            else LegacySnapshotStatus.PARTIAL
            if records
            else LegacySnapshotStatus.UNAVAILABLE
        )
        return LegacySnapshot(status, tuple(sorted(records, key=lambda item: item.sort_key)), tuple(issues))
