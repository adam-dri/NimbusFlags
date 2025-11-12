import os
from flask import Flask
from dotenv import load_dotenv
from pathlib import Path

from blueprints.system.health import health_bp
from blueprints.admin.flags_admin import flags_admin_bp
from blueprints.flags.evaluate import evaluate_bp
from blueprints.docs.docs import docs_bp


from errors.handlers import register_error_handlers

APP_PORT = Path(__file__).resolve().parent

def create_app() -> Flask:
    """
    Flask application factory.

    Returns:
        Flask: The Flask application instance.
    """
    load_dotenv()
    app = Flask(__name__)

    register_error_handlers(app)            # Register error handlers

    app.register_blueprint(health_bp)       # /health/
    app.register_blueprint(flags_admin_bp)  # /admin/flags/
    app.register_blueprint(evaluate_bp)     # /evaluate/
    app.register_blueprint(docs_bp)         # expose /openapi.yaml and /docs
    
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("BACKEND_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG","false").lower()=="true")
