"""Authenticated API for the bounded specialist-agent orchestrator."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from app.api.deps import require_principal
from app.api.v1.endpoints.analytics import analytics_overview
from app.db.models import User
from app.services.agent_orchestrator import run_orchestration

router = APIRouter(prefix="/agent", tags=["agent-orchestrator"])


class OrchestrateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str = Field(min_length=1, max_length=500)


class EvidenceItem(BaseModel):
    source: str
    description: str
    value: int | float


class AgentAnalysis(BaseModel):
    summary: str
    observations: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ProviderAttempt(BaseModel):
    """One attempt against one configured provider, for diagnostics."""
    provider: str
    outcome: Literal[
        "ai_completed", "timeout", "auth_failed", "rate_limited",
        "provider_error", "http_error", "connection_failed", "invalid_response",
    ]
    latency_ms: int = 0
    http_status: int | None = None


class AgentStage(BaseModel):
    name: Literal["analytics", "safety", "academic", "operations", "evidence", "ethics_review"]
    kind: Literal["deterministic", "llm_assisted"]
    status: Literal["completed", "limited"]
    agent_role: str
    provider: Literal["deterministic", "cloud", "local", "hybrid"]
    analysis_status: Literal["ai_completed", "deterministic_fallback"]
    summary: str | None = None
    advisory_summary: str | None = None
    analysis: AgentAnalysis | None = None
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reviewed_stages: list[str] = Field(default_factory=list)
    # Threshold provenance emitted by the deterministic agents (policy layer).
    threshold_refs: list[str] = Field(default_factory=list)
    policy_version: str | None = None
    # Why this stage's model call succeeded or fell back.
    failure_reason: str | None = None
    latency_ms: int = 0
    attempts: list[ProviderAttempt] = Field(default_factory=list)


class ReportFinding(BaseModel):
    stage: str
    type: Literal["flag", "recommendation", "warning"]
    text: str


class UnifiedReviewReport(BaseModel):
    title: str
    status: Literal["completed", "limited"]
    data_status: Literal["demo", "live", "unknown"]
    data_notice: str
    finding_count: int
    findings: list[ReportFinding]
    evidence_count: int
    limitations: list[str]
    ai_agent_count: int = 0
    ai_providers: list[Literal["cloud", "local"]] = Field(default_factory=list)
    # Distinct reasons the AI layer produced nothing, e.g. provider_disabled.
    fallback_reasons: list[str] = Field(default_factory=list)
    reviewed_agents: list[str] = Field(default_factory=list)


class OrchestrateResponse(BaseModel):
    request_id: str
    status: Literal["completed", "limited"]
    task: str
    provider: Literal["deterministic", "cloud", "local", "hybrid"]
    stages: list[AgentStage]
    evidence: list[EvidenceItem]
    report: UnifiedReviewReport
    confidence: Literal["low", "moderate"]
    requires_human_review: bool
    autonomous_action_taken: Literal[False]


@router.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate_agents(
    payload: OrchestrateRequest,
    _user: User = Depends(require_principal),
) -> OrchestrateResponse:
    """Coordinate specialist agents over allowlisted aggregate metrics.

    Principal and Ministry roles may call this endpoint. No student-level records
    are fetched. AI analyses are advisory and cannot alter deterministic findings.
    """
    try:
        result = run_orchestration(payload.task, analytics_overview())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return OrchestrateResponse.model_validate(result)
