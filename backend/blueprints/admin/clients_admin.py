# NimbusFlags/backend/blueprints/admin/clients_admin.py
"""Admin-facing client endpoints (signup + profile) for NimbusFlags."""


from __future__ import annotations

from flask import Blueprint, jsonify, request, g, Response
from services.auth_service import require_api_key


try:
    # (tests)
    from backend.services.clients_service import (
        Client,
        ClientAlreadyExistsError,
        register_client,
    )
except ImportError:
    # (python app.py)
    from services.clients_service import (
        Client,
        ClientAlreadyExistsError,
        register_client,
    )


clients_admin_bp = Blueprint(
    "clients_admin_bp",
    __name__,
    url_prefix="/clients",
)


def _client_to_dict(client: Client) -> dict:
    """Serialize a Client domain model into a JSON-safe dict.
    We never expose password_hash or api_key_hash.

    Args:
        client (Client): The Client domain model to serialize.

    Returns:
        dict: A dictionary representation of the Client.
    """
    return {
        "id": str(client.id),
        "email": client.email,
        "subscription_tier": client.subscription_tier,
        "active": client.active,
        "created_at": client.created_at.isoformat(),
    }


@clients_admin_bp.post("/signup")
def post_signup() -> tuple[Response, int]:
    """Register a new NimbusFlags client (tenant).

    Body JSON (minimal V1):
    {
        "email": "user@example.com",
        "password": "plain-text-password"
    }

    Behaviour:
        - 201 + { "client": {...}, "api_key": "<plaintext> } on success
        - 400 + if email/password invalid
        - 409 if email already exists

    Returns:
        tuple[Response, int]: Flask JSON response and HTTP status code.
    """

    payload = request.get_json(silent=True) or {}

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    # Basic input validation here.
    if not email or "@" not in email:
        return (
            jsonify({
                "error": "Invalid email address provided.",
                "code": "clients.invalid_email",
                }
            ),
            400,
        )

    if not password:
        return (
            jsonify({
                "error": "Password cannot be empty.",
                "code": "clients.invalide_password",
                }
            ),
            400,
        )

    try:
        client, api_key_plain = register_client(email=email, password=password)
    except ClientAlreadyExistsError:
        return (
            jsonify(
                {
                    "error": "Email already registered",
                    "code": "clients.email_conflict",
                }
            ),
            409,
        )
    except ValueError as e:
        # Ex: invalide email/password raised by service.
        return (
            jsonify(
                {
                    "error": str(e),
                    "code": "clients.invalid_input",
                }
            ),
            400,
        )

    response_body = {
        "client": _client_to_dict(client),
        # Important: we only return the plaintext API key ONCE.
        "api_key": api_key_plain,
    }

    return jsonify(response_body), 201


@clients_admin_bp.get("/me")
@require_api_key
def get_current_client_profile():
    """Fetch the profile of the current authenticated client.

    Auth:
        Requires a valid ``X-Api-Key`` header set on the request.
        The ``require_api_key`` decorator attaches the authenticated
        client object to ``flask.g`` as ``g.client``.

    Returns:
        tuple[Response, int]: JSON response containing the client profile
        and the HTTP status code 200.
    """
    client = g.client  # Set by require_api_key
    return jsonify({"client": _client_to_dict(client)}), 200
