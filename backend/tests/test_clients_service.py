# backend/tests/test_clients_service.py
"""
Unit tests for the clients_service module.

These tests verify password hashing/verification, API key generation and
hashing, and client registration / resolution logic (with repository calls
mocked out using monkeypatch).
"""


from uuid import uuid4
from datetime import datetime, timezone

import pytest


from backend.services.clients_service import (
    Client,
    ClientAlreadyExistsError,
    API_KEY_PREFIX,
    hash_password,
    verify_password,
    generate_api_key,
    hash_api_key,
    register_client,
    resolve_client_by_api_key,
)


# ---------- Password hashing ----------


def test_hash_and_verify_password_success():
    plain = "my_strong_password"
    password_hash = hash_password(plain)

    assert isinstance(password_hash, str)
    assert password_hash != plain
    # bcrypt hashes usually start with "$2b$" or "$2a$"
    assert password_hash.startswith("$2")

    assert verify_password(plain, password_hash) is True
    assert verify_password("wrong_password", password_hash) is False


def test_hash_password_empty_raises_value_error():
    with pytest.raises(ValueError):
        hash_password("")


def test_verify_password_with_empty_values_returns_false():
    assert verify_password("", "") is False
    assert verify_password("some-password", "") is False
    assert verify_password("", "$2b$12$something") is False


# ---------- API key generation / hashing ----------


def test_generate_api_key_format():
    api_key = generate_api_key()
    assert isinstance(api_key, str)
    assert api_key.startswith(API_KEY_PREFIX)
    # Not strictly required, but we expect a relatively long key
    assert len(api_key) > len(API_KEY_PREFIX) + 10


def test_hash_api_key_is_deterministic():
    key = "nf_live_test_key"
    h1 = hash_api_key(key)
    h2 = hash_api_key(key)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex digest


# ---------- register_client ----------


def test_register_client_creates_client_and_returns_api_key(monkeypatch):
    """
    We mock clients_repo to simulate a real DB insert and verify that:
    - the email is normalized
    - the password is hashed (not equal to plain)
    - the api_key_hash stored in DB matches hash_api_key(api_key_plain)
    - we get back a Client object with expected fields
    """
    created_clients = {}

    def fake_get_client_by_email(email: str):
        # No existing client in this test
        return None

    def fake_create_client(
            email,
            password_hash,
            api_key_hash,
            subscription_tier
            ):
        client_id = uuid4()
        now = datetime.now(timezone.utc)

        # Keep what has been passed for later assertions
        created_clients["email"] = email
        created_clients["password_hash"] = password_hash
        created_clients["api_key_hash"] = api_key_hash
        created_clients["subscription_tier"] = subscription_tier

        # Simulate the row dict returned by psycopg (dict_row)
        return {
            "id": client_id,
            "email": email,
            "password_hash": password_hash,
            "api_key_hash": api_key_hash,
            "subscription_tier": subscription_tier,
            "active": True,
            "created_at": now,
        }

    # Patch the repository functions
    monkeypatch.setattr(
        "backend.services.clients_service.clients_repo.get_client_by_email",
        fake_get_client_by_email,
    )
    monkeypatch.setattr(
        "backend.services.clients_service.clients_repo.create_client",
        fake_create_client,
    )

    client, api_key_plain = register_client("USER@Example.COM", "my_password")

    # Basic checks on return types
    assert isinstance(client, Client)
    assert isinstance(api_key_plain, str)
    assert api_key_plain.startswith(API_KEY_PREFIX)

    # Email is normalized (lowercased)
    assert created_clients["email"] == "user@example.com"

    # Password is hashed
    assert created_clients["password_hash"] != "my_password"
    assert created_clients["password_hash"].startswith("$2")

    # The stored api_key_hash matches the plaintext api key returned
    expected_hash = hash_api_key(api_key_plain)
    assert created_clients["api_key_hash"] == expected_hash

    # DTO fields
    assert client.email == "user@example.com"
    assert client.subscription_tier == "free"
    assert client.active is True
    assert isinstance(client.created_at, datetime)


def test_register_client_existing_email_raises(monkeypatch):
    def fake_get_client_by_email(email: str):
        # Simulate an existing client row
        return {"id": uuid4(), "email": email}

    monkeypatch.setattr(
        "backend.services.clients_service.clients_repo.get_client_by_email",
        fake_get_client_by_email,
    )

    with pytest.raises(ClientAlreadyExistsError):
        register_client("user@example.com", "some-password")


def test_register_client_invalid_email_raises():
    with pytest.raises(ValueError):
        register_client("not-an-email", "password")


def test_register_client_empty_password_raises(monkeypatch):
    def fake_get_client_by_email(email: str):
        return None

    monkeypatch.setattr(
        "backend.services.clients_service.clients_repo.get_client_by_email",
        fake_get_client_by_email,
    )

    with pytest.raises(ValueError):
        register_client("user@example.com", "")


# ---------- resolve_client_by_api_key ----------


def test_resolve_client_by_api_key_returns_client_when_active(monkeypatch):
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    def fake_get_client_by_api_key_hash(received_hash: str):
        # Ensure the service hashed the key correctly
        assert received_hash == api_key_hash

        client_id = uuid4()
        now = datetime.now(timezone.utc)
        return {
            "id": client_id,
            "email": "user@example.com",
            "password_hash": "ignored",
            "api_key_hash": api_key_hash,
            "subscription_tier": "free",
            "active": True,
            "created_at": now,
        }

    monkeypatch.setattr(
            "backend.services.clients_service.clients_repo"
            ".get_client_by_api_key_hash",
            fake_get_client_by_api_key_hash,
        )

    client = resolve_client_by_api_key(api_key)

    assert isinstance(client, Client)
    assert client.email == "user@example.com"
    assert client.subscription_tier == "free"
    assert client.active is True


def test_resolve_client_by_api_key_returns_none_for_missing_or_wrong_prefix():
    assert resolve_client_by_api_key("") is None
    assert resolve_client_by_api_key("random_string_without_prefix") is None


def test_resolve_client_by_api_key_returns_none_when_not_found(monkeypatch):
    def fake_get_client_by_api_key_hash(api_key_hash: str):
        return None

    monkeypatch.setattr(
            "backend.services.clients_service.clients_repo"
            ".get_client_by_api_key_hash",
            fake_get_client_by_api_key_hash,
        )

    api_key = generate_api_key()
    client = resolve_client_by_api_key(api_key)
    assert client is None


def test_resolve_client_by_api_key_returns_none_when_inactive(monkeypatch):
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    def fake_get_client_by_api_key_hash(received_hash: str):
        assert received_hash == api_key_hash
        client_id = uuid4()
        now = datetime.now(timezone.utc)
        return {
            "id": client_id,
            "email": "user@example.com",
            "password_hash": "ignored",
            "api_key_hash": api_key_hash,
            "subscription_tier": "free",
            "active": False,  # inactive
            "created_at": now,
        }

    monkeypatch.setattr(
            "backend.services.clients_service.clients_repo"
            ".get_client_by_api_key_hash",
            fake_get_client_by_api_key_hash,
        )

    client = resolve_client_by_api_key(api_key)
    assert client is None
