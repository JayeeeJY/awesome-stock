"""Pure synthetic shadow comparison and conservative switch gates."""

from dataclasses import dataclass
from typing import Callable, Mapping

from awesome_stock.core.vectors import (
    evaluate_ledger_vector,
    evaluate_missingness_vector,
    evaluate_mixed_currency_vector,
)

from .spec_vectors import LEDGER_VECTORS, MISSINGNESS_VECTORS, MIXED_CURRENCY_VECTOR, VECTOR_COUNT


FIELD_STATES = frozenset({"match", "mismatch", "missing"})
GATE_STATES = frozenset({"passed", "pending", "blocked"})


@dataclass(frozen=True)
class ComparisonField:
    path: str
    expected: object
    actual: object
    status: str

    def __post_init__(self) -> None:
        if not self.path or self.status not in FIELD_STATES:
            raise ValueError("comparison field must have a path and known status")

    def as_dict(self) -> dict[str, object]:
        return {"path": self.path, "expected": self.expected, "actual": self.actual, "status": self.status}


@dataclass(frozen=True)
class ShadowCase:
    case_id: str
    category: str
    fields: tuple[ComparisonField, ...]

    def __post_init__(self) -> None:
        if not self.case_id or not self.category or not self.fields:
            raise ValueError("shadow case identity, category, and fields are required")
        if len({item.path for item in self.fields}) != len(self.fields):
            raise ValueError("shadow comparison field paths must be unique")

    @property
    def status(self) -> str:
        return "match" if all(item.status == "match" for item in self.fields) else "difference"

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "status": self.status,
            "fields": tuple(item.as_dict() for item in self.fields),
        }


@dataclass(frozen=True)
class ShadowReport:
    cases: tuple[ShadowCase, ...]

    def __post_init__(self) -> None:
        if len(self.cases) != VECTOR_COUNT:
            raise ValueError(f"shadow report requires exactly {VECTOR_COUNT} specification cases")
        if len({item.case_id for item in self.cases}) != len(self.cases):
            raise ValueError("shadow case identifiers must be unique")

    @property
    def matched_cases(self) -> int:
        return sum(item.status == "match" for item in self.cases)

    @property
    def difference_cases(self) -> int:
        return len(self.cases) - self.matched_cases

    @property
    def overall_status(self) -> str:
        return "matched" if self.difference_cases == 0 else "difference_found"

    def as_dict(self) -> dict[str, object]:
        return {
            "source": "approved_synthetic_specification",
            "overall_status": self.overall_status,
            "case_count": len(self.cases),
            "matched_cases": self.matched_cases,
            "difference_cases": self.difference_cases,
            "cases": tuple(item.as_dict() for item in self.cases),
        }


def compare_fields(expected: Mapping[str, object], actual: Mapping[str, object]) -> tuple[ComparisonField, ...]:
    """Compare required fields exactly while making absent output explicit."""

    result = []
    for path, expected_value in expected.items():
        if path not in actual:
            result.append(ComparisonField(path, expected_value, None, "missing"))
            continue
        actual_value = actual[path]
        state = "match" if actual_value == expected_value else "mismatch"
        result.append(ComparisonField(path, expected_value, actual_value, state))
    return tuple(result)


def run_shadow_comparison(
    *,
    ledger_evaluator: Callable[[Mapping[str, object]], Mapping[str, object]] = evaluate_ledger_vector,
    mixed_currency_evaluator: Callable[[Mapping[str, object]], Mapping[str, object]] = evaluate_mixed_currency_vector,
    missingness_evaluator: Callable[[Mapping[str, object]], Mapping[str, object]] = evaluate_missingness_vector,
) -> ShadowReport:
    """Run only approved synthetic expectations against the independent core."""

    cases = []
    for vector in LEDGER_VECTORS:
        cases.append(ShadowCase(vector["id"], "ledger", compare_fields(vector["expected"], ledger_evaluator(vector))))
    cases.append(
        ShadowCase(
            MIXED_CURRENCY_VECTOR["id"],
            "mixed_currency",
            compare_fields(MIXED_CURRENCY_VECTOR["expected"], mixed_currency_evaluator(MIXED_CURRENCY_VECTOR)),
        )
    )
    for vector in MISSINGNESS_VECTORS:
        cases.append(ShadowCase(vector["id"], "missingness", compare_fields(vector["expected"], missingness_evaluator(vector))))
    return ShadowReport(tuple(cases))


@dataclass(frozen=True)
class SwitchGate:
    key: str
    label: str
    state: str
    detail: str

    def __post_init__(self) -> None:
        if not self.key or not self.label or not self.detail or self.state not in GATE_STATES:
            raise ValueError("switch gate must contain a known, explicit state")

    def as_dict(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "state": self.state, "detail": self.detail}


@dataclass(frozen=True)
class SwitchReadiness:
    gates: tuple[SwitchGate, ...]
    switch_allowed: bool = False
    rollback_ready: bool = False
    write_path_changed: bool = False

    def __post_init__(self) -> None:
        if len(self.gates) != 6 or len({item.key for item in self.gates}) != 6:
            raise ValueError("switch readiness requires six unique gates")
        if self.switch_allowed or self.rollback_ready or self.write_path_changed:
            raise ValueError("F5-A cannot authorize a switch, rollback claim, or write-path change")

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": "hold",
            "switch_allowed": self.switch_allowed,
            "rollback_ready": self.rollback_ready,
            "write_path_changed": self.write_path_changed,
            "gates": tuple(item.as_dict() for item in self.gates),
        }


def build_switch_readiness(report: ShadowReport) -> SwitchReadiness:
    comparison_state = "passed" if report.overall_status == "matched" else "blocked"
    return SwitchReadiness(
        (
            SwitchGate("synthetic_shadow", "合成影子对照", comparison_state, f"{report.matched_cases}/{len(report.cases)} 组合成规范样例一致"),
            SwitchGate("real_read_only_reconciliation", "真实数据只读对照", "pending", "尚未获得用户专项授权，不连接真实数据"),
            SwitchGate("backup_restore", "备份恢复验证", "pending", "尚未进入真实迁移准备阶段"),
            SwitchGate("human_switch_confirmation", "人工切换确认", "pending", "必须由用户查看差异报告后单独确认"),
            SwitchGate("rollback_drill", "回退演练", "pending", "尚未对真实安装执行回退演练"),
            SwitchGate("write_path_approval", "写路径授权", "blocked", "F5-A 明确禁止修改真实写路径"),
        )
    )
