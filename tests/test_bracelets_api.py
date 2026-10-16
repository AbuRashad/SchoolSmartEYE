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
