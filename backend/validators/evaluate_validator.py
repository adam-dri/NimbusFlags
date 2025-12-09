# NimbusFlags/backend/validators/evaluate_validator.py
"""
Validator for /evaluate/ requests using JSON Schema.

This module loads the EvaluateRequest JSON Schema once at import time and
exposes a helper to validate incoming payloads, raising BadRequest on error.
"""


from pathlib import Path
import json
from jsonschema import validate as js_validate, ValidationError
from errors.handlers import BadRequest


# Resovle schema path
SCHEMA_PATH = (
    Path(__file__).parent.parent / "schemas" / "EvaluateRequest.schema.json"
)

# Load schema
with SCHEMA_PATH.open("r", encoding="utf-8") as f:
    EVALUATE_REQUEST_SCHEMA = json.load(f)


def validate_eval_payload(payload: dict) -> None:
    """
    Validate the evaluation request body against the EvaluateRequest schema.

    Args:
        payload: Parsed JSON body.

    Raises:
        BadRequest: If payload is not JSON or doesn't match the schema.
    """
    if not isinstance(payload, dict):
        raise BadRequest("Payload must be a JSON object.")

    try:
        js_validate(instance=payload, schema=EVALUATE_REQUEST_SCHEMA)
    except ValidationError as e:
        msg = getattr(e, "message", None) or str(e)
        raise BadRequest(f"Invalid EvaluateRequest: {msg}")
