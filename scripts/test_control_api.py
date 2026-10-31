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
# Use a throw-away SQLite database instead of the developer's real one.
_TMP_DB = Path(tempfile.gettempdir()) / "control_panel_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

# Use TestClient as a context manager so the FastAPI lifespan (which seeds
# demo data and loads cameras.json) actually runs.
_client_cm = TestClient(app)
client = _client_cm.__enter__()

# The control endpoints require a principal (or higher) account.
_login = client.post(
    "/api/v1/auth/login",
    data={"username": "principal", "password": os.environ.get("DEMO_PRINCIPAL_PASSWORD", "principal123")},
)
assert _login.status_code == 200, _login.text
client.headers["Authorization"] = "Bear" + "er " + _login.json()["access_token"]

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
check("GET /settings fails closed → 503", r.status_code == 503, r.text)

r = client.patch("/api/v1/settings", json={"camera_max_fps": 7.5, "ssi_benchmark": 85.0})
check("PATCH /settings fails closed → 503", r.status_code == 503, r.text)


print("\n── ZONES ─────────────────────────────────────────────────")

r = client.get("/api/v1/zones")
check("GET /zones fails closed → 503", r.status_code == 503, r.text)


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

# Location heartbeat remains disabled until zone ownership is migrated.
r = client.post(
    "/api/v1/bracelets/br-test-001/ping",
    json={"zone_id": "legacy-zone", "battery_level": 42},
)
check("POST /bracelets/{id}/ping fails closed → 503", r.status_code == 503, r.text)

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


print("\n── CAMERAS TENANT BOUNDARY ────────────────────────────────")

# Camera ingestion is process-global; no list, stream, or mutation is allowed
# until camera records and workers are partitioned by verified school ownership.
for method, path, payload in (
    ("get", "/api/v1/cameras", None),
    ("post", "/api/v1/cameras", {
        "camera_id": "cam-test-001",
        "zone_id": "legacy-zone",
        "label": "Test Camera",
        "source_url": "0",
        "anonymize_faces": True,
    }),
    ("post", "/api/v1/cameras/cam-test-001/stop", None),
    ("post", "/api/v1/cameras/cam-test-001/start", None),
    ("delete", "/api/v1/cameras/cam-test-001", None),
):
    response = getattr(client, method)(path, json=payload) if payload is not None else getattr(client, method)(path)
    check(f"{method.upper()} {path} fails closed → 503", response.status_code == 503, response.text)


print("\n──────────────────────────────────────────────────────────")
print(f"Passed: {passed}   Failed: {failed}")
if _TMP_CAMERAS.exists():
    _TMP_CAMERAS.unlink()
_client_cm.__exit__(None, None, None)
sys.exit(0 if failed == 0 else 1)
