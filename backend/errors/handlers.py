from flask import jsonify
from werkzeug.exceptions import HTTPException


class BadRequest(Exception):
    """Exception raised for bad requests (400)."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFound(Exception):
    """Exception raised for not found resources (404)."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def register_error_handlers(app):
    """Register JSON error handlers for common hTTP errors."""

    @app.errorhandler(BadRequest)
    def _on_bad_request(err: BadRequest) -> jsonify:
        """400 for validation/contract issues"""
        return jsonify({"error": "BadRequest", "detail": err.detail}), 400
    
    @app.errorhandler(NotFound)
    def _on_not_found(err: NotFound) -> jsonify:
        """404 for missing ressources"""
        return jsonify({"error": "NotFound", "detail": err.detail}), 404

    @app.errorhandler(HTTPException)
    def _on_http_exception(err: HTTPException) -> jsonify:
        """Fallback for other HTTP errors (i.e. 500, 405 Method Not Allowed)"""
        code = err.code or 500
        name = err.name or "HTTPException"
        return jsonify({"error": name, "detail": err.description}), code
    
    @app.errorhandler(Exception)
    def _on_unexpected(_: Exception) -> jsonify:
        """Fast-resort handler to avoid HTML stack traces"""
        return jsonify({"error": "InternalServerError", "detail": "An unexpected error occurred."}), 500
