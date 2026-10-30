"""Pydantic request/response schemas for the SchoolSmartEYE API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Health ────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"] = "ok"


# ── Dashboard ─────────────────────────────────────────────────────────────────


class HeatmapCellSchema(BaseModel):
    x: int
    y: int
    time_slot: str
    risk_intensity: float = Field(ge=0.0, le=1.0)
    reason: str
    label: str


class AlertFeedItemSchema(BaseModel):
    id: str
    title: str
    message: str
    severity: Literal["critical", "warning", "stable"]
    stream: Literal["coherence", "anomaly", "density"]
    computed_at: str


class DashboardSummaryResponse(BaseModel):
    schoolName: str
    ssi: int = Field(ge=0, le=100)
    benchmark: int
    websocketStatus: Literal["connected", "reconnecting", "offline"]


class DashboardAlertsResponse(BaseModel):
    alerts: list[AlertFeedItemSchema]


class DashboardHeatmapResponse(BaseModel):
    location_id: str
    availableTimeSlots: list[str]
    cells: list[HeatmapCellSchema]


class DashboardSnapshotResponse(BaseModel):
    schoolName: str
    ssi: int = Field(ge=0, le=100)
    benchmark: int
    websocketStatus: Literal["connected", "reconnecting", "offline"]
    liveAlerts: list[AlertFeedItemSchema]
    heatmapCells: list[HeatmapCellSchema]
    availableTimeSlots: list[str]
    fetchedFromBackend: bool


# ── SSI ───────────────────────────────────────────────────────────────────────


class SSIInputsSchema(BaseModel):
    anomaly_coefficient: float = Field(ge=0.0, le=1.0)
    coherence_score: float = Field(ge=0.0, le=1.0)
    attendance_discrepancy: float = Field(ge=0.0, le=1.0)
    predictive_risk_level: float = Field(ge=0.0)


class DensityForecastSchema(BaseModel):
    location: str
    predicted_density: float = Field(ge=0.0, le=1.0)
    safety_threshold: float
    risk_level: str
    warning: bool
    model: str


class SSIWeightsSchema(BaseModel):
    w1_anomaly: float
    w2_coherence: float
    w3_attendance: float
    w4_density: float


class SSILiveResponse(BaseModel):
    ssi: float
    benchmark: int
    status: Literal["above_benchmark", "below_benchmark"]
    inputs: SSIInputsSchema
    density_forecast: DensityForecastSchema
    weights: SSIWeightsSchema
    computed_at: str


class SSIHistoryPointSchema(BaseModel):
    day: int
    ssi: float


class SSIHistoryResponse(BaseModel):
    school: str
    period: str
    benchmark: int
    scores: list[SSIHistoryPointSchema]
    average: float | None
    trend: Literal["improving", "stable", "declining", "insufficient_data"]


# ── Units ─────────────────────────────────────────────────────────────────────


class UnitInfoSchema(BaseModel):
    unit_id: int
    name: str
    category: str
    status: Literal["active", "degraded", "offline"]


# ── Analytics ─────────────────────────────────────────────────────────────────


class AnalyticsMetricResponse(BaseModel):
    value: float | int | str | None = None
    status: Literal["live", "stale", "unavailable", "demo"]
    source: str | None = None
    observed_at: str | None = None


class AnalyticsOverviewResponse(BaseModel):
    data_status: Literal["live", "partial", "unavailable", "demo"]
    data_notice: str
    generated_at: str
    metrics: dict[str, AnalyticsMetricResponse]
    attendance_rate: float | None = None
    total_students: int | None = None
    active_cameras: int | None = None
    total_units: int | None = None
    incidents_today: int | None = None
    incidents_week: int | None = None
    avg_crowd_density: float | None = None
    peak_density_zone: str | None = None
    uptime_percent: float | None = None
    alerts_resolved_today: int | None = None
    patrol_efficiency: float | None = None
    compliance_score: float | None = None


# ── Reports ───────────────────────────────────────────────────────────────────


class ReportItemSchema(BaseModel):
    id: str
    title: str
    type: Literal["operational", "analytical", "supervisory", "ministerial"]
    period: str
    generated_at: str
    status: Literal["ready", "generating", "scheduled"]


class IncidentDaySchema(BaseModel):
    day: str
    count: int


class RiskZoneSchema(BaseModel):
    zone: str
    risk: float
    incidents: int


class AttendanceWeekSchema(BaseModel):
    week: str
    rate: float


class IncidentTypeSchema(BaseModel):
    type: str
    count: int
    color: str


class ReportStatsResponse(BaseModel):
    weekly_incidents_by_day: list[IncidentDaySchema]
    top_risk_zones: list[RiskZoneSchema]
    attendance_by_week: list[AttendanceWeekSchema]
    incident_types: list[IncidentTypeSchema]


# ── Parent Portal ─────────────────────────────────────────────────────────────


class PortalNotificationSchema(BaseModel):
    id: str
    type: Literal["attendance", "safety", "info"]
    message: str
    time: str
    read: bool


class WeeklyAttendanceDaySchema(BaseModel):
    day: str
    present: bool


class StudentPortalResponse(BaseModel):
    name: str
    grade: str
    student_id: str
    photo_initial: str
    attendance_today: Literal["present", "absent", "late"]
    arrival_time: str
    last_seen_zone: str
    dismissal_status: str
    safety_status: Literal["safe", "warning", "unknown"]
    attendance_streak: int
    monthly_attendance: float
    notifications: list[PortalNotificationSchema]
    weekly_attendance: list[WeeklyAttendanceDaySchema]
