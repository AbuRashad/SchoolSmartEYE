from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import models as orm
from app.main import app
from app.services import seed_data


def test_dashboard_rest_endpoints_return_school_scoped_database_views(client: TestClient) -> None:
    seed_data.populate()
    summary = client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["schoolId"] == "DEMO-SCHOOL-001"
    assert summary.json()["totalStudents"] == 10
    assert summary.json()["dataSource"] == "school_scoped_database"
    assert summary.json()["ssiStatus"] in {"measured", "awaiting_school_measurement"}

    alerts = client.get("/api/v1/dashboard/alerts")
    assert alerts.status_code == 200
    assert all(item["stream"] == "persisted_incident" for item in alerts.json())

    heatmap = client.get("/api/v1/dashboard/heatmap")
    assert heatmap.status_code == 200
    assert heatmap.json()["dataSource"] == "school_scoped_database"
    assert all("zone_id" in cell and "signal_source" in cell for cell in heatmap.json()["cells"])

    live = client.get("/api/v1/dashboard/live")
    assert live.status_code == 200
    assert live.json()["snapshotType"] == "database_derived_not_streaming"
    assert live.json()["fetchedFromBackend"] is True


def test_dashboard_views_exclude_other_school_records(client: TestClient, db_session_factory) -> None:
    seed_data.populate()
    with db_session_factory() as db:
        db.add(orm.School(school_id="DASH-FOREIGN", name="Foreign Dashboard School", is_active=True))
        db.flush()
        db.add(orm.Student(
            student_id="DASH-FOREIGN-STUDENT", school_id="DASH-FOREIGN", name="Foreign",
            grade="G8", class_section="A", parent_id="P-F",
        ))
        db.add(orm.Zone(
            zone_id="DASH-FOREIGN-ZONE", school_id="DASH-FOREIGN", label="Foreign Zone",
            zone_type="classroom", capacity=20, floor=1, grid_x=99, grid_y=99,
        ))
        db.flush()
        db.add(orm.Incident(
            incident_id="DASH-FOREIGN-INCIDENT", zone_id="DASH-FOREIGN-ZONE",
            severity="critical", description="Private foreign incident",
            detected_at=datetime.now(timezone.utc), resolved=False,
        ))
        db.add(orm.Camera(
            camera_id="DASH-FOREIGN-CAMERA", zone_id="DASH-FOREIGN-ZONE",
            label="Foreign Camera", is_active=True,
        ))
        db.commit()

    summary = client.get("/api/v1/dashboard/summary").json()
    alerts = client.get("/api/v1/dashboard/alerts").json()
    heatmap = client.get("/api/v1/dashboard/heatmap").json()
    assert summary["totalStudents"] == 10
    assert summary["activeCameras"] == 12
    assert all(item["id"] != "DASH-FOREIGN-INCIDENT" for item in alerts)
    assert all(cell["zone_id"] != "DASH-FOREIGN-ZONE" for cell in heatmap["cells"])


def test_dashboard_websocket_is_refused_until_tenant_scoped(auth_headers) -> None:
    token = auth_headers("teacher")["Authorization"].split()[1]
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/dashboard/ws?access_token={token}") as websocket:
            websocket.receive_json()
