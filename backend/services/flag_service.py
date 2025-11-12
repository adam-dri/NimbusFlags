from typing import Dict, Any
from repositories.memory_repo import save_flag, get_flag_by_key
from errors.handlers import NotFound


def upsert_flag(flag_dict: Dict[str, Any]) -> None:
    """
    Create or update a validated FlagConfig.
    """
    save_flag(flag_dict)

def get_flag(key: str) -> Dict[str, Any]:
    """
    Return a flag config by key or raise NotFound.
    """
    flag = get_flag_by_key(key)
    if not flag:
        raise NotFound("Flag not found.")
    return flag

def evaluate_flag(flag_key: str, user_attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute evaluation of a given flag and user attributes (MVP).

    Rules (AND):
        - If flag.enabled == false -> enabled:false
        - For each condition:
            * operator 'equals':    user[attr] == value
            * operator 'in':        user[attr] in value (value must be a non-empty array)
            * missing attribute ->  enabled:false
        - If all conditions pass -> enabled:true + parameters
    """
    flag = get_flag_by_key(flag_key)
    if not flag:
        raise NotFound("Flag not found.")
    
    # Kill switch
    if not flag.get("enabled", False):
        return {"enabled": False}
    
    conditions = flag.get("conditions", [])
    for condition in conditions:
        attr = condition["attribute"]
        operator = condition["operator"]
        ref = condition["value"]
        
        # Attribute must be present
        if attr not in user_attributes:
            return {"enabled": False}
        

        val = user_attributes[attr]
        if operator == "equals":
            if val != ref:
                return {"enabled": False}
        elif operator == "in":
            if not isinstance(ref, list) or not ref or val not in ref:
                return {"enabled": False}
        else:
            return {"enabled": False}  # Unknown operator
        
    # All conditions passed
    return {
        "enabled": True,
        "parameters": flag.get("parameters", {}),
    }