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
        resolve_client_by_session_token,
    )
except ImportError:  # pragma: no cover - app.py / direct execution
    from services.clients_service import (
        Client,
        resolve_client_by_api_key,  # type: ignore[no-redef]
        resolve_client_by_session_token,  # type: ignore[no-redef]
    )


F = TypeVar("F", bound=Callable[..., object])


def get_current_client() -> Optional[Client]:
    """Return the current authenticated client, if any.

    This helper reads the ``g.client`` attribute that is populated by
    authentication decorators such as :func:`require_api_key` or
    :func:`require_client_auth`.

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
                    "error": "Invalid or missing API key",
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


def require_client_auth(func: F) -> F:
    """Flask view decorator accepting session token OR API key auth.

    This is the decorator used by routes shared between the React
    dashboard (which sends ``X-Session-Token``) and machine clients
    (which send ``X-Api-Key``).

    Behaviour:
        * If ``X-Session-Token`` is present, resolves the client via
          :func:`resolve_client_by_session_token`.
        * Otherwise, if ``X-Api-Key`` is present, resolves the client
          via :func:`resolve_client_by_api_key`.
        * If no client could be resolved -> returns ``401`` with a JSON
          error (``{"error": "Unauthorized", "code": "auth.required"}``).
        * On success, attaches ``g.client`` and ``g.client_id`` and
          calls the wrapped view.

    Args:
        func: The view function to wrap.

    Returns:
        F: The wrapped view function that enforces client authentication.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        client: Optional[Client] = None

        session_token = _get_session_token_from_request()
        if session_token is not None:
            client = resolve_client_by_session_token(session_token)
        else:
            api_key = request.headers.get("X-Api-Key", "").strip()
            if api_key:
                client = resolve_client_by_api_key(api_key)

        if client is None:
            response = jsonify(
                {
                    "error": "Unauthorized",
                    "code": "auth.required",
                }
            )
            return response, 401

        # Attach client to the request context (same convention as API keys).
        g.client = client
        g.client_id = client.id

        return func(*args, **kwargs)

    return cast(F, wrapper)
