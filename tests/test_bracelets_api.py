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


def test_bracelet_conflicts_do_not_disclose_foreign_school_records(client, seeded, db_session_factory) -> None:
    from app.db import models as orm

    with db_session_factory() as db:
        db.add(orm.School(school_id="FOREIGN-BRACELET-SCHOOL", name="Foreign Bracelet School", is_active=True))
        db.flush()
        db.add(orm.Student(
            student_id="FOREIGN-BRACELET-STUDENT",
            school_id="FOREIGN-BRACELET-SCHOOL",
            name="Private Student",
            grade="G8",
            class_section="B",
            parent_id="PRIVATE-PARENT",
        ))
        db.flush()
        db.add(orm.Bracelet(
            bracelet_id="BR-FOREIGN-PRIVATE",
            student_id="FOREIGN-BRACELET-STUDENT",
            mac_address="AA:BB:CC:DD:EE:91",
        ))
        db.commit()

    # A globally unique bracelet ID owned by another school receives the same
    # neutral conflict response as any other database uniqueness conflict.
    id_conflict = client.post(
        "/api/v1/bracelets",
        json=_payload(bracelet_id="BR-FOREIGN-PRIVATE"),
    )
    assert id_conflict.status_code == 409
    assert id_conflict.json()["detail"] == (
        "Bracelet could not be created because its identifier or assignment conflicts with an existing record."
    )
    assert "BR-FOREIGN-PRIVATE" not in id_conflict.text
    assert "FOREIGN-BRACELET-SCHOOL" not in id_conflict.text

    # Updating a local bracelet with a MAC owned by another school must
    # return the same neutral conflict without echoing the address.
    update_mac_conflict = client.patch(
        "/api/v1/bracelets/BR-0001",
        json={"mac_address": "AA:BB:CC:DD:EE:91"},
    )
    assert update_mac_conflict.status_code == 409
    assert "AA:BB:CC:DD:EE:91" not in update_mac_conflict.text
    assert "FOREIGN-BRACELET-SCHOOL" not in update_mac_conflict.text

    # MAC addresses are globally unique hardware identifiers; do not run a
    # cross-tenant preflight query or reveal the school that owns the MAC.
    mac_conflict = client.post(
        "/api/v1/bracelets",
        json=_payload(bracelet_id="BR-NEW-MAC-CONFLICT", mac_address="AA:BB:CC:DD:EE:91"),
    )
    assert mac_conflict.status_code == 409
    assert mac_conflict.json()["detail"] == id_conflict.json()["detail"]
    assert "AA:BB:CC:DD:EE:91" not in mac_conflict.text


def test_update_ping_delete_bracelet(client, seeded) -> None:
    r = client.patch("/api/v1/bracelets/BR-0001", json={"battery_level": 5, "notes": "check"})
    assert r.status_code == 200 and r.json()["low_battery"] is True
    r = client.post("/api/v1/bracelets/BR-0001/ping", json={"zone_id": "zone-cafeteria", "battery_level": 70})
    assert r.json()["last_seen_zone"] == "zone-cafeteria" and r.json()["battery_level"] == 70
    assert client.post("/api/v1/bracelets/BR-0001/ping", json={"zone_id": "nope"}).status_code == 400
    assert client.patch("/api/v1/bracelets/BR-0001", json={"student_id": "STU-2024-0848"}).status_code == 409
    assert client.delete("/api/v1/bracelets/BR-0001").status_code == 204
    assert client.delete("/api/v1/bracelets/BR-0001").status_code == 404
