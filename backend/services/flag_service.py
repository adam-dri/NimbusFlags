# NimbusFlags/backend/services/flag_service.py
"""Flag evaluation service for NimbusFlags.

Provides a pure, stateless function to evaluate a single feature flag
for a given user context.
"""


from __future__ import annotations

from typing import Any, Dict


def evaluate_flag(
    flag: Dict[str, Any], user_attributes: Dict[str, Any]
) -> Dict[str, Any]:
    """Pure evaluation of a single feature flag for a given user.

    Args:
        flag: dict with at least:
            - "key": str
            - "enabled": bool
            - "conditions": list[dict] (each with attribute/operator/value)
            - "parameters": dict
        user_attributes: dict of user attributes (e.g. {"country": "CA"}).

    Rules (AND):
        - If flag.enabled == false -> enabled:false
        - For each condition:
            * operator 'equals':    user[attr] == value
            * operator 'in':        user[attr] in value (non-empty array)
            * missing attribute ->  enabled:false
        - If all conditions pass -> enabled:true + parameters

    Returns:
        A dict in the spirit of EvaluateResponse:
        {
            "flag_key": <str>,
            "enabled": <bool>,
            "parameters": <dict when enabled else {}>,
        }
    """

    flag_key = flag.get("key")

    # Kill switch
    if not flag.get("enabled", False):
        return {
            "flag_key": flag_key,
            "enabled": False,
            "parameters": {},
        }

    conditions = flag.get("conditions") or []

    def _matches_condition(cond: Dict[str, Any]) -> bool:
        attr = cond.get("attribute")
        operator = cond.get("operator")
        ref = cond.get("value")

        # Missing attribute in user -> fail
        if attr not in user_attributes:
            return False

        val = user_attributes[attr]

        if operator == "equals":
            return val == ref

        if operator == "in":
            # value is expected to be a non-empty list
            if not isinstance(ref, list) or not ref:
                return False
            return val in ref

        # Unknown operator -> fail closed
        return False

    # All conditions must pass
    for cond in conditions:
        if not _matches_condition(cond):
            return {
                "flag_key": flag_key,
                "enabled": False,
                "parameters": {},
            }

    # All conditions passed
    return {
        "flag_key": flag_key,
        "enabled": True,
        "parameters": flag.get("parameters") or {},
    }
