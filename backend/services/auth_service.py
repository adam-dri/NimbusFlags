# NimbusFlags/backend/services/auth_service.py

"""
Authentication helpers and decorators.

This module provides two authentication mechanisms:

1. API key authentication (machine-to-machine):
    - Header: ``X-Api-Key``
    - Used by runtime clients and programmatic admin access.

2. Session-based authentication (dashboard login):
    - Header: ``X-Session-Token``
    - Used by the React dashboard after a user logs in with
        email/password and receives a short-lived session token.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, Optional, TypeVar, cast

from flask import g, jsonify, request

# Support both "backend." package imports and running app.py directly.
try:  # pragma: no cover - import-path handling
    from backend.services.clients_service import (
        Client,
        resolve_client_by_api_key,
    )
    from backend.services.sessions_service import get_session_for_token
    from backend.repositories import clients_repo
except ImportError:  # pragma: no cover - app.py / direct execution
    from services.clients_service import (
        Client,
        resolve_client_by_api_key,  # type: ignore[no-redef]
    )
    from services.sessions_service import (
        get_session_for_token,  # type: ignore[no-redef]
    )
    from repositories import clients_repo  # type: ignore[no-redef]


F = TypeVar("F", bound=Callable[..., object])


def get_current_client() -> Optional[Client]:
    """Return the current authenticated client, if any.

    This helper reads the ``g.client`` attribute that is populated by
    authentication decorators such as :func:`require_api_key` or
    :func:`require_session`.

    Returns:
        Optional[Client]: The currently authenticated client, or ``None``
        if no client has been attached to the context.
    """
    return getattr(g, "client", None)


def require_api_key(func: F) -> F:
    """Flask view decorator that enforces API key authentication.

    Behaviour:
        - Reads the ``X-Api-Key`` header from the request.
        - Uses :func:`resolve_client_by_api_key` to resolve the client.
        - If invalid or missing -> returns ``401`` with a JSON error.
        - If valid -> stores ``client`` and ``client_id`` on ``flask.g``
            and calls the wrapped view.

    Usage example:

        from backend.services.auth_service import require_api_key

        @bp.route("/admin/flags", methods=["GET"])
        @require_api_key
        def list_flags():
            client = g.client        # full Client DTO
            client_id = g.client_id  # UUID
            ...

    Args:
        func: The view function to wrap.

    Returns:
        F: The wrapped view function that enforces API key authentication.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-Api-Key", "").strip()

        client = resolve_client_by_api_key(api_key)
        if client is None:
            response = jsonify(
                {
                    "error": "Invalide or missing API key",
                    "code": "auth.api_key_invalid",
                }
            )
            return response, 401

        # Attach client to the request context
        g.client = client
        g.client_id = client.id

        return func(*args, **kwargs)

    return cast(F, wrapper)


def _get_session_token_from_request() -> Optional[str]:
    """Extract the raw session token from the incoming HTTP request.

    Currently the token is read from the ``X-Session-Token`` header.

    Returns:
        Optional[str]: The raw session token, or ``None`` if it is not
        present or only contains whitespace.
    """
    token = request.headers.get("X-Session-Token", "").strip()
    return token or None


def require_session(func: F) -> F:
    """Require a valid dashboard session for human (UI) requests.

    This decorator is intended for routes that are called by the React
    dashboard, where users authenticate via email/password and receive
    a short-lived session token. It is **complementary** to
    :func:`require_api_key`, which is kept for machine clients.

    Behaviour:
        * Reads the token from ``X-Session-Token`` header.
        * Looks up a non-expired session via :func:`get_session_for_token`.
        * Resolves the associated client record from the ``clients`` table.
        * On success, attaches ``g.client`` and ``g.client_id``.
        * On failure, returns a JSON ``401 Unauthorized`` response.

    Error responses use stable codes that can be asserted in tests:

    * Missing token:

        .. code-block:: json

            {
                "error": "Invalid or missing session token",
                "code": "auth.session_missing"
            }

    * Invalid or expired token:

        .. code-block:: json

            {
                "error": "Invalid or expired session token",
                "code": "auth.session_invalid"
            }

    * Client not found for a valid session (rare edge case):

        .. code-block:: json

            {
                "error": "Client not found for session",
                "code": "auth.session_client_missing"
            }

    Args:
        func: The view function to wrap.

    Returns:
        F: The wrapped view function that enforces session-based
        authentication.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        raw_token = _get_session_token_from_request()
        if raw_token is None:
            response = jsonify(
                {
                    "error": "Invalid or missing session token",
                    "code": "auth.session_missing",
                }
            )
            return response, 401

        session = get_session_for_token(raw_token)
        if session is None:
            response = jsonify(
                {
                    "error": "Invalid or expired session token",
                    "code": "auth.session_invalid",
                }
            )
            return response, 401

        # Fetch the client associated with this session.
        row = clients_repo.get_client_by_id(session.client_id)
        if row is None:
            # Session exists but client was deleted or is unreachable.
            response = jsonify(
                {
                    "error": "Client not found for session",
                    "code": "auth.session_client_missing",
                }
            )
            return response, 401

        client = Client(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            api_key_hash=row["api_key_hash"],
            subscription_tier=row["subscription_tier"],
            active=row["active"],
            created_at=row["created_at"],
        )

        # Attach client to the request context (same convention as API keys).
        g.client = client
        g.client_id = client.id

        return func(*args, **kwargs)

    return cast(F, wrapper)
