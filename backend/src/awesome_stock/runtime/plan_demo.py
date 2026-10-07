"""Authenticated all-synthetic projections for the three Plan tools."""

from decimal import Decimal
from typing import Mapping

from awesome_stock.api.contracts import ApiResponse, problem_from_exception
from awesome_stock.plan.allocation import AllocationItem, PlanValidationError, analyze_allocation
from awesome_stock.plan.build_up import BuildStage, create_build_up_plan
from awesome_stock.plan.pre_trade import check_trade


BUCKETS = {
    "core": ("核心资产", frozenset({"ALPH", "BETA", "IOTA"})),
    "growth": ("成长资产", frozenset({"GAMMA", "DELTA", "EPSLN", "LAMBDA"})),
    "defensive": ("防御资产", frozenset({"ZETA", "THETA"})),
    "opportunity": ("机会仓", frozenset({"KAPPA"})),
    "cash": ("现金", frozenset()),
}
DEFAULT_TARGETS = {
    "core": Decimal("40"),
    "growth": Decimal("25"),
    "defensive": Decimal("15"),
    "opportunity": Decimal("5"),
    "cash": Decimal("15"),
}
DEFAULT_STAGES = (
    BuildStage(Decimal("35"), Decimal("0")),
    BuildStage(Decimal("35"), Decimal("-5")),
    BuildStage(Decimal("30"), Decimal("-10")),
)


def _decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _portfolio(runtime, access_token: str, request_id: object) -> tuple[dict[str, object] | None, ApiResponse | None]:
    response = runtime.portfolio(access_token, request_id=request_id)
    if response.problem is not None:
        return None, response
    return response.data, None


def _targets(value: object) -> dict[str, Decimal]:
    if value is None:
        return dict(DEFAULT_TARGETS)
    if not isinstance(value, Mapping) or set(value) != set(DEFAULT_TARGETS):
        raise PlanValidationError("target categories must match the current policy")
    try:
        return {key: Decimal(str(value[key])) for key in DEFAULT_TARGETS}
    except Exception as exc:
        raise PlanValidationError("target percentages must be decimal") from exc


def allocation_response(runtime, *, access_token: str, targets: object = None, request_id: object = None) -> ApiResponse:
    try:
        portfolio, failure = _portfolio(runtime, access_token, request_id)
        if failure is not None:
            return failure
        requested = _targets(targets)
        totals = {key: Decimal("0") for key in BUCKETS}
        for holding in portfolio["holdings"]:
            matched = next(
                (key for key, (_name, symbols) in BUCKETS.items() if holding["symbol"] in symbols),
                None,
            )
            if matched is None:
                raise PlanValidationError("holding category is not defined")
            totals[matched] += Decimal(holding["market_value"])
        totals["cash"] = Decimal(portfolio["summary"]["cash"])
        result = analyze_allocation(
            net_assets=portfolio["summary"]["net_assets"],
            items=tuple(
                AllocationItem(key, BUCKETS[key][0], totals[key], requested[key])
                for key in BUCKETS
            ),
        )
        return ApiResponse(
            200,
            data={
                "mode": "synthetic_preview",
                "persistence": False,
                "execution": False,
                "summary": {
                    "net_assets": _decimal(result.net_assets),
                    "invested_percent": portfolio["summary"]["invested_ratio"],
                    "cash_percent": portfolio["summary"]["cash_ratio"],
                    "status": result.status,
                    "tolerance_pp": _decimal(result.tolerance_pp),
                    "total_to_shift": _decimal(result.total_to_shift),
                },
                "rows": tuple(
                    {
                        "key": row.key,
                        "name": row.name,
                        "current_value": _decimal(row.current_value),
                        "target_value": _decimal(row.target_value),
                        "current_percent": _decimal(row.current_percent),
                        "target_percent": _decimal(row.target_percent),
                        "deviation_pp": _decimal(row.deviation_pp),
                        "adjustment_value": _decimal(row.adjustment_value),
                        "status": row.status,
                    }
                    for row in result.rows
                ),
            },
        )
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))


def build_up_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        portfolio, failure = _portfolio(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        holdings = {item["symbol"]: item for item in portfolio["holdings"]}
        symbol = str(body.get("symbol", "BETA")).upper()
        if symbol not in holdings:
            raise PlanValidationError("symbol is outside the synthetic portfolio")
        holding = holdings[symbol]
        raw_stages = body.get("stages")
        if raw_stages is None:
            stages = DEFAULT_STAGES
        elif isinstance(raw_stages, list):
            stages = tuple(
                BuildStage(item.get("weight_percent"), item.get("price_offset_percent"))
                for item in raw_stages
                if isinstance(item, Mapping)
            )
        else:
            raise PlanValidationError("stages must be a list")
        plan = create_build_up_plan(
            symbol=symbol,
            budget=body.get("budget", "18000"),
            current_price=holding["price"],
            available_cash=portfolio["summary"]["cash"],
            current_position_value=holding["market_value"],
            net_assets=portfolio["summary"]["net_assets"],
            stages=stages,
            fee_per_stage=body.get("fee_per_stage", "1"),
            max_position_percent=body.get("max_position_percent", "25"),
        )
        return ApiResponse(
            200,
            data={
                "mode": "synthetic_preview",
                "persistence": False,
                "execution": False,
                "symbols": tuple(
                    {"symbol": item["symbol"], "name": item["name"], "price": item["price"]}
                    for item in portfolio["holdings"]
                ),
                "plan": {
                    "symbol": plan.symbol,
                    "budget": _decimal(plan.budget),
                    "current_price": _decimal(plan.current_price),
                    "planned_cash": _decimal(plan.planned_cash),
                    "unallocated_cash": _decimal(plan.unallocated_cash),
                    "available_cash_after": _decimal(plan.available_cash_after),
                    "projected_position_value": _decimal(plan.projected_position_value),
                    "projected_weight_percent": _decimal(plan.projected_weight_percent),
                    "status": plan.status,
                    "issues": plan.issues,
                    "stages": tuple(
                        {
                            "sequence": stage.sequence,
                            "weight_percent": _decimal(stage.weight_percent),
                            "price_offset_percent": _decimal(stage.price_offset_percent),
                            "trigger_price": _decimal(stage.trigger_price),
                            "shares": _decimal(stage.shares),
                            "gross_value": _decimal(stage.gross_value),
                            "fee": _decimal(stage.fee),
                            "required_cash": _decimal(stage.required_cash),
                        }
                        for stage in plan.stages
                    ),
                },
            },
        )
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))


def pre_trade_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        portfolio, failure = _portfolio(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        holdings = {item["symbol"]: item for item in portfolio["holdings"]}
        symbol = str(body.get("symbol", "ALPH")).upper()
        if symbol not in holdings:
            raise PlanValidationError("symbol is outside the synthetic portfolio")
        holding = holdings[symbol]
        impact = check_trade(
            symbol=symbol,
            side=body.get("side", "buy"),
            quantity=body.get("quantity", "20"),
            price=body.get("price", holding["price"]),
            fee=body.get("fee", "1"),
            current_quantity=holding["quantity"],
            current_position_value=holding["market_value"],
            available_cash=portfolio["summary"]["cash"],
            net_assets=portfolio["summary"]["net_assets"],
            max_position_percent=body.get("max_position_percent", "20"),
        )
        return ApiResponse(
            200,
            data={
                "mode": "synthetic_preview",
                "persistence": False,
                "execution": False,
                "symbols": tuple(
                    {"symbol": item["symbol"], "name": item["name"], "price": item["price"]}
                    for item in portfolio["holdings"]
                ),
                "impact": {
                    "symbol": impact.symbol,
                    "side": impact.side,
                    "quantity": _decimal(impact.quantity),
                    "current_quantity": _decimal(impact.current_quantity),
                    "price": _decimal(impact.price),
                    "fee": _decimal(impact.fee),
                    "gross_value": _decimal(impact.gross_value),
                    "post_cash": _decimal(impact.post_cash),
                    "post_quantity": _decimal(impact.post_quantity),
                    "post_position_value": _decimal(impact.post_position_value),
                    "post_weight_percent": _decimal(impact.post_weight_percent),
                    "estimated_net_assets": _decimal(impact.estimated_net_assets),
                    "status": impact.status,
                    "checks": tuple(
                        {"code": item.code, "status": item.status, "label": item.label, "detail": item.detail}
                        for item in impact.checks
                    ),
                },
            },
        )
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))
