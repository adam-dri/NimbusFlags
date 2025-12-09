# NimbusFlags/backend/repositories/postgres_flags_repo.py
"""PostgreSQL-backed feature flag repository for NimbusFlags.

This module provides CRUD-style helpers to store and retrieve feature flags
in the ``flags`` table, scoped per client (multi-tenant).
"""


from typing import List, Optional
from uuid import UUID, uuid4

from psycopg import DatabaseError
from psycopg.types.json import Json

from .db import get_connection


def upsert_flag(client_id: UUID, flag_data: dict) -> dict:
    """Insert or update a flag for a given client.

    Expects ``flag_data`` to follow the ``flag_config.schema.json`` contract::

        {
            "key": str,
            "enabled": bool,
            "conditions": [...],
            "parameters": {...}
        }

    Behaviour:
        - If ``(client_id, key)`` does not exist:
            insert a new row with a fresh UUID.
        - If it exists: update ``enabled``, ``conditions``, ``parameters``, and
            ``updated_at``.

    Args:
        client_id: UUID of the client (tenant) owning the flag.
        flag_data: Dictionary describing the flag configuration.

    Returns:
        dict: The upserted flag record as returned by PostgreSQL.

    Raises:
        RuntimeError: If the underlying database operation fails.
    """
    key = flag_data["key"]
    enabled = flag_data["enabled"]
    conditions = flag_data.get("conditions", [])
    parameters = flag_data.get("parameters", {})

    sql = """
        INSERT INTO flags (
            id,
            client_id,
            key,
            enabled,
            conditions,
            parameters
        )
        VALUES (
            %(id)s,
            %(client_id)s,
            %(key)s,
            %(enabled)s,
            %(conditions)s,
            %(parameters)s
        )
        ON CONFLICT (client_id, key)
        DO UPDATE SET
            enabled = EXCLUDED.enabled,
            conditions = EXCLUDED.conditions,
            parameters = EXCLUDED.parameters,
            updated_at = NOW()
        RETURNING *;
    """

    params = {
        "id": uuid4(),
        "client_id": client_id,
        "key": key,
        "enabled": enabled,
        # IMPORTANT: explicit conversion to JSON for PostgreSQL JSONB columns.
        "conditions": Json(conditions),
        "parameters": Json(parameters),
    }

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return row
    except DatabaseError as exc:
        raise RuntimeError("Failed to upsert flag.") from exc


def get_flag_by_key(client_id: UUID, key: str) -> Optional[dict]:
    """Fetch a single flag for a given client and flag key.

    Args:
        client_id: UUID of the client (tenant).
        key: The flag key (unique per client).

    Returns:
        A dictionary representing the flag record if found, otherwise ``None``.
    """
    sql = """
        SELECT *
        FROM flags
        WHERE client_id = %(client_id)s
          AND key = %(key)s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"client_id": client_id, "key": key})
            row = cur.fetchone()
            return row


def list_flags_for_client(
    client_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    """List flags for a given client, with basic pagination.

    Args:
        client_id: UUID of the client (tenant).
        limit: Maximum number of flags to return.
        offset: Offset used for pagination.

    Returns:
        A list of dictionaries representing the flag records.
    """
    sql = """
        SELECT *
        FROM flags
        WHERE client_id = %(client_id)s
        ORDER BY key
        LIMIT %(limit)s
        OFFSET %(offset)s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "client_id": client_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            rows = cur.fetchall()
            return rows


def delete_flag(client_id: UUID, key: str) -> None:
    """Delete a flag for a given client and key.

    The operation is idempotent: attempting to delete a non-existent flag
    does not raise an error.

    Args:
        client_id: UUID of the client (tenant).
        key: The flag key to delete.

    Raises:
        RuntimeError: If the underlying database operation fails.
    """
    sql = """
        DELETE FROM flags
        WHERE client_id = %(client_id)s
          AND key = %(key)s;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"client_id": client_id, "key": key})
    except DatabaseError as exc:
        raise RuntimeError("Failed to delete flag.") from exc
