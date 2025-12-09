# NimbusFlags/backend/app.py

"""NimbusFlags backend application entrypoint.

This module creates and configures the Flask application and applies
development-time CORS settings for local React frontends.
It then starts the HTTP server using environment-based configuration.
"""

from pathlib import Path
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from blueprints.admin.clients_admin import clients_admin_bp
from blueprints.admin.flags_admin import flags_admin_bp
from blueprints.auth.auth import auth_bp
from blueprints.docs.docs import docs_bp
from blueprints.flags.evaluate import evaluate_bp
from blueprints.system.health import health_bp
from errors.handlers import register_error_handlers


def create_app() -> Flask:
    """Create and configure the NimbusFlags Flask application instance.

    This factory loads environment variables, registers blueprints,
    and applies global error handlers.

    Returns:
        Flask: A configured Flask application instance.
    """
    load_dotenv()
    app = Flask(__name__)

    # Register JSON error handlers (400/404/500, etc.).
    register_error_handlers(app)

    # System & health
    app.register_blueprint(health_bp)         # /health/

    # Admin / tenant APIs (machine-to-machine)
    app.register_blueprint(flags_admin_bp)    # /admin/flags/
    app.register_blueprint(clients_admin_bp)  # /clients/signup, /clients/me

    # Public evaluation endpoint (SDK / runtime)
    app.register_blueprint(evaluate_bp)       # /evaluate/

    # Documentation (OpenAPI + Swagger UI)
    app.register_blueprint(docs_bp)           # /openapi.yaml and /docs

    # Dashboard authentication (email/password + sessions)
    app.register_blueprint(auth_bp)           # /auth/*

    return app


if __name__ == "__main__":
    app = create_app()

    # Allow local React development frontends to call this API directly.
    # In production, CORS should be enforced at the reverse proxy layer.
    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "http://localhost:3000",
                    "http://localhost:5173",
                ],
            },
        },
        supports_credentials=False,
        allow_headers=["Content-Type", "X-Api-Key", "X-Session-Token",],
        methods=["GET", "POST", "DELETE", "OPTIONS"],
    )

    # HTTP server configuration derived from environment variables.
    port = int(os.getenv("BACKEND_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
    )
