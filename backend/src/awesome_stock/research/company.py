"""Deterministic company brief built from an explicit evidence ledger."""

from dataclasses import dataclass

from .evidence import EvidenceLedger, ResearchValidationError


FOCUS_DIMENSIONS = {
    "overview": None,
    "growth": "增长",
    "quality": "质量",
    "valuation": "估值",
    "risk": "风险",
}
ACTION_COPY = {
    "net_debt_ebitda": ("补齐杠杆事实", "确认净债务与 EBITDA 口径，避免在负债事实缺失时判断财务韧性。"),
    "customer_concentration": ("补齐客户集中度", "确认前五大客户占比及变化，核对收入增长是否依赖单一客户。"),
    "revenue_growth": ("补齐增长事实", "核对可比口径营收与增长来源。"),
    "gross_margin": ("补齐盈利质量", "核对毛利率口径和变化原因。"),
}


@dataclass(frozen=True)
class ResearchAction:
    key: str
    title: str
    detail: str


@dataclass(frozen=True)
class ResearchBrief:
    symbol: str
    name: str
    focus: str
    question: str
    conclusion_code: str
    conclusion_title: str
    summary: str
    evidence: EvidenceLedger
    actions: tuple[ResearchAction, ...]
    ai_generated: bool = False


def _text(value: object, field: str, *, maximum: int) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    if not normalized or len(normalized) > maximum:
        raise ResearchValidationError(f"{field} is invalid")
    return normalized


def _ordered(ledger: EvidenceLedger, focus: str) -> EvidenceLedger:
    dimension = FOCUS_DIMENSIONS[focus]
    if dimension is None:
        return ledger
    return EvidenceLedger(tuple(sorted(ledger.facts, key=lambda fact: fact.dimension != dimension)))


def _display_value(ledger: EvidenceLedger, key: str) -> str | None:
    fact = ledger.fact(key)
    return None if fact is None or fact.value is None else str(fact.value.normalize())


def create_research_brief(
    symbol: object,
    name: object,
    evidence: EvidenceLedger,
    *,
    focus: object = "overview",
    question: object = "哪些事实支持当前增长，哪些关键证据仍然缺失？",
) -> ResearchBrief:
    normalized_symbol = _text(symbol, "symbol", maximum=12).upper()
    normalized_name = _text(name, "name", maximum=80)
    normalized_focus = focus.strip().lower() if isinstance(focus, str) else ""
    if normalized_focus not in FOCUS_DIMENSIONS:
        raise ResearchValidationError("focus is invalid")
    normalized_question = _text(question, "question", maximum=160)
    ordered = _ordered(evidence, normalized_focus)
    incomplete = bool(evidence.missing_keys)
    conclusion_code = "evidence_incomplete" if incomplete else "ready_for_human_review"
    conclusion_title = "证据不足，保持观察" if incomplete else "证据较完整，等待人工判断"
    growth = _display_value(evidence, "revenue_growth")
    margin = _display_value(evidence, "gross_margin")
    known = []
    if growth is not None:
        known.append(f"合成样本营收增长为 {growth}%")
    if margin is not None:
        known.append(f"毛利率为 {margin}%")
    missing_labels = [fact.statement for fact in evidence.facts if fact.status == "missing"]
    summary = "；".join(known) + "。"
    if missing_labels:
        summary += f"但{'、'.join(missing_labels)}仍为待补事实，当前材料不足以形成投资判断。"
    else:
        summary += "当前证据可进入人工假设复核，但系统不提供买卖结论。"
    actions = tuple(
        ResearchAction(key, *(ACTION_COPY.get(key) or (f"补齐{fact.statement}", "确认定义、口径与观察时间。")))
        for key in evidence.missing_keys
        for fact in (evidence.fact(key),)
    )
    if not actions:
        actions = (ResearchAction("review_assumptions", "复核关键假设", "由用户核对事实口径、反例和风险边界后再决定下一步。"),)
    return ResearchBrief(
        normalized_symbol,
        normalized_name,
        normalized_focus,
        normalized_question,
        conclusion_code,
        conclusion_title,
        summary,
        ordered,
        actions,
    )
