import pytest

from app.services import seed_data


@pytest.fixture()
def seeded(db_session_factory):
    seed_data.populate()
    return db_session_factory


def _payload(**over):
    base = {"bracelet_id": "BR-9", "student_id": "STU-2024-0851", "mac_address": "aa-bb-cc-dd-ee-ff"}
    base.update(over)
    return base


def test_list_bracelets_backward_compatible_shape(client, seeded) -> None:
    data = client.get("/api/v1/bracelets").json()
    assert len(data) == 5
    assert set(data[0]) == {
        "bracelet_id", "student_id", "student_name", "mac_address", "battery_level", "is_active",
        "last_seen_zone", "last_seen_at", "firmware_version", "notes", "low_battery",
    }
    assert data[0]["student_name"] == "Ahmed Al-Rashidi"


def test_create_bracelet_validates_and_normalises_mac(client, seeded) -> None:
    r = client.post("/api/v1/bracelets", json=_payload())
    assert r.status_code == 201
    assert r.json()["mac_address"] == "AA:BB:CC:DD:EE:FF"
    # Duplicates: id, student, MAC
    assert client.post("/api/v1/bracelets", json=_payload()).status_code == 409
    assert client.post("/api/v1/bracelets", json=_payload(bracelet_id="BR-10")).status_code == 409
    assert client.post(
        "/api/v1/bracelets", json=_payload(bracelet_id="BR-11", student_id="STU-2024-0853")
    ).status_code == 409
    assert client.post("/api/v1/bracelets", json=_payload(bracelet_id="BR-12", student_id="NOPE")).status_code == 400


def test_update_ping_delete_bracelet(client, seeded) -> None:
    r = client.patch("/api/v1/bracelets/BR-0001", json={"battery_level": 5, "notes": "check"})
    assert r.status_code == 200 and r.json()["low_battery"] is True
    r = client.post("/api/v1/bracelets/BR-0001/ping", json={"zone_id": "zone-cafeteria", "battery_level": 70})
    assert r.json()["last_seen_zone"] == "zone-cafeteria" and r.json()["battery_level"] == 70
    assert client.post("/api/v1/bracelets/BR-0001/ping", json={"zone_id": "nope"}).status_code == 400
    assert client.patch("/api/v1/bracelets/BR-0001", json={"student_id": "STU-2024-0848"}).status_code == 409
    assert client.delete("/api/v1/bracelets/BR-0001").status_code == 204
    assert client.delete("/api/v1/bracelets/BR-0001").status_code == 404



def test_bracelet_records_are_isolated_by_school(client, db_session_factory, seeded) -> None:
    from app.db import models as orm

    with db_session_factory() as db:
        db.add(orm.School(school_id="school-other", name="Other School"))
        db.flush()
        db.add(
            orm.Student(
                student_id="STU-OTHER-1", school_id="school-other", name="Other Student",
                grade="Grade 8", class_section="8A", parent_id="P-OTHER",
                photo_initial="O", is_active=True,
            )
        )
        db.flush()
        db.add(
            orm.Bracelet(
                bracelet_id="BR-OTHER", student_id="STU-OTHER-1",
                mac_address="AA:BB:CC:DD:EE:99", battery_level=100, is_active=True,
                firmware_version="1.0.0", notes="",
            )
        )
        db.commit()

    listed = client.get("/api/v1/bracelets")
    assert listed.status_code == 200
    assert all(row["bracelet_id"] != "BR-OTHER" for row in listed.json())
    assert client.patch("/api/v1/bracelets/BR-OTHER", json={"battery_level": 1}).status_code == 404
    assert client.delete("/api/v1/bracelets/BR-OTHER").status_code == 404
    assert client.post(
        "/api/v1/bracelets",
        json={
            "bracelet_id": "BR-10", "student_id": "STU-OTHER-1",
            "mac_address": "AA:BB:CC:DD:EE:10",
        },
    ).status_code == 400


def test_bracelet_ping_rejects_zone_from_another_school(client, db_session_factory, seeded) -> None:
    from app.db import models as orm

    with db_session_factory() as db:
        db.add(orm.School(school_id="school-other", name="Other School"))
        db.flush()
        db.add(
            orm.Zone(
                school_id="school-other", zone_id="zone-other", label="Other",
                zone_type="classroom", capacity=20, floor=1, grid_x=0, grid_y=0,
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/bracelets/BR-0001/ping", json={"zone_id": "zone-other"}
    )
    assert response.status_code == 400
