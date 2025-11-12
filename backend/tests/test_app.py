import pytest

try:
    from app import app as flask_app
except Exception:
    from app import create_app as _create_app
    flask_app = _create_app()


@pytest.fixture(scope="module")
def client():
    with flask_app.test_client() as c:
        yield c

def _seed_flag(client):
    """
    Idempotent: safe to call multiple times.
    """
    client.post("/admin/flags/", json={
        "key": "promo_premium_ca",
        "enabled": True,
        "conditions": [
            {"attribute": "subscription", "operator": "equals", "value": "premium"},
            {"attribute": "country", "operator": "in", "value": ["CA", "US"]},
        ],
        "parameters": {"discount_percentage": 40},
    })

def test_health(client):
    r = client.get("/health/")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}

def test_admin_upsert_and_get(client):
    body = {
        "key": "promo_premium_ca",
        "enabled": True,
        "conditions": [
            {"attribute": "subscription", "operator": "equals", "value": "premium"},
            {"attribute": "country", "operator": "in", "value": ["CA", "US"]},
        ],
        "parameters": {"discount_percentage": 40},
    }
    assert client.post("/admin/flags/", json=body).status_code == 200

    r = client.get("/admin/flags/promo_premium_ca")
    assert r.status_code == 200
    data = r.get_json()
    assert data["key"] == "promo_premium_ca"
    assert data["parameters"]["discount_percentage"] == 40

def test_evaluate_pass_fail_unknown(client):
    _seed_flag(client)

    # pass
    r = client.post("/evaluate/", json={
        "flag_key": "promo_premium_ca",
        "user_attributes": {"subscription": "premium", "country": "CA"},
    })
    assert r.status_code == 200
    data = r.get_json()
    assert data["enabled"] is True and data["parameters"]["discount_percentage"] == 40

    # fail (missing attribute)
    r = client.post("/evaluate/", json={
        "flag_key": "promo_premium_ca",
        "user_attributes": {"subscription": "premium"},
    })
    assert r.status_code == 200
    assert r.get_json()["enabled"] is False

    # unknown flag -> 404
    r = client.post("/evaluate/", json={
        "flag_key": "does_not_exist",
        "user_attributes": {"subscription": "premium", "country": "CA"},
    })
    assert r.status_code == 404
    assert r.get_json()["error"] == "NotFound"

def test_openapi_and_schemas(client):
    yml = client.get("/openapi.yaml")
    assert yml.status_code == 200
    assert yml.data.startswith(b"openapi: 3.")
    for name in [
        "flag_config.schema.json",
        "EvaluateRequest.schema.json",
        "EvaluateResponse.schema.json",
    ]:
        rr = client.get(f"/schemas/{name}")
        assert rr.status_code == 200
        assert rr.data.strip().startswith(b"{")
