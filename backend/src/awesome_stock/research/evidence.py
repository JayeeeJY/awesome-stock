"""Evidence types that preserve missing facts instead of inventing values."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class ResearchValidationError(ValueError):
    """Raised when research input cannot support a trustworthy projection."""

    code = "invalid_research_input"


def as_decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool):
        raise ResearchValidationError(f"{field} must be a finite number")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ResearchValidationError(f"{field} must be a finite number") from exc
    if not result.is_finite():
        raise ResearchValidationError(f"{field} must be a finite number")
    return result


@dataclass(frozen=True)
class EvidenceFact:
    key: str
    dimension: str
    statement: str
    value: Decimal | str | int | float | None
    unit: str
    status: str
    observed_at: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key or not self.key.replace("_", "").isalnum():
            raise ResearchValidationError("evidence key is invalid")
        if not isinstance(self.dimension, str) or not self.dimension.strip():
            raise ResearchValidationError("evidence dimension is required")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ResearchValidationError("evidence statement is required")
        if self.status not in {"verified", "missing", "stale"}:
            raise ResearchValidationError("evidence status is invalid")
        if self.status == "missing":
            if self.value is not None or self.observed_at is not None:
                raise ResearchValidationError("missing evidence cannot contain a value or observation")
            normalized = None
        else:
            if self.value is None or not isinstance(self.observed_at, str) or not self.observed_at.strip():
                raise ResearchValidationError("available evidence requires a value and observation")
            normalized = as_decimal(self.value, self.key)
        object.__setattr__(self, "value", normalized)
        object.__setattr__(self, "dimension", self.dimension.strip())
        object.__setattr__(self, "statement", self.statement.strip())

    @property
    def available(self) -> bool:
        return self.status in {"verified", "stale"}


@dataclass(frozen=True)
class EvidenceLedger:
    facts: tuple[EvidenceFact, ...]

    def __post_init__(self) -> None:
        facts = tuple(self.facts)
        if not facts:
            raise ResearchValidationError("evidence ledger cannot be empty")
        if not all(isinstance(fact, EvidenceFact) for fact in facts):
            raise ResearchValidationError("ledger items must be evidence facts")
        keys = [fact.key for fact in facts]
        if len(set(keys)) != len(keys):
            raise ResearchValidationError("evidence keys must be unique")
        object.__setattr__(self, "facts", facts)

    @property
    def coverage_count(self) -> int:
        return sum(fact.available for fact in self.facts)

    @property
    def total_count(self) -> int:
        return len(self.facts)

    @property
    def coverage_percent(self) -> Decimal:
        return (Decimal(self.coverage_count) / Decimal(self.total_count) * Decimal("100")).quantize(Decimal("0.01"))

    @property
    def missing_keys(self) -> tuple[str, ...]:
        return tuple(fact.key for fact in self.facts if fact.status == "missing")

    def fact(self, key: str) -> EvidenceFact | None:
        return next((fact for fact in self.facts if fact.key == key), None)
