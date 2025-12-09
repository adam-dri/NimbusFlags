# NimbusFlags/backend/blueprints/auth/auth.py
"""Authentication endpoints for NimbusFlags (login + logout sessions).

This module exposes HTTP endpoints used by the dashboard frontend to:
- authenticate a client with email/password and create a session
- revoke an existing session token (logout)
"""


from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from services.clients_service import authenticate_client
from services.sessions_service import (
    create_session_for_client,
    delete_session_for_token,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _extract_session_token() -> str | None:
    """Extract a session token from the current request.

    Priority:
        1. X-Session-Token header
        2. Authorization: Bearer <token> header

    Returns:
        str | None: The raw session token string if present,
        otherwise ``None``.
    """
    header_token = request.headers.get("X-Session-Token")
    if header_token:
        return header_token.strip()

    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return None


@auth_bp.post("/login")
def login() -> tuple[Any, int]:
    """Authenticate a client and create a new session.

    Expected JSON body:
        {
            "email": "demo@example.com",
            "password": "secure_password_123"
        }

    Behaviour:
        - Validates that both email and password are provided.
        - Delegates credential verification to ``authenticate_client``.
        - On success, delegates session creation to
          ``create_session_for_client``.

    Returns:
        tuple[Any, int]:
            - On success (200):
                {
                    "session_token": "nsess_...",
                    "client": {
                        "id": "...",
                        "email": "...",
                        "subscription_tier": "free",
                        "active": true,
                        "created_at": "..."
                    }
                }
            - On missing credentials (400):
                JSON error payload.
            - On invalid credentials (401):
                JSON error payload without revealing which field is wrong.
    """
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))

    if not email or not password:
        return (
            jsonify(
                {
                    "error": "Email and password are required.",
                    "code": "auth.missing_credentials",
                }
            ),
            400,
        )

    client = authenticate_client(email=email, password=password)
    if client is None:
        # Do not reveal whether the email or the password is wrong.
        return (
            jsonify(
                {
                    "error": "Invalid email or password.",
                    "code": "auth.invalid_credentials",
                }
            ),
            401,
        )

    # create_session_for_client returns (Session, raw_token)
    _session, session_token = create_session_for_client(client_id=client.id)

    response_body = {
        "session_token": session_token,
        "client": {
            "id": str(client.id),
            "email": client.email,
            "subscription_tier": client.subscription_tier,
            "active": client.active,
            "created_at": client.created_at.isoformat(),
        },
    }
    return jsonify(response_body), 200


@auth_bp.post("/logout")
def logout() -> tuple[Any, int]:
    """Log out the current session.

    The client must send the session token either as:
        - ``X-Session-Token: <token>``
        - ``Authorization: Bearer <token>``

    The endpoint is idempotent: even if the token does not exist,
    it still returns 204.

    Returns:
        tuple[Any, int]:
            - On missing token (400): JSON error payload.
            - On success (204): empty body and HTTP 204.
    """
    token = _extract_session_token()
    if not token:
        return (
            jsonify(
                {
                    "error": "Missing session token.",
                    "code": "auth.missing_session_token",
                }
            ),
            400,
        )

    delete_session_for_token(token)
    return "", 204
