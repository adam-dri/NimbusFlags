"""Runtime evaluation endpoint for NimbusFlags feature flags.

This blueprint exposes the public `/evaluate/` API used by client
applications to check whether a flag is enabled for a given user
context.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, g, request

from repositories import postgres_flags_repo
from services.auth_service import require_api_key
from services.flag_service import evaluate_flag
from validators.evaluate_validator import validate_eval_payload


evaluate_bp = Blueprint("evaluate_bp", __name__, url_prefix="/evaluate")


@evaluate_bp.post("/")
@require_api_key
def post_evaluate() -> tuple[Any, int]:
    """Evaluate a flag for a user (public API).

    Request JSON body (EvaluateRequest):
        {
            "flag_key": "string",
            "user_attributes": { ... }
        }

    Behaviour:
        - Requires a valid ``X-Api-Key`` header (tenant authentication).
        - Looks up the flag for the authenticated client in Postgres.
        - Returns 404 with {"error": "NotFound"} if the flag does not exist.
        - Otherwise applies the flag evaluation logic and returns 200
            with the evaluation result.

    Returns:
        A tuple ``(response, status_code)`` where:
            - ``response`` is a JSON response produced by ``jsonify``.
            - ``status_code`` is 200 on success or 404 if the flag is
                not found.
    """
    payload = request.get_json(silent=True) or {}
    validate_eval_payload(payload)

    client_id = g.client_id
    flag_key = payload["flag_key"]

    # Multi-tenant lookup in Postgres
    row = postgres_flags_repo.get_flag_by_key(
        client_id=client_id, key=flag_key
    )
    if row is None:
        return jsonify({"error": "NotFound"}), 404

    result = evaluate_flag(
        flag=row,
        user_attributes=payload["user_attributes"],
    )

    return jsonify(result), 200
