"""Rule-based opportunity screening without scores or recommendations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .evidence import EvidenceLedger, ResearchValidationError, as_decimal


@dataclass(frozen=True)
class ScreenCandidate:
    symbol: str
    name: str
    market: str
    evidence: EvidenceLedger

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper() if isinstance(self.symbol, str) else ""
        market = self.market.strip().upper() if isinstance(self.market, str) else ""
        if not symbol or not self.name.strip() or market not in {"US", "HK", "CN"}:
            raise ResearchValidationError("screen candidate is invalid")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "market", market)


@dataclass(frozen=True)
class ScreenRules:
    revenue_growth_min: Decimal | str | int | float = Decimal("12")
    gross_margin_min: Decimal | str | int | float = Decimal("35")
    net_debt_ebitda_max: Decimal | str | int | float = Decimal("2")
    coverage_min: Decimal | str | int | float = Decimal("60")

    def __post_init__(self) -> None:
        for field in ("revenue_growth_min", "gross_margin_min", "net_debt_ebitda_max", "coverage_min"):
            value = as_decimal(getattr(self, field), field)
            object.__setattr__(self, field, value)
        if not Decimal("0") <= self.coverage_min <= Decimal("100"):
            raise ResearchValidationError("coverage must be between zero and one hundred")


@dataclass(frozen=True)
class ScreenResult:
    symbol: str
    name: str
    market: str
    status: str
    reasons: tuple[str, ...]
    missing_keys: tuple[str, ...]
    coverage_percent: Decimal
    revenue_growth: Decimal | None
    gross_margin: Decimal | None
    net_debt_ebitda: Decimal | None


def run_screen(candidates: Iterable[ScreenCandidate], rules: ScreenRules, *, market: object = "all") -> tuple[ScreenResult, ...]:
    normalized_market = market.strip().upper() if isinstance(market, str) else ""
    if normalized_market not in {"ALL", "US", "HK", "CN"}:
        raise ResearchValidationError("market is invalid")
    rows = []
    for candidate in tuple(candidates):
        if normalized_market != "ALL" and candidate.market != normalized_market:
            continue
        growth = candidate.evidence.fact("revenue_growth")
        margin = candidate.evidence.fact("gross_margin")
        leverage = candidate.evidence.fact("net_debt_ebitda")
        required = (growth, margin, leverage)
        if any(fact is None for fact in required):
            raise ResearchValidationError("candidate lacks required evidence definitions")
        reasons = []
        if growth.value is not None and growth.value < rules.revenue_growth_min:
            reasons.append("营收增长低于规则线")
        if margin.value is not None and margin.value < rules.gross_margin_min:
            reasons.append("毛利率低于规则线")
        if leverage.value is not None and leverage.value > rules.net_debt_ebitda_max:
            reasons.append("杠杆高于规则线")
        if candidate.evidence.coverage_percent < rules.coverage_min:
            reasons.append("证据覆盖率低于规则线")
        missing = tuple(fact.key for fact in required if fact.value is None)
        status = "excluded" if reasons else "needs_evidence" if missing else "matched"
        rows.append(ScreenResult(
            candidate.symbol,
            candidate.name,
            candidate.market,
            status,
            tuple(reasons),
            missing,
            candidate.evidence.coverage_percent,
            growth.value,
            margin.value,
            leverage.value,
        ))
    return tuple(rows)
