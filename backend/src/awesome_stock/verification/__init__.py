"""Synthetic verification and release-safety contracts."""

from .shadow import (
    ComparisonField,
    ShadowCase,
    ShadowReport,
    SwitchGate,
    SwitchReadiness,
    build_switch_readiness,
    compare_fields,
    run_shadow_comparison,
)

__all__ = [
    "ComparisonField",
    "ShadowCase",
    "ShadowReport",
    "SwitchGate",
    "SwitchReadiness",
    "build_switch_readiness",
    "compare_fields",
    "run_shadow_comparison",
]
