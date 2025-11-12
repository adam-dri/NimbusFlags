from pathlib import Path
import json
from jsonschema import validate as js_validate, ValidationError
from errors.handlers import BadRequest

# Resolve schema path
SCHEMA_PATH = (Path(__file__).resolve().parent.parent / "schemas" / "flag_config.schema.json")

# Load schema
with SCHEMA_PATH.open("r", encoding="utf-8") as f:
    FLAG_CONFIG_SCHEMA = json.load(f)


def validate_flag_config(payload: dict) -> None:
    """
    Validate admin FlagConfig payload against schema.
    
    Args:
        Ppayload: Parsed JSON body for flag configuration.
    
    Raises:
        BadRequest: If payload is not an object pr violates the schema.
    """
    if not isinstance(payload, dict):
        raise BadRequest("Body myst be a JSON object.")
    
    try:
        js_validate(instance=payload, schema=FLAG_CONFIG_SCHEMA)
    except ValidationError as e:
        msg = getattr(e, "message", None) or str(e)
        raise BadRequest(f"Invalid FlagConfig: {msg}")