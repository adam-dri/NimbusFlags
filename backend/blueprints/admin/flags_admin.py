# NimbusFlags/backend/blueprints/admin/flags_admin.py
"""Admin-facing feature flag management endpoints for NimbusFlags.

Provides CRUD and listing operations on feature flags for an authenticated
client.
"""


from __future__ import annotations

from typing import Any

from flask import Blueprint, request, jsonify, g

from validators.flag_config_validator import validate_flag_config
from services.auth_service import require_api_key
from repositories import postgres_flags_repo


flags_admin_bp = Blueprint("flags_admin", __name__, url_prefix="/admin/flags")


def _serialize_flag(row: dict) -> dict:
    """Serialize a flag row (dict_row from psycopg) into a JSON-safe dict.

    Returns:
        dict: Serialized flag.
    """
    return {
        "id": str(row["id"]),
        "key": row["key"],
        "enabled": row["enabled"],
        "conditions": row["conditions"],
        "parameters": row["parameters"],
        "created_at": (
            row["created_at"].isoformat() if row.get("created_at") else None
        ),
        "updated_at": (
            row["updated_at"].isoformat() if row.get("updated_at") else None
        ),
    }


@flags_admin_bp.post("/")
@require_api_key
def post_upsert_flag() -> tuple[Any, int]:
    """Create or update a flag configuration for the authenticated client.

    - Requires a valid X-Api-Key header.
    - Validates the payload against flag_config.schema.json
      via validate_flag_config.
    - Uses postgres_flags_repo.upsert_flag(client_id, flag_data).

    Returns:
        tuple: (JSON response, HTTP status code).
    """
    payload = request.get_json(silent=True) or {}

    # Validate payload shape (raise / aborts 400 if invalid)
    validate_flag_config(payload)

    client_id = g.client_id

    # Repository expects a dict with keys: key, enabled, conditions, parameters
    row = postgres_flags_repo.upsert_flag(
        client_id=client_id,
        flag_data=payload,
    )

    return jsonify(_serialize_flag(row)), 200


@flags_admin_bp.get("/")
@require_api_key
def list_flags() -> tuple[Any, int]:
    """
    List flags for the authenticated client.

    Query params:
        - limit (optional, default 50)
        - offset (optional, default 0)

    Returns:
        tuple: (JSON list of flag representations, HTTP status code).
    """
    client_id = g.client_id

    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50

    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        offset = 0

    rows = postgres_flags_repo.list_flags_for_client(
        client_id=client_id,
        limit=limit,
        offset=offset,
    )

    return jsonify([_serialize_flag(r) for r in rows]), 200


@flags_admin_bp.get("/<string:key>")
@require_api_key
def get_flag_by_key(key: str) -> tuple[Any, int]:
    """Retrieve a flag configuration by its key for the authenticated client.

    Args:
        key: The key of the flag to retrieve.

    Returns:
        tuple: (JSON flag representation, HTTP status code).
               Returns 404 if the flag is not found.
    """
    client_id = g.client_id

    row = postgres_flags_repo.get_flag_by_key(client_id=client_id, key=key)
    if row is None:
        return (
            jsonify(
                {
                    "error": "Flag not found",
                    "code": "flags.not_found",
                }
            ),
            404,
        )

    return jsonify(_serialize_flag(row)), 200


@flags_admin_bp.delete("/<string:key>")
@require_api_key
def delete_flag(key: str) -> tuple[str, int]:
    """Delete a flag by its key for the authenticated client.

    Behaviour:
        - If the flag does not exist, we still return 204 (idempotent delete).
        - If stricter behaviour is desired (404 when not found),
          this can be changed later.

    Returns:
        tuple: ("", 204) on success.
    """
    client_id = g.client_id

    # postgres_flags_repo.delete_flag does not need to return anything.
    postgres_flags_repo.delete_flag(client_id=client_id, key=key)

    # No content on success
    return "", 204
