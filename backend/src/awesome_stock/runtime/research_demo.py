"""Authenticated, all-synthetic projections for the three Research pages."""

from decimal import Decimal
from typing import Mapping

from awesome_stock.api.contracts import ApiResponse, problem_from_exception
from awesome_stock.research.batch import compare_research
from awesome_stock.research.company import create_research_brief
from awesome_stock.research.evidence import EvidenceFact, EvidenceLedger, ResearchValidationError
from awesome_stock.research.screening import ScreenCandidate, ScreenRules, run_screen


OBSERVED_AT = "2026-08-31"
FACT_LABELS = {
    "revenue_growth": ("增长", "营收同比增长", "%"),
    "gross_margin": ("质量", "毛利率", "%"),
    "net_debt_ebitda": ("风险", "净债务/EBITDA", "x"),
    "customer_concentration": ("风险", "前五大客户占比", "%"),
    "rd_ratio": ("投入", "研发费用率", "%"),
    "cashflow_growth": ("现金流", "经营现金流增长", "%"),
}
SYNTHETIC_ROWS = (
    ("ALPH", "Alpha Systems", "US", ("18.4", "42.1", None, None, "8.6", "12.3")),
    ("BETA", "Beta Works", "US", ("9.2", "36.4", "1.6", "28.0", "5.4", "7.8")),
    ("GAMMA", "Gamma Labs", "US", ("27.8", "58.2", "0.4", "22.0", "18.3", "31.0")),
    ("DELTA", "Delta Industries", "HK", ("5.1", "24.6", "3.2", "46.0", "4.2", "-8.0")),
    ("EPSLN", "Epsilon Health", "US", ("16.3", "55.0", None, "35.0", "14.0", "19.0")),
    ("ZETA", "Zeta Consumer", "HK", ("7.1", "31.2", "1.2", "18.0", "3.2", "5.6")),
    ("THETA", "Theta Energy", "CN", ("12.0", "28.0", "2.1", None, "2.0", "10.0")),
    ("IOTA", "Iota Finance", "CN", ("14.2", "49.0", "1.8", "21.0", "9.1", "15.0")),
)


def _fact(key: str, value: str | None) -> EvidenceFact:
    dimension, statement, unit = FACT_LABELS[key]
    return EvidenceFact(
        key,
        dimension,
        statement,
        value,
        unit,
        "missing" if value is None else "verified",
        None if value is None else OBSERVED_AT,
    )


def synthetic_universe() -> tuple[ScreenCandidate, ...]:
    keys = tuple(FACT_LABELS)
    return tuple(
        ScreenCandidate(symbol, name, market, EvidenceLedger(tuple(_fact(key, value) for key, value in zip(keys, values))))
        for symbol, name, market, values in SYNTHETIC_ROWS
    )


def _decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _flags() -> dict[str, object]:
    return {
        "mode": "synthetic_preview",
        "persistence": False,
        "ai_generated": False,
        "external_provider": False,
    }


def _portfolio(runtime, access_token: str, request_id: object) -> tuple[dict[str, object] | None, ApiResponse | None]:
    response = runtime.portfolio(access_token, request_id=request_id)
    if response.problem is not None:
        return None, response
    return response.data, None


def _evidence(fact: EvidenceFact) -> dict[str, object]:
    if fact.value is None:
        display = "-- / 待补"
        value = None
    else:
        suffix = "%" if fact.unit == "%" else "×" if fact.unit == "x" else fact.unit
        display = f"{fact.value}{suffix}"
        value = str(fact.value)
    return {
        "key": fact.key,
        "dimension": fact.dimension,
        "statement": fact.statement,
        "value": value,
        "unit": fact.unit,
        "display_value": display,
        "status": fact.status,
        "observed_at": fact.observed_at,
        "source": "合成研究样本",
    }


def _brief(candidate: ScreenCandidate, *, focus: object, question: object, portfolio: Mapping[str, object]) -> dict[str, object]:
    brief = create_research_brief(candidate.symbol, candidate.name, candidate.evidence, focus=focus, question=question)
    holding = next((item for item in portfolio["holdings"] if item["symbol"] == candidate.symbol), None)
    return {
        "symbol": brief.symbol,
        "name": brief.name,
        "market": candidate.market,
        "focus": brief.focus,
        "question": brief.question,
        "question_role": "context_only",
        "conclusion_code": brief.conclusion_code,
        "conclusion_title": brief.conclusion_title,
        "summary": brief.summary,
        "coverage": {
            "available": brief.evidence.coverage_count,
            "total": brief.evidence.total_count,
            "percent": _decimal(brief.evidence.coverage_percent),
        },
        "evidence": tuple(_evidence(fact) for fact in brief.evidence.facts),
        "actions": tuple({"key": action.key, "title": action.title, "detail": action.detail} for action in brief.actions),
        "portfolio_context": {
            "held": holding is not None,
            "weight": None if holding is None else holding["weight"],
            "market_value": None if holding is None else holding["market_value"],
            "today_percent": None if holding is None else holding["today_percent"],
            "total_pnl_percent": None if holding is None else holding["total_pnl_percent"],
        },
        "observation_note": "固定合成观察日，不代表实时数据",
    }


def company_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        portfolio, failure = _portfolio(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        universe = synthetic_universe()
        candidates = {candidate.symbol: candidate for candidate in universe}
        symbol = str(body.get("symbol", "ALPH")).strip().upper()
        if symbol not in candidates:
            raise ResearchValidationError("symbol is outside the synthetic universe")
        focus = body.get("focus", "overview")
        question = body.get("question", "哪些事实支持当前增长，哪些关键证据仍然缺失？")
        return ApiResponse(200, data={
            **_flags(),
            "symbols": tuple({"symbol": item.symbol, "name": item.name, "market": item.market} for item in universe),
            "brief": _brief(candidates[symbol], focus=focus, question=question, portfolio=portfolio),
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))


def _rules(body: Mapping[str, object]) -> ScreenRules:
    return ScreenRules(
        body.get("revenue_growth_min", "12"),
        body.get("gross_margin_min", "35"),
        body.get("net_debt_ebitda_max", "2"),
        body.get("coverage_min", "60"),
    )


def screening_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        _portfolio_data, failure = _portfolio(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        rules = _rules(body)
        rows = run_screen(synthetic_universe(), rules, market=body.get("market", "all"))
        return ApiResponse(200, data={
            **_flags(),
            "rules": {
                "market": str(body.get("market", "all")).upper(),
                "revenue_growth_min": _decimal(rules.revenue_growth_min),
                "gross_margin_min": _decimal(rules.gross_margin_min),
                "net_debt_ebitda_max": _decimal(rules.net_debt_ebitda_max),
                "coverage_min": _decimal(rules.coverage_min),
            },
            "counts": {status: sum(row.status == status for row in rows) for status in ("matched", "needs_evidence", "excluded")},
            "rows": tuple({
                "symbol": row.symbol,
                "name": row.name,
                "market": row.market,
                "status": row.status,
                "reasons": row.reasons,
                "missing_keys": row.missing_keys,
                "coverage_percent": _decimal(row.coverage_percent),
                "revenue_growth": None if row.revenue_growth is None else str(row.revenue_growth),
                "gross_margin": None if row.gross_margin is None else str(row.gross_margin),
                "net_debt_ebitda": None if row.net_debt_ebitda is None else str(row.net_debt_ebitda),
            } for row in rows),
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))


def batch_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        _portfolio_data, failure = _portfolio(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        universe = synthetic_universe()
        symbols = body.get("symbols", ["ALPH", "BETA", "GAMMA"])
        rows = compare_research(universe, symbols)
        return ApiResponse(200, data={
            **_flags(),
            "symbols": tuple({"symbol": item.symbol, "name": item.name, "market": item.market} for item in universe),
            "rows": tuple({
                "symbol": row.symbol,
                "name": row.name,
                "market": row.market,
                "coverage": {"available": row.coverage_count, "total": row.coverage_total, "percent": _decimal(row.coverage_percent)},
                "revenue_growth": row.revenue_growth,
                "gross_margin": row.gross_margin,
                "net_debt_ebitda": row.net_debt_ebitda,
                "gaps": row.gaps,
                "review_priority": row.review_priority,
            } for row in rows),
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))
