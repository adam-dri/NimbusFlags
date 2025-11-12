from flask import Blueprint, request, jsonify
from validators.flag_config_validator import validate_flag_config
from services.flag_service import upsert_flag, get_flag

flags_admin_bp = Blueprint('flags_admin', __name__, url_prefix='/admin/flags')


@flags_admin_bp.post("/")
def post_upsert_flag() -> jsonify:
    """
    Create or update a flag configuration (admin, MVP placeholder).

    Body (JSON):
        Expected to match the FlagConfig (MVP) later.
    
    Returns:
        200 with a placeholder payload for now: {"todo": "..."}.
    """
    payload = request.get_json(silent=True) or {}
    validate_flag_config(payload)       # 400 JSON if invalid
    upsert_flag(payload)                # save to in-memory repo
    return jsonify({"ok": True}), 200   # minimal succes response


@flags_admin_bp.get("/<string:key>")
def get_flag_by_key(key: str) -> jsonify:
    """
    Retrieve a flag configuration by its public key.
    """
    flag = get_flag(key)  # 404 if not found
    return jsonify(flag), 200