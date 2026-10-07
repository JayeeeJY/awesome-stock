"""Decision review records that separate process quality from short-term outcome."""

from dataclasses import dataclass


class EvolveValidationError(ValueError):
    """Raised when an Evolve projection request is outside the explicit demo contract."""

    code = "invalid_evolve_input"


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvolveValidationError(f"{field} is required")
    return value.strip()


@dataclass(frozen=True)
class ReviewDimension:
    key: str
    label: str
    status: str
    detail: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _required_text(self.key, "dimension key"))
        object.__setattr__(self, "label", _required_text(self.label, "dimension label"))
        object.__setattr__(self, "detail", _required_text(self.detail, "dimension detail"))
        if self.status not in {"pass", "deviated", "missing"}:
            raise EvolveValidationError("dimension status is invalid")


@dataclass(frozen=True)
class CandidateRule:
    rule_id: str
    statement: str
    trigger: str
    intended_effect: str
    evidence_ids: tuple[str, ...]
    confirmation_status: str = "pending_human_confirmation"

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_text(self.rule_id, "rule id"))
        object.__setattr__(self, "statement", _required_text(self.statement, "rule statement"))
        object.__setattr__(self, "trigger", _required_text(self.trigger, "rule trigger"))
        object.__setattr__(self, "intended_effect", _required_text(self.intended_effect, "rule effect"))
        evidence_ids = tuple(self.evidence_ids)
        if not evidence_ids or not all(isinstance(item, str) and item for item in evidence_ids):
            raise EvolveValidationError("candidate rule requires evidence records")
        if self.confirmation_status != "pending_human_confirmation":
            raise EvolveValidationError("Community rules must remain pending human confirmation")
        object.__setattr__(self, "evidence_ids", evidence_ids)


@dataclass(frozen=True)
class DecisionReview:
    record_id: str
    decided_at: str
    review_due_at: str
    reviewed_at: str | None
    symbol: str
    name: str
    original_thesis: str
    planned_action: str
    actual_action: str
    outcome_direction: str
    outcome_summary: str | None
    dimensions: tuple[ReviewDimension, ...]
    process_summary: str
    next_change: str
    candidate_rule_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("record_id", "decided_at", "review_due_at", "symbol", "name", "original_thesis", "planned_action", "actual_action", "process_summary", "next_change"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        if self.outcome_direction not in {"favorable", "unfavorable", "unknown"}:
            raise EvolveValidationError("outcome direction is invalid")
        if self.outcome_direction == "unknown":
            if self.outcome_summary is not None:
                raise EvolveValidationError("unknown outcome must not carry an invented summary")
        else:
            object.__setattr__(self, "outcome_summary", _required_text(self.outcome_summary, "outcome summary"))
        dimensions = tuple(self.dimensions)
        expected = {"plan_adherence", "counter_evidence", "review_timing", "outcome_known"}
        if {item.key for item in dimensions} != expected or len(dimensions) != len(expected):
            raise EvolveValidationError("review dimensions are incomplete or duplicated")
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "candidate_rule_ids", tuple(self.candidate_rule_ids))

    def dimension(self, key: str) -> ReviewDimension:
        match = next((item for item in self.dimensions if item.key == key), None)
        if match is None:
            raise EvolveValidationError("review dimension does not exist")
        return match


@dataclass(frozen=True)
class ReviewLedger:
    records: tuple[DecisionReview, ...]
    rules: tuple[CandidateRule, ...]

    def __post_init__(self) -> None:
        records, rules = tuple(self.records), tuple(self.rules)
        if not records or len({item.record_id for item in records}) != len(records):
            raise EvolveValidationError("review record ids must be unique")
        if len({item.rule_id for item in rules}) != len(rules):
            raise EvolveValidationError("candidate rule ids must be unique")
        record_ids, rule_ids = {item.record_id for item in records}, {item.rule_id for item in rules}
        if any(set(rule.evidence_ids) - record_ids for rule in rules):
            raise EvolveValidationError("candidate rule references an unknown record")
        if any(set(record.candidate_rule_ids) - rule_ids for record in records):
            raise EvolveValidationError("review references an unknown candidate rule")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "rules", rules)

    def filtered(self, value: object) -> tuple[DecisionReview, ...]:
        key = str(value or "all")
        if key == "all":
            return self.records
        if key == "reviewable":
            return tuple(item for item in self.records if item.outcome_direction != "unknown")
        if key == "missing_result":
            return tuple(item for item in self.records if item.outcome_direction == "unknown")
        raise EvolveValidationError("review filter is invalid")

    def record(self, record_id: object) -> DecisionReview:
        match = next((item for item in self.records if item.record_id == record_id), None)
        if match is None:
            raise EvolveValidationError("review record does not exist")
        return match

    def rule(self, rule_id: object) -> CandidateRule:
        match = next((item for item in self.rules if item.rule_id == rule_id), None)
        if match is None:
            raise EvolveValidationError("candidate rule does not exist")
        return match

    def preview_rule(self, rule_id: object) -> dict[str, object]:
        rule = self.rule(rule_id)
        return {
            "rule_id": rule.rule_id,
            "status": rule.confirmation_status,
            "supported_records": rule.evidence_ids,
            "requirements": ("逐条核对适用条件", "确认不会覆盖既有纪律", "由用户明确启用"),
            "persisted": False,
            "activated": False,
        }


def _dimensions(plan: str, evidence: str, timing: str, outcome: str) -> tuple[ReviewDimension, ...]:
    details = {
        "plan_adherence": {"pass": "执行与原计划一致", "deviated": "实际执行偏离原计划", "missing": "执行事实待补"},
        "counter_evidence": {"pass": "反方证据已记录", "deviated": "反方证据被忽略", "missing": "反方证据待补"},
        "review_timing": {"pass": "在计划时间内完成复核", "deviated": "复核晚于计划时间", "missing": "复核时间待补"},
        "outcome_known": {"pass": "结果事实已记录", "deviated": "结果口径与计划不一致", "missing": "结果尚未形成"},
    }
    labels = {"plan_adherence": "计划遵守", "counter_evidence": "反方证据", "review_timing": "复核时效", "outcome_known": "结果已知"}
    values = {"plan_adherence": plan, "counter_evidence": evidence, "review_timing": timing, "outcome_known": outcome}
    return tuple(ReviewDimension(key, labels[key], status, details[key][status]) for key, status in values.items())


def build_review_ledger() -> ReviewLedger:
    """Return three fixed records that demonstrate review semantics without user history."""

    rules = (
        CandidateRule("RULE-01", "仓位超过原计划上限时，必须记录偏离原因后再继续执行。", "实际仓位超过原 Decision 上限", "让执行偏离可解释、可复核", ("EV-002",)),
        CandidateRule("RULE-02", "反方证据未完成时，先补证再形成结论或复核。", "反方证据状态为待补", "减少只验证原有观点的倾向", ("EV-002", "EV-003")),
    )
    records = (
        DecisionReview(
            "EV-001", "2026-08-06", "2026-08-20", "2026-08-19", "ALPH", "Alpha Systems",
            "增长仍由核心产品续费支持，但需要验证现金流同步改善。", "维持观察仓位，不在结果公布前追加。",
            "按计划维持观察仓位。", "favorable", "观察期内收入与现金流方向一致，价格变化为正。",
            _dimensions("pass", "pass", "pass", "pass"), "过程完整；结果与判断同向，但只记录事实，不归因于能力。",
            "继续按既定周期复核现金流，不提高仓位上限。", (),
        ),
        DecisionReview(
            "EV-002", "2026-08-09", "2026-08-18", "2026-08-22", "BETA", "Beta Works",
            "毛利率企稳可能支持修复，但客户集中度仍需验证。", "仓位不超过组合的 12%，补齐客户集中度后再调整。",
            "在证据未补齐时将仓位提高至 15%。", "favorable", "短期价格上涨，组合贡献为正。",
            _dimensions("deviated", "missing", "deviated", "pass"), "结果良好不等于过程合格；执行偏离且反方证据缺失。",
            "以后先记录偏离理由并补齐反方证据，再改变仓位上限。", ("RULE-01", "RULE-02"),
        ),
        DecisionReview(
            "EV-003", "2026-08-17", "2026-08-31", "2026-08-30", "GAMMA", "Gamma Labs",
            "研发投入与增长较强，但持续性和估值约束尚未验证。", "只建立观察记录，两周后复核，不执行交易。",
            "按计划保持观察，未执行交易。", "unknown", None,
            _dimensions("pass", "missing", "pass", "missing"), "过程按计划完成；结果尚未形成，不能按零收益处理。",
            "在下次复核前补齐竞争与估值反方证据。", ("RULE-02",),
        ),
    )
    return ReviewLedger(records, rules)
