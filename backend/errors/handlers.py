# NimbusFlags/backend/errors/handlers.py
"""Centralized JSON error handling for the NimbusFlags backend.

Defines domain-specific exceptions and registers Flask error handlers
so that errors are returned as consistent JSON payloads instead of
HTML pages.
"""


from __future__ import annotations

from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class BadRequest(Exception):
    """Exception raised for bad requests (HTTP 400).

    Attributes:
        detail: Human-readable description of the error.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFound(Exception):
    """Exception raised for missing resources (HTTP 404).

    Attributes:
        detail: Human-readable description of the error.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def register_error_handlers(app: Flask) -> None:
    """Register JSON error handlers for common HTTP errors.

    Attaches Flask error handlers so the API always returns JSON
    instead of HTML error pages.

    Args:
        app: The Flask application instance to configure.
    """

    @app.errorhandler(BadRequest)
    def _on_bad_request(err: BadRequest) -> tuple[Any, int]:
        """Return HTTP 400 for validation/contract issues."""
        return jsonify({"error": "BadRequest", "detail": err.detail}), 400

    @app.errorhandler(NotFound)
    def _on_not_found(err: NotFound) -> tuple[Any, int]:
        """Return HTTP 404 for missing resources."""
        return jsonify({"error": "NotFound", "detail": err.detail}), 404

    @app.errorhandler(HTTPException)
    def _on_http_exception(err: HTTPException) -> tuple[Any, int]:
        """Fallback for other HTTP errors (for example 500, 405)."""
        code = err.code or 500
        name = err.name or "HTTPException"
        return jsonify({"error": name, "detail": err.description}), code

    @app.errorhandler(Exception)
    def _on_unexpected(_: Exception) -> tuple[Any, int]:
        """Last-resort handler to avoid HTML stack traces."""
        return (
            jsonify(
                {
                    "error": "InternalServerError",
                    "detail": "An unexpected error occurred.",
                }
            ),
            500,
        )
