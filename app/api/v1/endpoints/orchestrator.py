"""Authenticated API for the bounded specialist-agent orchestrator."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from app.api.deps import get_current_school_id, require_principal
from app.api.v1.endpoints.analytics import analytics_overview
from app.db.models import User
from app.db.session import get_db
from sqlalchemy.orm import Session
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


class AgentStage(BaseModel):
    name: Literal["analytics", "safety", "academic", "operations", "evidence", "ethics_review"]
    kind: Literal["deterministic", "llm_assisted"]
    status: Literal["completed", "limited"]
    agent_role: str
    provider: Literal["deterministic", "ollama"]
    analysis_status: Literal["ai_completed", "deterministic_fallback"]
    summary: str | None = None
    advisory_summary: str | None = None
    analysis: AgentAnalysis | None = None
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reviewed_stages: list[str] = Field(default_factory=list)


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
    reviewed_agents: list[str] = Field(default_factory=list)


class OrchestrateResponse(BaseModel):
    request_id: str
    status: Literal["completed", "limited"]
    task: str
    provider: Literal["deterministic", "ollama"]
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
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> OrchestrateResponse:
    """Coordinate specialist agents over allowlisted aggregate metrics.

    Principal and Ministry roles may call this endpoint. No student-level records
    are fetched. AI analyses are advisory and cannot alter deterministic findings.
    """
    try:
        analytics = analytics_overview(db, school_id)
        daily = analytics["attendance"]["daily"]
        latest_attendance = daily[-1] if daily else {}
        result = run_orchestration(
            payload.task,
            {
                "total_students": analytics["students"]["active"],
                "active_cameras": analytics["cameras"]["active"],
                "incidents_today": analytics["incidents"]["last_30_days_by_severity"].get("today", 0),
                "attendance_rate": latest_attendance.get("attendance_rate"),
                "data_status": "unknown",
                "data_notice": (
                    "School-scoped database records are isolated, but per-record demo/live provenance "
                    "is not yet labelled. Verify source and freshness before operational decisions."
                ),
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return OrchestrateResponse.model_validate(result)
