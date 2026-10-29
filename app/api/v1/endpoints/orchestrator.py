"""Authenticated API for the bounded agent orchestrator."""
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


class AgentStage(BaseModel):
    name: Literal["analytics", "safety", "education", "ethics_review"]
    kind: Literal["deterministic"]
    status: Literal["completed", "limited"]
    summary: str | None = None
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OrchestrateResponse(BaseModel):
    request_id: str
    status: Literal["completed", "limited"]
    task: str
    provider: Literal["deterministic"]
    stages: list[AgentStage]
    evidence: list[EvidenceItem]
    confidence: Literal["low", "moderate"]
    requires_human_review: bool
    autonomous_action_taken: Literal[False]


@router.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate_agents(
    payload: OrchestrateRequest,
    _user: User = Depends(require_principal),
) -> OrchestrateResponse:
    """Coordinate deterministic specialists over allowlisted aggregate metrics.

    Principal and Ministry roles may call this endpoint. No student records are
    fetched, and no external LLM provider is called in this initial version.
    """
    try:
        result = run_orchestration(payload.task, analytics_overview())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return OrchestrateResponse.model_validate(result)
