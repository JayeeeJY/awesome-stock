"""Transparent process trends over explicit decision-review records."""

from dataclasses import dataclass

from .review import DecisionReview, EvolveValidationError


@dataclass(frozen=True)
class TrendMetric:
    key: str
    label: str
    passed: int
    total: int
    missing: int


@dataclass(frozen=True)
class TrendCell:
    record_id: str
    status: str
    detail: str


@dataclass(frozen=True)
class TrendRow:
    key: str
    label: str
    cells: tuple[TrendCell, ...]


@dataclass(frozen=True)
class ReviewPattern:
    statement: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvolveTrends:
    metrics: tuple[TrendMetric, ...]
    matrix: tuple[TrendRow, ...]
    patterns: tuple[ReviewPattern, ...]
    actions: tuple[str, ...]


def build_trends(records: tuple[DecisionReview, ...]) -> EvolveTrends:
    records = tuple(records)
    if not records:
        raise EvolveValidationError("trend window cannot be empty")
    keys = ("plan_adherence", "review_timing", "counter_evidence", "outcome_known")
    labels = {"plan_adherence": "计划遵守", "review_timing": "按期复核", "counter_evidence": "证据完整", "outcome_known": "结果已知"}
    metrics, matrix = [], []
    for key in keys:
        dimensions = tuple(record.dimension(key) for record in records)
        metrics.append(TrendMetric(key, labels[key], sum(item.status == "pass" for item in dimensions), len(records), sum(item.status == "missing" for item in dimensions)))
        matrix.append(TrendRow(key, labels[key], tuple(TrendCell(record.record_id, dimension.status, dimension.detail) for record, dimension in zip(records, dimensions))))
    missing_evidence = tuple(record.record_id for record in records if record.dimension("counter_evidence").status == "missing")
    deviations = tuple(record.record_id for record in records if record.dimension("plan_adherence").status == "deviated")
    patterns = (
        ReviewPattern(f"反方证据在 {len(missing_evidence)}/{len(records)} 次决策中不完整。", missing_evidence),
        ReviewPattern(f"计划偏离在 {len(deviations)}/{len(records)} 次决策中出现。", deviations),
    )
    return EvolveTrends(
        tuple(metrics), tuple(matrix), patterns,
        ("下次形成结论前，先补齐至少一条反方证据。", "仓位偏离计划上限时，同步记录原因和复核时间。"),
    )
