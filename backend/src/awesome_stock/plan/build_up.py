"""Transparent staged-entry planning without order execution."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Iterable

from .allocation import HUNDRED, PlanValidationError, decimal_value


@dataclass(frozen=True)
class BuildStage:
    weight_percent: Decimal
    price_offset_percent: Decimal

    def __post_init__(self) -> None:
        weight = decimal_value(self.weight_percent, "weight_percent", minimum=Decimal("0.01"))
        try:
            offset = Decimal(str(self.price_offset_percent))
        except Exception as exc:
            raise PlanValidationError("price_offset_percent must be decimal") from exc
        if not offset.is_finite() or offset <= Decimal("-100") or offset > Decimal("100"):
            raise PlanValidationError("price offset is outside its supported range")
        object.__setattr__(self, "weight_percent", weight)
        object.__setattr__(self, "price_offset_percent", offset)


@dataclass(frozen=True)
class PlannedStage:
    sequence: int
    weight_percent: Decimal
    price_offset_percent: Decimal
    trigger_price: Decimal
    shares: Decimal
    gross_value: Decimal
    fee: Decimal
    required_cash: Decimal


@dataclass(frozen=True)
class BuildUpPlan:
    symbol: str
    budget: Decimal
    current_price: Decimal
    stages: tuple[PlannedStage, ...]
    planned_cash: Decimal
    unallocated_cash: Decimal
    available_cash_after: Decimal
    projected_position_value: Decimal
    projected_weight_percent: Decimal
    status: str
    issues: tuple[str, ...]


def create_build_up_plan(
    *,
    symbol: str,
    budget: object,
    current_price: object,
    available_cash: object,
    current_position_value: object,
    net_assets: object,
    stages: Iterable[BuildStage],
    fee_per_stage: object = Decimal("1"),
    max_position_percent: object = Decimal("25"),
) -> BuildUpPlan:
    if not isinstance(symbol, str) or not symbol.strip():
        raise PlanValidationError("symbol is required")
    planned_budget = decimal_value(budget, "budget", minimum=Decimal("0.01"))
    price = decimal_value(current_price, "current_price", minimum=Decimal("0.01"))
    cash = decimal_value(available_cash, "available_cash")
    position_value = decimal_value(current_position_value, "current_position_value")
    assets = decimal_value(net_assets, "net_assets", minimum=Decimal("0.01"))
    fee = decimal_value(fee_per_stage, "fee_per_stage")
    limit = decimal_value(max_position_percent, "max_position_percent", minimum=Decimal("0.01"))
    if limit > HUNDRED:
        raise PlanValidationError("max_position_percent cannot exceed 100")
    stage_inputs = tuple(stages)
    if not stage_inputs or sum((item.weight_percent for item in stage_inputs), Decimal("0")) != HUNDRED:
        raise PlanValidationError("stage weights must total 100")

    planned_stages = []
    for index, stage in enumerate(stage_inputs, start=1):
        trigger_price = price * (Decimal("1") + stage.price_offset_percent / HUNDRED)
        stage_budget = planned_budget * stage.weight_percent / HUNDRED
        spendable = max(Decimal("0"), stage_budget - fee)
        shares = (spendable / trigger_price).to_integral_value(rounding=ROUND_DOWN)
        gross = shares * trigger_price
        stage_fee = fee if shares > 0 else Decimal("0")
        planned_stages.append(
            PlannedStage(
                index,
                stage.weight_percent,
                stage.price_offset_percent,
                trigger_price,
                shares,
                gross,
                stage_fee,
                gross + stage_fee,
            )
        )
    planned_cash = sum((stage.required_cash for stage in planned_stages), Decimal("0"))
    projected_position = position_value + sum((stage.gross_value for stage in planned_stages), Decimal("0"))
    projected_weight = projected_position / assets * HUNDRED
    issues = []
    if planned_cash > cash:
        issues.append("insufficient_cash")
    if projected_weight > limit:
        issues.append("position_limit_exceeded")
    status = "blocked" if "insufficient_cash" in issues else "warning" if issues else "ready_for_review"
    return BuildUpPlan(
        symbol.strip().upper(),
        planned_budget,
        price,
        tuple(planned_stages),
        planned_cash,
        planned_budget - planned_cash,
        cash - planned_cash,
        projected_position,
        projected_weight,
        status,
        tuple(issues),
    )
