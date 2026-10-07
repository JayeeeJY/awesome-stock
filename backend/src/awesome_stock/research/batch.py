"""Side-by-side research facts with evidence-gap priority, never ranking."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .evidence import ResearchValidationError
from .screening import ScreenCandidate


@dataclass(frozen=True)
class BatchComparisonRow:
    symbol: str
    name: str
    market: str
    coverage_count: int
    coverage_total: int
    coverage_percent: Decimal
    revenue_growth: str | None
    gross_margin: str | None
    net_debt_ebitda: str | None
    gaps: tuple[str, ...]
    review_priority: str


def _value(candidate: ScreenCandidate, key: str) -> str | None:
    fact = candidate.evidence.fact(key)
    return None if fact is None or fact.value is None else str(fact.value)


def compare_research(candidates: Iterable[ScreenCandidate], symbols: object) -> tuple[BatchComparisonRow, ...]:
    if not isinstance(symbols, (tuple, list)):
        raise ResearchValidationError("symbols must be a list")
    normalized = tuple(str(symbol).strip().upper() for symbol in symbols)
    if not 2 <= len(normalized) <= 4 or len(set(normalized)) != len(normalized) or any(not symbol for symbol in normalized):
        raise ResearchValidationError("select two to four unique symbols")
    universe = {candidate.symbol: candidate for candidate in candidates}
    if any(symbol not in universe for symbol in normalized):
        raise ResearchValidationError("selected symbol is outside the synthetic universe")
    rows = []
    for symbol in normalized:
        candidate = universe[symbol]
        gaps = tuple(fact.statement for fact in candidate.evidence.facts if fact.status == "missing")
        rows.append(BatchComparisonRow(
            candidate.symbol,
            candidate.name,
            candidate.market,
            candidate.evidence.coverage_count,
            candidate.evidence.total_count,
            candidate.evidence.coverage_percent,
            _value(candidate, "revenue_growth"),
            _value(candidate, "gross_margin"),
            _value(candidate, "net_debt_ebitda"),
            gaps,
            "补证优先" if gaps else "复核假设",
        ))
    return tuple(rows)
