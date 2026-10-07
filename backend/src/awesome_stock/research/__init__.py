"""Pure, deterministic research evidence and comparison primitives."""

from .batch import BatchComparisonRow, compare_research
from .company import ResearchAction, ResearchBrief, create_research_brief
from .evidence import EvidenceFact, EvidenceLedger, ResearchValidationError
from .screening import ScreenCandidate, ScreenResult, ScreenRules, run_screen

__all__ = (
    "BatchComparisonRow",
    "EvidenceFact",
    "EvidenceLedger",
    "ResearchAction",
    "ResearchBrief",
    "ResearchValidationError",
    "ScreenCandidate",
    "ScreenResult",
    "ScreenRules",
    "compare_research",
    "create_research_brief",
    "run_screen",
)
