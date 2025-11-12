# ~/NimbusFlags/backend/blueprints/docs/docs.py
from flask import Blueprint, send_from_directory, jsonify, current_app
from pathlib import Path

# Absolute routes: /openapi.yaml, /schemas/*, /docs
docs_bp = Blueprint("docs_bp", __name__)

@docs_bp.get("/openapi.yaml")
def get_openapi_yaml():
    """
    Serve the OpenAPI spec file located at backend/docs/openapi.yaml.
    """
    backend_dir = Path(current_app.root_path)         # resolved at request time
    docs_dir = backend_dir / "docs"
    spec = docs_dir / "openapi.yaml"
    if not spec.exists():
        return jsonify({
            "error": "NotFound",
            "detail": "openapi.yaml not found",
            "tried": str(spec)
        }), 404
    return send_from_directory(docs_dir, "openapi.yaml", mimetype="text/yaml")

@docs_bp.get("/schemas/<path:filename>")
def get_schema_file(filename: str):
    """
    Serve JSON schema files used by OpenAPI $refs (from backend/schemas).
    """
    backend_dir = Path(current_app.root_path)         # resolved at request time
    schemas_dir = backend_dir / "schemas"
    target = schemas_dir / filename
    if not target.exists():
        return jsonify({
            "error": "NotFound",
            "detail": filename,
            "tried": str(target)
        }), 404
    return send_from_directory(schemas_dir, filename, mimetype="application/json")

@docs_bp.get("/docs")
def swagger_ui():
    """
    Minimal Swagger UI (CDN) pointing to /openapi.yaml.
    """
    return """
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <title>NimbusFlags API Docs</title>
            <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css"/>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
            <script>
            window.ui = SwaggerUIBundle({ url: '/openapi.yaml', dom_id: '#swagger-ui' });
            </script>
        </body>
        </html>
    """, 200, {"Content-Type": "text/html; charset=utf-8"}
