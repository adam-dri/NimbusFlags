from flask import Blueprint, request, jsonify
from validators.evaluate_validator import validate_eval_payload
from services.flag_service import evaluate_flag

evaluate_bp = Blueprint("evaluate_bp", __name__, url_prefix="/evaluate")

@evaluate_bp.post("/")
def post_evaluate() -> jsonify:
    """
    Evaluate a flag for a user (public API, MVP, placeholder).
    
    Body (JSON):
        EvaluateRequest:
        - flag_key: str
        - user_attributes: dict
    
    Returns:
        200 with a placeholder payload for now.
    """

    payload = request.get_json(silent=True) or {}
    validate_eval_payload(payload)  # 404 if invalid

    result = evaluate_flag(
        flag_key=payload["flag_key"],
        user_attributes=payload["user_attributes"],
    )
    return jsonify(result), 200