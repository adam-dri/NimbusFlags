# NimbusFlags/backend/tests/test_app.py
"""
Integration tests for the NimbusFlags Flask application.

These tessts exercise the real Flask app + Postgres database stack to ensure
that all components work together as expected.

They intentionnaly:
- boostrap the app from backend/app.py (via the "app" module),
- hit the real HTTP routes Flask's test client,
- reset "clients" and "flags" tables between tests to keep them independent.
"""


import pathlib
import sys
import uuid

import pytest

# Ensure backend/ is on sys.path so that `app` and `blueprints` work
BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app import app as flask_app
except ImportError:
    from app import create_app as _create_app
    flask_app = _create_app()


@pytest.fixture(scope="module")
def client():
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def api_key(client):
    """Create a test client (tenant) and return its API key.

    This hits the real /clients/signup endpoint so that all subsequent
    admin and evaluate calls are authenticated and go through the full stack.
    """
    email = f"test_admin_{uuid.uuid4().hex}@example.com"
    resp = client.post(
        "/clients/signup",
        json={
            "email": email,
            "password": "secret123",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "api_key" in data
    return data["api_key"]


def _seed_flag(client, api_key: str):
    """Create or update a test flag for the authenticated client.

    Idempotent: safe to call multiple times for the same client, since the
    underlying repository implements an upsert on (client_id, key).
    """
    headers = {"X-Api-Key": api_key}
    client.post(
        "/admin/flags/",
        json={
            "key": "promo_premium_ca",
            "enabled": True,
            "conditions": [
                {
                    "attribute": "subscription",
                    "operator": "equals",
                    "value": "premium",
                },
                {
                    "attribute": "country",
                    "operator": "in",
                    "value": ["CA", "US"],
                },
            ],
            "parameters": {"discount_percentage": 40},
        },
        headers=headers,
    )


def test_health(client):
    r = client.get("/health/")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_admin_upsert_and_get(client, api_key):
    headers = {"X-Api-Key": api_key}
    body = {
        "key": "promo_premium_ca",
        "enabled": True,
        "conditions": [
            {
                "attribute": "subscription",
                "operator": "equals",
                "value": "premium",
            },
            {
                "attribute": "country",
                "operator": "in",
                "value": ["CA", "US"],
            },
        ],
        "parameters": {"discount_percentage": 40},
    }

    r = client.post("/admin/flags/", json=body, headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["key"] == "promo_premium_ca"
    assert data["parameters"]["discount_percentage"] == 40

    # GET by key should return the same flag for the same client
    r = client.get("/admin/flags/promo_premium_ca", headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["key"] == "promo_premium_ca"
    assert data["parameters"]["discount_percentage"] == 40


def test_evaluate_pass_fail_unknown(client, api_key):
    headers = {"X-Api-Key": api_key}
    _seed_flag(client, api_key)

    # pass
    r = client.post(
        "/evaluate/",
        json={
            "flag_key": "promo_premium_ca",
            "user_attributes": {"subscription": "premium", "country": "CA"},
        },
        headers=headers,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["enabled"] is True
    assert data["parameters"]["discount_percentage"] == 40

    # fail (missing attribute)
    r = client.post(
        "/evaluate/",
        json={
            "flag_key": "promo_premium_ca",
            "user_attributes": {"subscription": "premium"},
        },
        headers=headers,
    )
    assert r.status_code == 200
    assert r.get_json()["enabled"] is False

    # unknown flag -> 404
    r = client.post(
        "/evaluate/",
        json={
            "flag_key": "does_not_exist",
            "user_attributes": {"subscription": "premium", "country": "CA"},
        },
        headers=headers,
    )
    assert r.status_code == 404
    assert r.get_json()["error"] == "NotFound"


def test_openapi_and_schemas(client):
    yml = client.get("/openapi.yaml")
    assert yml.status_code == 200
    assert b"openapi: 3." in yml.data
    for name in [
        "flag_config.schema.json",
        "EvaluateRequest.schema.json",
        "EvaluateResponse.schema.json",
    ]:
        rr = client.get(f"/schemas/{name}")
        assert rr.status_code == 200
        assert rr.data.strip().startswith(b"{")


def test_clients_me_requires_api_key(client):
    """Calling /clients/me without X-Api-Key should return 401."""
    response = client.get("/clients/me")
    assert response.status_code == 401


def test_clients_me_returns_current_client_profile(client):
    """After signup, /clients/me should return the same client
    when called with the API key."""
    # 1) Signup a new client
    email = f"me-{uuid.uuid4()}@example.com"
    signup_response = client.post(
        "/clients/signup",
        json={"email": email, "password": "secret123"},
    )

    assert signup_response.status_code == 201
    signup_body = signup_response.get_json()
    assert isinstance(signup_body, dict)
    assert "api_key" in signup_body
    assert "client" in signup_body

    api_key = signup_body["api_key"]

    # 2) Call /clients/me with the returned API key
    me_response = client.get(
        "/clients/me",
        headers={"X-Api-Key": api_key},
    )

    assert me_response.status_code == 200
    me_body = me_response.get_json()
    assert isinstance(me_body, dict)
    assert "client" in me_body

    client_payload = me_body["client"]
    # Basic invariants
    assert client_payload["email"] == email
    assert client_payload["active"] is True
    assert client_payload["subscription_tier"] == "free"
    assert "id" in client_payload
    assert "created_at" in client_payload


def test_auth_login_succes(client):
    """
    Login returns 200 and a session_token for valid credentials.
    """
    # First signup a client with a unique email
    email = f"login-succes-{uuid.uuid4().hex}@example.com"
    signup_payload = {
        "email": email,
        "password": "secret123",
    }
    resp = client.post("/clients/signup", json=signup_payload)
    assert resp.status_code == 201

    # Then login with the same credentials
    login_payload = {
        "email": email,
        "password": "secret123",
    }
    resp = client.post("/auth/login", json=login_payload)
    assert resp.status_code == 200

    data = resp.get_json()
    assert "client" in data
    assert "session_token" in data

    client_obj = data["client"]
    assert client_obj["email"] == email
    assert client_obj["active"] is True


def test_auth_login_wrond_password(client):
    """
    Login returns 401 when the password is incorrect.
    """
    # Signup with a known password and a unique email
    email = f"login-wrong-password-{uuid.uuid4().hex}@example.com"
    signup_payload = {
        "email": email,
        "password": "correct_password",
    }
    resp = client.post("/clients/signup", json=signup_payload)
    assert resp.status_code == 201

    # Attempt login with the wrong password
    login_payload = {
        "email": email,
        "password": "incorrect_password",
    }
    resp = client.post("/auth/login", json=login_payload)

    # Authentication should fail with 401
    assert resp.status_code == 401



def test_auth_login_unkown_email(client):
    """No signup for this email on purpose"""
    login_payload = {
        "email": "unknown@example.com",
        "password": "whatever123",
    }
    resp = client.post("/auth/login", json=login_payload)

    # Unknown email should be treated as a generic aith failure
    assert resp.status_code == 401


def test_auth_logout_with_valid_token(client):
    """
    Logout returns 204 when called with a valid session token.
    """
    # 1) Signup + login to obtain a session token
    email = f"logout-test-{uuid.uuid4().hex}@example.com"
    signup_payload = {
        "email": email,
        "password": "secret123",
    }
    resp = client.post("/clients/signup", json=signup_payload)
    assert resp.status_code == 201

    login_payload = {
        "email": email,
        "password": "secret123",
    }
    resp = client.post("/auth/login", json=login_payload)
    assert resp.status_code == 200

    data = resp.get_json()
    session_token = data["session_token"]
    assert isinstance(session_token, str)
    assert session_token.startswith("nsess_")

    # 2) Call logout with the same token
    resp = client.post(
        "/auth/logout",
        headers={"X-Session-Token": session_token},
    )

    # Logout is idempotent and returns no body
    assert resp.status_code == 204
