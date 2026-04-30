"""Unit 15: Pedagogical Behavioral Intelligence Agent — وحدة الذكاء السلوكي التربوي.

Integrates pose-based engagement scoring, Egyptian Arabic audio context
analysis, long-term per-student behavioral memory, and a continuous
self-evaluation loop driven by teacher feedback.
"""
from __future__ import annotations

from app.services.pedagogical_agent import (
    PedagogicalAgentService,
    StudentEngagementSummary,
    default_score_for,
)
from app.models import EngagementSnapshot, EngagementState, AgentFeedback

UNIT_15_NAME = "Pedagogical Behavioral Intelligence Agent"

__all__ = [
    "UNIT_15_NAME",
    "PedagogicalAgentService",
    "StudentEngagementSummary",
    "EngagementSnapshot",
    "EngagementState",
    "AgentFeedback",
    "default_score_for",
]
