"""Authenticated synthetic projections for Evolve review and process trends."""

from typing import Mapping

from awesome_stock.api.contracts import ApiResponse, problem_from_exception
from awesome_stock.evolve.review import CandidateRule, DecisionReview, EvolveValidationError, ReviewDimension, build_review_ledger
from awesome_stock.evolve.trends import build_trends


def _flags() -> dict[str, object]:
    return {
        "mode": "synthetic_preview",
        "persistence": False,
        "ai_generated": False,
        "external_provider": False,
        "score_generated": False,
    }


def _authenticated(runtime, access_token: str, request_id: object) -> ApiResponse | None:
    response = runtime.portfolio(access_token, request_id=request_id)
    return response if response.problem is not None else None


def _dimension(item: ReviewDimension) -> dict[str, object]:
    return {"key": item.key, "label": item.label, "status": item.status, "detail": item.detail}


def _rule(item: CandidateRule) -> dict[str, object]:
    return {
        "rule_id": item.rule_id,
        "statement": item.statement,
        "trigger": item.trigger,
        "intended_effect": item.intended_effect,
        "evidence_ids": item.evidence_ids,
        "confirmation_status": item.confirmation_status,
    }


def _record(item: DecisionReview) -> dict[str, object]:
    labels = {"favorable": "结果为正", "unfavorable": "结果为负", "unknown": "结果待补"}
    return {
        "record_id": item.record_id,
        "decided_at": item.decided_at,
        "review_due_at": item.review_due_at,
        "reviewed_at": item.reviewed_at,
        "symbol": item.symbol,
        "name": item.name,
        "original_thesis": item.original_thesis,
        "planned_action": item.planned_action,
        "actual_action": item.actual_action,
        "outcome": {"direction": item.outcome_direction, "label": labels[item.outcome_direction], "summary": item.outcome_summary},
        "dimensions": tuple(_dimension(dimension) for dimension in item.dimensions),
        "process_summary": item.process_summary,
        "next_change": item.next_change,
        "candidate_rule_ids": item.candidate_rule_ids,
    }


def reviews_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        failure = _authenticated(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        ledger = build_review_ledger()
        review_filter = body.get("filter", "all")
        records = ledger.filtered(review_filter)
        selected_id = body.get("record_id", records[0].record_id if records else None)
        selected = ledger.record(selected_id)
        if selected not in records:
            raise EvolveValidationError("selected record is outside the active filter")
        return ApiResponse(200, data={
            **_flags(),
            "filter": str(review_filter),
            "filters": ({"value": "all", "label": "全部记录"}, {"value": "reviewable", "label": "可复盘"}, {"value": "missing_result", "label": "待补结果"}),
            "summary": {
                "total": len(ledger.records),
                "reviewable": len(ledger.filtered("reviewable")),
                "missing_result": len(ledger.filtered("missing_result")),
                "candidate_rules": len(ledger.rules),
            },
            "records": tuple(_record(item) for item in records),
            "selected": _record(selected),
            "rules": tuple(_rule(item) for item in ledger.rules),
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))


def _window_records(window: object) -> tuple[str, tuple[DecisionReview, ...]]:
    ledger = build_review_ledger()
    key = str(window or "latest_3")
    if key == "latest_3":
        return key, ledger.records
    if key == "latest_2":
        return key, ledger.records[-2:]
    raise EvolveValidationError("trend window is invalid")


def trends_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        failure = _authenticated(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        window, records = _window_records(body.get("window", "latest_3"))
        trends = build_trends(records)
        return ApiResponse(200, data={
            **_flags(),
            "window": window,
            "windows": ({"value": "latest_3", "label": "最近 3 次合成决策"}, {"value": "latest_2", "label": "最近 2 次合成决策"}),
            "records": tuple({"record_id": item.record_id, "symbol": item.symbol, "decided_at": item.decided_at} for item in records),
            "metrics": tuple({"key": item.key, "label": item.label, "passed": item.passed, "total": item.total, "missing": item.missing} for item in trends.metrics),
            "matrix": tuple({"key": row.key, "label": row.label, "cells": tuple({"record_id": cell.record_id, "status": cell.status, "detail": cell.detail} for cell in row.cells)} for row in trends.matrix),
            "patterns": tuple({"statement": item.statement, "evidence_ids": item.evidence_ids} for item in trends.patterns),
            "actions": trends.actions,
            "methodology": "每个比例均以当前所选合成 Decision 记录为分母；缺失保持为缺失，不计作通过，也不生成综合评分。",
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))


def rule_preview_response(runtime, *, access_token: str, values: object = None, request_id: object = None) -> ApiResponse:
    try:
        failure = _authenticated(runtime, access_token, request_id)
        if failure is not None:
            return failure
        body = values if isinstance(values, Mapping) else {}
        preview = build_review_ledger().preview_rule(body.get("rule_id"))
        return ApiResponse(200, data={**_flags(), "preview": preview})
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))
