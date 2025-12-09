# NIimbusFlags/backend/repositories/memory_repo.py
"""In-memory feature flag repository for NimbusFlags.

This repository keeps flag configurations in process memory. It is mainly
useful for local experiments or tests and is not persisted.
"""


from __future__ import annotations

from typing import Dict, List, Optional

# In-memory store keyed by flag "key"
_FLAG: Dict[str, dict] = {}


def save_flag(flag_dict: dict) -> None:
    """Upsert a flag configuration by its ``key`` in the in-memory store.

    Args:
        flag_dict: A dictionary representing the flag configuration.
            Must contain a ``"key"`` field used as the identifier.

    Returns:
        None.
    """
    key = flag_dict["key"]
    _FLAG[key] = flag_dict


def get_flag_by_key(key: str) -> Optional[dict]:
    """Retrieve a single flag configuration by its key.

    Args:
        key: The flag key to look up.

    Returns:
        The flag configuration dictionary if present, otherwise ``None``.
    """
    return _FLAG.get(key)


def list_flags() -> List[dict]:
    """Return all stored flag configurations.

    This is primarily used for debug or admin-style listing.

    Returns:
        A list of all flag configuration dictionaries currently stored.
    """
    return list(_FLAG.values())
