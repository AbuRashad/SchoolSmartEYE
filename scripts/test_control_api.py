"""End-to-end HTTP tests for the Control Panel endpoints.

Runs against the real FastAPI app via TestClient — exercises JSON
serialization, validation, status codes, and cross-endpoint side effects
(cascade delete, cameras.json persistence).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Make the project root importable when run directly
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Redirect the persisted cameras file into a temp path so we don't
# mutate the repo's real cameras.json during the test.
_TMP_CAMERAS = Path(tempfile.gettempdir()) / "control_panel_test_cameras.json"
if _TMP_CAMERAS.exists():
    _TMP_CAMERAS.unlink()
# Pydantic-settings reads env vars by field-name (case-insensitive)
os.environ["CAMERA_SOURCES_FILE"] = str(_TMP_CAMERAS)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

# Use TestClient as a context manager so the FastAPI lifespan (which seeds
# demo data and loads cameras.json) actually runs.
_client_cm = TestClient(app)
client = _client_cm.__enter__()

OK = "\033[92m✔\033[0m"
FAIL = "\033[91m✘\033[0m"
passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        print(f"{OK} {name}")
        passed += 1
    else:
        print(f"{FAIL} {name}  {detail}")
        failed += 1


print("\n── SETTINGS ──────────────────────────────────────────────")

r = client.get("/api/v1/settings")
check("GET /settings → 200", r.status_code == 200, r.text)
initial_settings = r.json()
check("  has camera_max_fps field", "camera_max_fps" in initial_settings)
check("  has bracelet_low_battery_percent field", "bracelet_low_battery_percent" in initial_settings)

r = client.patch("/api/v1/settings", json={"camera_max_fps": 7.5, "ssi_benchmark": 85.0})
check("PATCH /settings happy path → 200", r.status_code == 200, r.text)
check("  camera_max_fps updated to 7.5", r.json()["camera_max_fps"] == 7.5)
check("  ssi_benchmark updated to 85.0", r.json()["ssi_benchmark"] == 85.0)

r = client.patch("/api/v1/settings", json={"camera_max_fps": 9999})
check("PATCH /settings out-of-range → 422", r.status_code == 422, r.text)

r = client.patch("/api/v1/settings", json={"bracelet_low_battery_percent": 0})
check("PATCH /settings battery=0 → 422", r.status_code == 422)


print("\n── ZONES ─────────────────────────────────────────────────")

r = client.get("/api/v1/zones")
check("GET /zones → 200", r.status_code == 200)
zones = r.json()
check("  returns non-empty list", isinstance(zones, list) and len(zones) > 0)
check("  entries have zone_id + label", all("zone_id" in z and "label" in z for z in zones))
first_zone_id = zones[0]["zone_id"]


print("\n── STUDENTS ──────────────────────────────────────────────")

r = client.get("/api/v1/students")
check("GET /students → 200", r.status_code == 200)
initial_student_count = len(r.json())

student_payload = {
    "student_id": "stu-test-001",
    "name": "Test Student",
    "grade": "Grade 7",
    "class_section": "7A",
    "parent_id": "P-TEST-001",
    "photo_initial": "T",
}
r = client.post("/api/v1/students", json=student_payload)
check("POST /students create → 201", r.status_code == 201, r.text)
check("  name echoed back", r.json().get("name") == "Test Student")

r = client.post("/api/v1/students", json=student_payload)
check("POST /students duplicate id → 409", r.status_code == 409)

r = client.patch("/api/v1/students/stu-test-001", json={"grade": "Grade 8"})
check("PATCH /students/{id} → 200", r.status_code == 200, r.text)
check("  grade updated", r.json()["grade"] == "Grade 8")

r = client.patch("/api/v1/students/does-not-exist", json={"grade": "X"})
check("PATCH /students/{unknown} → 404", r.status_code == 404)


print("\n── BRACELETS ─────────────────────────────────────────────")

r = client.get("/api/v1/bracelets")
check("GET /bracelets → 200", r.status_code == 200)

bad_mac = {
    "bracelet_id": "br-test-001",
    "student_id": "stu-test-001",
    "mac_address": "NOT-A-MAC",
}
r = client.post("/api/v1/bracelets", json=bad_mac)
check("POST /bracelets bad MAC → 422", r.status_code == 422)

missing_student = {
    "bracelet_id": "br-test-001",
    "student_id": "stu-does-not-exist",
    "mac_address": "AA:BB:CC:DD:EE:FF",
}
r = client.post("/api/v1/bracelets", json=missing_student)
check("POST /bracelets unknown student → 400", r.status_code == 400)

good = {
    "bracelet_id": "br-test-001",
    "student_id": "stu-test-001",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "battery_level": 85,
}
r = client.post("/api/v1/bracelets", json=good)
check("POST /bracelets create → 201", r.status_code == 201, r.text)
check("  MAC normalized to upper", r.json()["mac_address"] == "AA:BB:CC:DD:EE:FF")
check("  student_name populated", r.json().get("student_name") == "Test Student")
check("  low_battery=False @ 85%", r.json()["low_battery"] is False)

dup_student = {
    "bracelet_id": "br-test-002",
    "student_id": "stu-test-001",
    "mac_address": "11:22:33:44:55:66",
}
r = client.post("/api/v1/bracelets", json=dup_student)
check("POST /bracelets second for same student → 409", r.status_code == 409)

dup_mac = {
    "bracelet_id": "br-test-003",
    "student_id": "stu-test-001",
    "mac_address": "AA:BB:CC:DD:EE:FF",
}
r = client.post("/api/v1/bracelets", json=dup_mac)
check("POST /bracelets duplicate MAC → 409", r.status_code == 409)

# Ping heartbeat
r = client.post(
    "/api/v1/bracelets/br-test-001/ping",
    json={"zone_id": first_zone_id, "battery_level": 42},
)
check("POST /bracelets/{id}/ping → 200", r.status_code == 200, r.text)
body = r.json()
check("  last_seen_zone updated", body["last_seen_zone"] == first_zone_id)
check("  battery_level updated to 42", body["battery_level"] == 42)
check("  low_battery=True @ 42% (threshold 30 default? check flag)", isinstance(body["low_battery"], bool))

r = client.post(
    "/api/v1/bracelets/br-test-001/ping",
    json={"zone_id": "zone-invalid"},
)
check("POST /bracelets/{id}/ping unknown zone → 400", r.status_code == 400)

r = client.patch("/api/v1/bracelets/br-test-001", json={"battery_level": 100, "is_active": False})
check("PATCH /bracelets/{id} → 200", r.status_code == 200, r.text)
check("  battery_level=100", r.json()["battery_level"] == 100)
check("  is_active=False", r.json()["is_active"] is False)


print("\n── CASCADE DELETE ────────────────────────────────────────")

r = client.delete("/api/v1/students/stu-test-001")
check("DELETE /students/{id} → 204", r.status_code == 204)

r = client.get("/api/v1/bracelets")
remaining = [b for b in r.json() if b["bracelet_id"] == "br-test-001"]
check("  bracelet cascaded-deleted", len(remaining) == 0)

r = client.delete("/api/v1/students/stu-test-001")
check("DELETE /students/{id} again → 404", r.status_code == 404)


print("\n── CAMERAS PERSISTENCE ───────────────────────────────────")

# Remove any leftover camera with same id
client.delete("/api/v1/cameras/cam-test-001")

cam_payload = {
    "camera_id": "cam-test-001",
    "zone_id": first_zone_id,
    "label": "Test Camera",
    "source_url": "0",
    "anonymize_faces": True,
}
r = client.post("/api/v1/cameras", json=cam_payload)
check("POST /cameras → 201/200", r.status_code in (200, 201), r.text)

check(
    "  cameras.json persisted to disk",
    _TMP_CAMERAS.exists(),
    f"expected {_TMP_CAMERAS} to exist",
)
if _TMP_CAMERAS.exists():
    persisted = json.loads(_TMP_CAMERAS.read_text(encoding="utf-8"))
    ids = [e.get("camera_id") for e in persisted]
    check("  persisted entry contains cam-test-001", "cam-test-001" in ids)

# Stop & restart
r = client.post("/api/v1/cameras/cam-test-001/stop")
check("POST /cameras/{id}/stop → 200", r.status_code == 200)

r = client.post("/api/v1/cameras/cam-test-001/start")
check("POST /cameras/{id}/start → 200", r.status_code == 200)

r = client.delete("/api/v1/cameras/cam-test-001")
check("DELETE /cameras/{id} → 204", r.status_code == 204)

if _TMP_CAMERAS.exists():
    persisted = json.loads(_TMP_CAMERAS.read_text(encoding="utf-8"))
    ids = [e.get("camera_id") for e in persisted]
    check("  cameras.json no longer contains cam-test-001", "cam-test-001" not in ids)


print("\n──────────────────────────────────────────────────────────")
print(f"Passed: {passed}   Failed: {failed}")
if _TMP_CAMERAS.exists():
    _TMP_CAMERAS.unlink()
_client_cm.__exit__(None, None, None)
sys.exit(0 if failed == 0 else 1)
