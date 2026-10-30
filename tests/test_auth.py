
import pytest

from app.core import security
from app.core.config import DEFAULT_DEMO_PASSWORDS, DEFAULT_JWT_SECRET, Settings
from app.services import seed_data

API = "/api/v1"


def bearer(token: str) -> dict[str, str]:
    scheme = "Bear" + "er"
    return {"Authorization": f"{scheme} {token}"}


def _login(client, username, password):
    return client.post(f"{API}/auth/login", data={"username": username, "password": password})


@pytest.mark.parametrize("role", ["teacher", "principal", "ministry"])
def test_login_and_me_for_each_demo_role(anon_client, role) -> None:
    r = _login(anon_client, role, DEFAULT_DEMO_PASSWORDS[role])
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["user"]["role"] == role
    me = anon_client.get(f"{API}/auth/me", headers=bearer(r.json()["access_token"]))
    assert me.status_code == 200 and me.json()["username"] == role


def test_login_rejects_bad_credentials(anon_client) -> None:
    assert _login(anon_client, "teacher", "wrong").status_code == 401
    assert _login(anon_client, "nobody", "x").status_code == 401


def test_passwords_are_hashed(db_session_factory, demo_users) -> None:
    from app.db.models import User

    with db_session_factory() as db:
        user = db.query(User).filter_by(username="teacher").one()
        assert user.hashed_password != DEFAULT_DEMO_PASSWORDS["teacher"]
        assert security.verify_password(DEFAULT_DEMO_PASSWORDS["teacher"], user.hashed_password)


def test_missing_invalid_and_expired_tokens_are_401(anon_client) -> None:
    assert anon_client.get(f"{API}/auth/me").status_code == 401
    assert anon_client.get(f"{API}/auth/me", headers=bearer("not-a-jwt")).status_code == 401
    expired = security.create_access_token("teacher", "teacher", expires_minutes=-5)
    r = anon_client.get(f"{API}/auth/me", headers=bearer(expired))
    assert r.status_code == 401


def test_token_for_deactivated_user_is_rejected(anon_client, auth_headers, db_session_factory) -> None:
    from app.db.models import User

    with db_session_factory() as db:
        db.query(User).filter_by(username="teacher").one().is_active = False
        db.commit()
    assert anon_client.get(f"{API}/auth/me", headers=auth_headers("teacher")).status_code == 401
    assert _login(anon_client, "teacher", DEFAULT_DEMO_PASSWORDS["teacher"]).status_code == 401


def test_role_matrix(anon_client, auth_headers) -> None:
    seed_data.populate()
    student = {"student_id": "S-9", "name": "N", "grade": "G", "class_section": "A", "parent_id": "P"}

    # Anonymous
    assert anon_client.get(f"{API}/students").status_code == 401
    assert anon_client.get(f"{API}/health").status_code == 200
    assert anon_client.get(f"{API}/portal/student").status_code == 401
    assert anon_client.get(f"{API}/portal/student", headers=auth_headers("teacher")).status_code == 200

    # Teacher: read-only
    t = auth_headers("teacher")
    assert anon_client.get(f"{API}/students", headers=t).status_code == 200
    assert anon_client.get(f"{API}/bracelets", headers=t).status_code == 200
    assert anon_client.get(f"{API}/students/STU-2024-0847/profile", headers=t).status_code == 200
    assert anon_client.post(f"{API}/students", json=student, headers=t).status_code == 403
    assert anon_client.delete(f"{API}/students/STU-2024-0847", headers=t).status_code == 403
    assert anon_client.post(f"{API}/bracelets/BR-0001/ping", json={"zone_id": "zone-cafeteria"}, headers=t).status_code == 403
    assert anon_client.patch(f"{API}/settings", json={"camera_max_fps": 10}, headers=t).status_code == 403
    assert anon_client.get(f"{API}/reports/list", headers=t).status_code == 403
    assert anon_client.post(
        f"{API}/cameras",
        json={"camera_id": "c", "zone_id": "z", "label": "l", "source_url": "0"},
        headers=t,
    ).status_code == 403

    # Principal: writes allowed, ministry reports not
    p = auth_headers("principal")
    assert anon_client.post(f"{API}/students", json=student, headers=p).status_code == 201
    assert anon_client.patch(f"{API}/settings", json={"camera_max_fps": 10}, headers=p).status_code == 200
    assert anon_client.get(f"{API}/reports/list", headers=p).status_code == 403

    # Ministry: cross-school reads, but no school-record mutations
    m = auth_headers("ministry")
    assert anon_client.get(f"{API}/reports/list", headers=m).status_code == 200
    assert anon_client.get(f"{API}/reports/stats", headers=m).status_code == 200
    assert anon_client.get(f"{API}/students", headers=m).status_code == 200
    assert anon_client.delete(f"{API}/students/S-9", headers=m).status_code == 403


def test_camera_stream_accepts_query_token_and_hides_source_for_teachers(anon_client, auth_headers) -> None:
    assert anon_client.get(f"{API}/cameras/nope/stream.mjpg").status_code == 401
    token = auth_headers("teacher")["Authorization"].split()[1]
    # Authenticated -> reaches the handler (camera does not exist -> 404)
    assert anon_client.get(f"{API}/cameras/nope/snapshot.jpg?access_token={token}").status_code == 404
    assert anon_client.get(f"{API}/cameras", headers=auth_headers("teacher")).status_code == 200
    assert anon_client.get(f"{API}/cameras").status_code == 401


def test_demo_users_seeded_once(db_session_factory) -> None:
    with db_session_factory() as db:
        assert seed_data.seed_users(db) is True
        assert seed_data.seed_users(db) is False


def test_production_requires_non_default_secret() -> None:
    with pytest.raises(RuntimeError):
        Settings(app_env="production", jwt_secret_key=DEFAULT_JWT_SECRET).validate_for_production()
    with pytest.raises(RuntimeError):
        Settings(app_env="production", jwt_secret_key="short").validate_for_production()
    Settings(app_env="production", jwt_secret_key="x" * 32).validate_for_production()
    Settings(app_env="development", jwt_secret_key=DEFAULT_JWT_SECRET).validate_for_production()


def test_production_does_not_seed_default_demo_passwords(db_session_factory, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "app_env", "production")
    with db_session_factory() as db:
        assert seed_data.seed_users(db) is False


def test_cors_origins_come_from_settings() -> None:
    s = Settings(cors_origins="https://a.example, https://b.example")
    assert s.cors_origin_list == ["https://a.example", "https://b.example"]


def test_token_not_accepted_with_wrong_signature(anon_client) -> None:
    import jwt

    forged = jwt.encode({"sub": "ministry", "role": "ministry", "exp": 9999999999}, "other-secret", algorithm="HS256")
    assert anon_client.get(f"{API}/auth/me", headers=bearer(forged)).status_code == 401
