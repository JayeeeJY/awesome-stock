"""Deterministic, side-effect-free investment facts."""

from .baseline import BaselineResult, PositionBaseline, rebuild_from_baseline
from .imports import (
    ImportConflict,
    ImportResult,
    ImportScope,
    ImportScopeError,
    ReadOnlyFactError,
    TradeRecord,
    reconcile_import,
    replace_record,
    rollback_import,
)
from .ledger import (
    CostMethod,
    FactValidationError,
    OpeningLot,
    OpeningPosition,
    PositionFacts,
    Trade,
    TradeSide,
    ValuationFacts,
    calculate_position,
    value_position,
)
from .portfolio import PortfolioFacts, PositionValue, aggregate_portfolio, convert_to_base
from .vectors import evaluate_ledger_vector, evaluate_missingness_vector, evaluate_mixed_currency_vector

__all__ = [
    "BaselineResult",
    "CostMethod",
    "FactValidationError",
    "ImportConflict",
    "ImportResult",
    "ImportScope",
    "ImportScopeError",
    "OpeningLot",
    "OpeningPosition",
    "PortfolioFacts",
    "PositionBaseline",
    "PositionFacts",
    "PositionValue",
    "ReadOnlyFactError",
    "Trade",
    "TradeRecord",
    "TradeSide",
    "ValuationFacts",
    "aggregate_portfolio",
    "calculate_position",
    "convert_to_base",
    "evaluate_ledger_vector",
    "evaluate_missingness_vector",
    "evaluate_mixed_currency_vector",
    "rebuild_from_baseline",
    "reconcile_import",
    "replace_record",
    "rollback_import",
    "value_position",
]
