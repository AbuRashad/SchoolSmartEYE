"""Compatibility facade for SchoolSmartEYE's first-party native intelligence."""
from typing import Any
from app.services.native_intelligence_engine import analyze_specialist

AGENT_ROLES = {
    "analytics": "Aggregate trend and data-quality analysis",
    "safety": "School safety signal analysis",
    "academic": "School-wide academic analysis",
    "operations": "Operational reliability analysis",
    "evidence": "Evidence sufficiency review",
    "ethics_review": "Privacy and cross-agent review",
}


def ai_enabled() -> bool:
    return True


def generate_specialist_analysis(agent_name: str, metrics: dict[str, int | float], fallback_summary: str,
                                 prior_analyses: list[dict[str, Any]] | None = None):
    if agent_name not in AGENT_ROLES:
        return None, False, None
    result = analyze_specialist(agent_name, metrics, prior_analyses or [])
    return (result, True, "native") if result else (None, False, None)


def generate_specialist_summary(agent_name: str, metrics: dict[str, int | float], fallback_summary: str):
    result, used, _provider = generate_specialist_analysis(agent_name, metrics, fallback_summary)
    return (result["summary"], True) if used and result else (fallback_summary, False)
