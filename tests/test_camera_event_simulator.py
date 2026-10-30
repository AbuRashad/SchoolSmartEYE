from datetime import datetime, timezone

import pytest

from app.services.camera_event_simulator import generate_camera_events


def test_simulator_generates_reproducible_privacy_minimised_events():
    start = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    first = list(generate_camera_events(
        ["cam-a", "cam-b"], events_per_camera=4, seed=17, run_id="test-run", start_at=start
    ))
    second = list(generate_camera_events(
        ["cam-a", "cam-b"], events_per_camera=4, seed=17, run_id="test-run", start_at=start
    ))

    assert first == second
    assert len(first) == 8
    assert len({event["idempotency_key"] for event in first}) == 8
    assert all(event["camera_id"] in {"cam-a", "cam-b"} for event in first)
    assert all("student_id" not in event and "person_id" not in event for event in first)
    assert all(str(event["evidence_ref"]).startswith("synthetic://") for event in first)


def test_simulator_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        list(generate_camera_events([], events_per_camera=1))
    with pytest.raises(ValueError):
        list(generate_camera_events(["cam-a"], events_per_camera=0))


def test_simulated_camera_events_can_be_ingested_as_a_batch(client):
    events = generate_camera_events(
        ["cam-01", "cam-02", "cam-03", "cam-04"],
        events_per_camera=5,
        seed=23,
        run_id="api-batch",
    )
    responses = [
        client.post("/api/v1/camera-reviews", json=event)
        for event in events
    ]

    assert len(responses) == 20
    assert all(response.status_code == 201 for response in responses)
    assert all(response.json()["status"] == "pending" for response in responses)

    listed = client.get("/api/v1/camera-reviews?status=pending&limit=100")
    assert listed.status_code == 200
    assert listed.json()["count"] == 20
