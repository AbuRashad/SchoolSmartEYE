"""Units overview endpoint — provides health and metadata for all 15 system units."""
from __future__ import annotations

from fastapi import APIRouter

from app.units.unit_01.module import UNIT_01_NAME, VideoCaptureUnit
from app.units.unit_02.module import UNIT_02_NAME
from app.units.unit_03.module import UNIT_03_NAME
from app.units.unit_04.module import UNIT_04_NAME
from app.units.unit_05.module import UNIT_05_NAME
from app.units.unit_06.module import UNIT_06_NAME
from app.units.unit_07.module import UNIT_07_NAME
from app.units.unit_08.module import UNIT_08_NAME
from app.units.unit_09.module import UNIT_09_NAME, AlertResponseUnit
from app.units.unit_10.module import UNIT_10_NAME
from app.units.unit_11.module import UNIT_11_NAME
from app.units.unit_12.module import UNIT_12_NAME
from app.units.unit_13.module import UNIT_13_NAME
from app.units.unit_14.module import UNIT_14_NAME
from app.units.unit_15.module import UNIT_15_NAME

router = APIRouter(prefix="/units", tags=["units"])

_UNIT_NAMES = [
    (1, UNIT_01_NAME, "Video Capture"),
    (2, UNIT_02_NAME, "Scene Understanding"),
    (3, UNIT_03_NAME, "Path Tracking"),
    (4, UNIT_04_NAME, "Hazard Detection"),
    (5, UNIT_05_NAME, "Spatial Behavioral Memory"),
    (6, UNIT_06_NAME, "Collective Behavioral Coherence"),
    (7, UNIT_07_NAME, "Predictive Density"),
    (8, UNIT_08_NAME, "Attendance & Safety Integration"),
    (9, UNIT_09_NAME, "Alert & Response"),
    (10, UNIT_10_NAME, "Smart Dashboard"),
    (11, UNIT_11_NAME, "Multi-Level Reports"),
    (12, UNIT_12_NAME, "Parent Portal"),
    (13, UNIT_13_NAME, "Institutional Self-Assessment"),
    (14, UNIT_14_NAME, "Arab Governance Layer"),
    (15, UNIT_15_NAME, "Pedagogical Behavioral Intelligence"),
]

_capture_unit = VideoCaptureUnit()
_alert_unit = AlertResponseUnit()

# Pre-register demo camera streams
_capture_unit.register_stream("cam-01", "main-campus", "Main Gate")
_capture_unit.register_stream("cam-02", "main-campus", "Corridor A")
_capture_unit.register_stream("cam-03", "main-campus", "Learning Commons")
_capture_unit.register_stream("cam-04", "main-campus", "Playground")


@router.get("")
def list_units() -> list[dict[str, object]]:
    """Return metadata for all 14 integrated system units."""
    return [
        {
            "unit_id": uid,
            "name": name,
            "category": category,
            "status": "active",
        }
        for uid, name, category in _UNIT_NAMES
    ]


@router.get("/capture/health")
def capture_health() -> dict[str, object]:
    """Unit 01 – real-time camera stream health."""
    return _capture_unit.health_summary()


@router.get("/alerts/summary")
def alerts_summary() -> dict[str, object]:
    """Unit 09 – pending alert queue summary."""
    return _alert_unit.summary()
