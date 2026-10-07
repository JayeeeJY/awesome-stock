"""Deterministic target-versus-current allocation analysis."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


HUNDRED = Decimal("100")


class PlanValidationError(ValueError):
    """Invalid planning input that must become a public 422 response."""

    code = "invalid_plan_input"


def decimal_value(value: object, field: str, *, minimum: Decimal = Decimal("0")) -> Decimal:
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise PlanValidationError(f"{field} must be decimal") from exc
    if not number.is_finite() or number < minimum:
        raise PlanValidationError(f"{field} is outside its supported range")
    return number


@dataclass(frozen=True)
class AllocationItem:
    key: str
    name: str
    current_value: Decimal
    target_percent: Decimal

    def __post_init__(self) -> None:
        if not self.key or not self.name:
            raise PlanValidationError("allocation key and name are required")
        object.__setattr__(self, "current_value", decimal_value(self.current_value, "current_value"))
        target = decimal_value(self.target_percent, "target_percent")
        if target > HUNDRED:
            raise PlanValidationError("target_percent cannot exceed 100")
        object.__setattr__(self, "target_percent", target)


@dataclass(frozen=True)
class AllocationRow:
    key: str
    name: str
    current_value: Decimal
    target_value: Decimal
    current_percent: Decimal
    target_percent: Decimal
    deviation_pp: Decimal
    adjustment_value: Decimal
    status: str


@dataclass(frozen=True)
class AllocationResult:
    net_assets: Decimal
    tolerance_pp: Decimal
    rows: tuple[AllocationRow, ...]
    total_to_shift: Decimal
    status: str


def analyze_allocation(
    *,
    net_assets: object,
    items: Iterable[AllocationItem],
    tolerance_pp: object = Decimal("2"),
) -> AllocationResult:
    assets = decimal_value(net_assets, "net_assets", minimum=Decimal("0.01"))
    tolerance = decimal_value(tolerance_pp, "tolerance_pp")
    rows_in = tuple(items)
    if len(rows_in) < 2 or len({item.key for item in rows_in}) != len(rows_in):
        raise PlanValidationError("allocation items must contain unique categories")
    if sum((item.target_percent for item in rows_in), Decimal("0")) != HUNDRED:
        raise PlanValidationError("target percentages must total 100")
    current_total = sum((item.current_value for item in rows_in), Decimal("0"))
    if abs(current_total - assets) > Decimal("0.01"):
        raise PlanValidationError("allocation values must reconcile to net assets")

    rows = []
    for item in rows_in:
        current_percent = item.current_value / assets * HUNDRED
        target_value = assets * item.target_percent / HUNDRED
        deviation = current_percent - item.target_percent
        if deviation > tolerance:
            status = "over"
        elif deviation < -tolerance:
            status = "under"
        else:
            status = "within"
        rows.append(
            AllocationRow(
                key=item.key,
                name=item.name,
                current_value=item.current_value,
                target_value=target_value,
                current_percent=current_percent,
                target_percent=item.target_percent,
                deviation_pp=deviation,
                adjustment_value=target_value - item.current_value,
                status=status,
            )
        )
    total_to_shift = sum(
        (row.adjustment_value for row in rows if row.adjustment_value > 0),
        Decimal("0"),
    )
    status = "needs_adjustment" if any(row.status != "within" for row in rows) else "within_policy"
    return AllocationResult(assets, tolerance, tuple(rows), total_to_shift, status)
