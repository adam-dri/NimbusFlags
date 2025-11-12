from typing import Dict, List, Optional

# In-memory store keyed by flag "key"
_FLAG: Dict[str, dict] = {}


def save_flag(flag_dict: dict) -> None:
    """
    Upsert a flag configuration by its 'key'.
    """
    key = flag_dict["key"]
    _FLAG[key] = flag_dict

def get_flag_by_key(key: str) -> Optional[dict]:
    """
    Return a flag configuration or None if not found.
    """
    return _FLAG.get(key)

def list_flags() -> List[dict]:
    """
    Return all flag configurations (for debug/admin).
    """
    return list(_FLAG.values())