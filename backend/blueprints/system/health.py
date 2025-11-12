from flask import Blueprint, jsonify

health_bp = Blueprint("health_bp", __name__, url_prefix="/health")

@health_bp.get("/")
def health() -> jsonify:
    """
    Health probe.

    Returns:
        {"status": "ok"}
    """
    return jsonify({"status": "ok"})
