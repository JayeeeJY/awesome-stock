"""Adapters for the independent synthetic acceptance-vector schema."""

from decimal import Decimal
from typing import Mapping

from .ledger import Trade, calculate_position, value_position
from .portfolio import PositionValue, aggregate_portfolio, convert_to_base


def _encoded(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def evaluate_ledger_vector(vector: Mapping[str, object]) -> dict[str, object]:
    """Evaluate one LED ledger vector and return JSON-safe facts."""

    facts = calculate_position(
        [Trade(**item) for item in vector["trades"]],
        quote=vector.get("quote"),
        method=vector["method"],
        currency=vector["currency"],
    )
    return {
        "shares": _encoded(facts.shares),
        "open_cost": _encoded(facts.open_cost),
        "released_cost": _encoded(facts.released_cost),
        "realized": _encoded(facts.realized),
        "market_value": _encoded(facts.market_value),
        "unrealized": _encoded(facts.unrealized),
        "total_pnl": _encoded(facts.total_pnl),
        "cash_delta": _encoded(facts.cash_delta),
        "ratio_available": facts.ratio_available,
    }


def evaluate_mixed_currency_vector(vector: Mapping[str, object]) -> dict[str, object]:
    """Evaluate the current synthetic USD/HKD portfolio-vector contract."""

    facts = aggregate_portfolio(
        [PositionValue(**item) for item in vector["positions"]],
        base_currency=vector["base_currency"],
        units_per_base={"HKD": vector["hkd_per_usd"]},
        cash_base=vector.get("cash_usd"),
    )
    weight = facts.position_weights_of_holdings[0] if facts.position_weights_of_holdings else None
    return {
        "holdings_value_base": _encoded(facts.holdings_value_base),
        "open_cost_base": _encoded(facts.open_cost_base),
        "unrealized_base": _encoded(facts.unrealized_base),
        "realized_base": _encoded(facts.realized_base),
        "total_pnl_base": _encoded(facts.total_pnl_base),
        "net_assets_base": _encoded(facts.net_assets_base),
        "invested_ratio": _encoded(facts.invested_ratio),
        "cash_ratio": _encoded(facts.cash_ratio),
        "position_weight_of_holdings": _encoded(weight),
    }


def evaluate_missingness_vector(vector: Mapping[str, object]) -> dict[str, object]:
    """Evaluate an explicit missing-cash, missing-FX, or missing-quote vector."""

    vector_id = vector["id"]
    if vector_id == "LED-NO-CASH":
        facts = aggregate_portfolio(
            [PositionValue("SYNTHETIC", "USD", vector["holdings_value_base"], "0")],
            base_currency="USD",
            units_per_base={},
            cash_base=vector.get("cash"),
        )
        return {
            "expected_net_assets_base": _encoded(facts.net_assets_base),
            "expected_cash_ratio": _encoded(facts.cash_ratio),
            "expected_invested_ratio": _encoded(facts.invested_ratio),
        }
    if vector_id == "LED-NO-FX":
        converted = convert_to_base(
            vector["market_value"],
            currency=vector["currency"],
            base_currency="USD",
            units_per_base={},
        )
        return {
            "expected_market_value_base": _encoded(converted),
            "expected_valuation_complete": converted is not None,
        }
    if vector_id == "LED-NO-QUOTE":
        facts = value_position(
            shares=vector["shares"],
            open_cost=vector["open_cost"],
            quote=vector.get("quote"),
        )
        return {
            "expected_market_value": _encoded(facts.market_value),
            "expected_unrealized": _encoded(facts.unrealized),
        }
    raise ValueError(f"unsupported missingness vector: {vector_id}")
