"""Documentation endpoints for NimbusFlags (OpenAPI spec, schemas, Swagger UI).

This blueprint serves:
- the OpenAPI YAML file
- JSON Schema files referenced by OpenAPI
- a minimal Swagger UI pointing to /openapi.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, send_from_directory

# Absolute routes: /openapi.yaml, /schemas/*, /docs
docs_bp = Blueprint("docs_bp", __name__)


@docs_bp.get("/openapi.yaml")
def get_openapi_yaml() -> Any:
    """Serve the OpenAPI spec file located at backend/docs/openapi.yaml.

    Returns:
        A Flask response streaming ``openapi.yaml`` with
        ``text/yaml`` mimetype, or a JSON error payload with a 404
        status code if the file cannot be found.
    """
    backend_dir = Path(current_app.root_path)  # resolved at request time
    docs_dir = backend_dir / "docs"
    spec = docs_dir / "openapi.yaml"

    if not spec.exists():
        return (
            jsonify(
                {
                    "error": "NotFound",
                    "detail": "openapi.yaml not found",
                    "tried": str(spec),
                }
            ),
            404,
        )

    return send_from_directory(docs_dir, "openapi.yaml", mimetype="text/yaml")


@docs_bp.get("/schemas/<path:filename>")
def get_schema_file(filename: str) -> Any:
    """Serve JSON schema files used by OpenAPI ``$ref``s.

    Files are loaded from ``backend/schemas``.

    Args:
        filename: Relative path of the schema file under the ``schemas``
            directory.

    Returns:
        A Flask response streaming the JSON schema with
        ``application/json`` mimetype, or a JSON error payload with a
        404 status code if the file does not exist.
    """
    backend_dir = Path(current_app.root_path)  # resolved at request time
    schemas_dir = backend_dir / "schemas"
    target = schemas_dir / filename

    if not target.exists():
        return (
            jsonify(
                {
                    "error": "NotFound",
                    "detail": filename,
                    "tried": str(target),
                }
            ),
            404,
        )

    return send_from_directory(
        schemas_dir,
        filename,
        mimetype="application/json",
    )


@docs_bp.get("/docs")
def swagger_ui() -> tuple[str, int, dict[str, str]]:
    """Serve a minimal Swagger UI pointing to ``/openapi.yaml``.

    The HTML page loads Swagger UI assets from a public CDN and
    configures them to fetch the OpenAPI document from the local
    ``/openapi.yaml`` endpoint.

    Returns:
        A tuple ``(html, status_code, headers)`` suitable for Flask,
        where ``html`` is the Swagger UI page, ``status_code`` is 200,
        and ``headers`` sets the ``Content-Type`` to HTML UTF-8.
    """
    return (
        """
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <title>NimbusFlags API Docs</title>
            <link rel="stylesheet"
                  href="https://unpkg.com/swagger-ui-dist/swagger-ui.css"/>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
            <script>
            window.ui = SwaggerUIBundle({
                url: '/openapi.yaml',
                dom_id: '#swagger-ui'
            });
            </script>
        </body>
        </html>
        """,
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )
