# NimbusFlags/backend/repositories/clients_repo.py
"""PostgreSQL repository helpers for the `clients` table.

This module contains low-level data access functions for creating and
retrieving clients. Business rules and validation live in the
`services.clients_service` layer.
"""


from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from psycopg import DatabaseError

from .db import get_connection


def create_client(
    email: str,
    password_hash: str,
    api_key_hash: str,
    subscription_tier: str = "free",
) -> dict:
    """Insert a new client into the database.

    This function:
        - Generates a UUID in Python (uuid4)
            to avoid depending on DB extensions.
        - Lets the database set `active` (DEFAULT TRUE)
            and `created_at` (DEFAULT NOW()).

    Args:
        email: Client email address (must be unique).
        password_hash: Bcrypt-hashed password string.
        api_key_hash: SHA-256 hash of the client's API key.
        subscription_tier:
            Optional subscription tier label, defaults to "free".

    Returns:
        The newly created client record as a dictionary.

    Raises:
        RuntimeError: If the underlying database operation fails.
    """
    client_id = uuid4()

    sql = """
        INSERT INTO clients (
            id,
            email,
            password_hash,
            api_key_hash,
            subscription_tier
        )
        VALUES (
            %(id)s,
            %(email)s,
            %(password_hash)s,
            %(api_key_hash)s,
            %(subscription_tier)s
        )
        RETURNING *;
    """

    params = {
        "id": client_id,
        "email": email,
        "password_hash": password_hash,
        "api_key_hash": api_key_hash,
        "subscription_tier": subscription_tier,
    }

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return row
    except DatabaseError as exc:
        raise RuntimeError("Failed to create client.") from exc


def get_client_by_id(client_id: UUID) -> Optional[dict]:
    """Fetch a client by its UUID.

    Args:
        client_id: The UUID of the client to retrieve.

    Returns:
        The client record as a dictionary if found, otherwise None.
    """
    sql = """
        SELECT *
        FROM clients
        WHERE id = %(id)s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"id": client_id})
            row = cur.fetchone()
            return row


def get_client_by_email(email: str) -> Optional[dict]:
    """Fetch a client by its email address.

    Args:
        email: The email address of the client to retrieve.

    Returns:
        The client record as a dictionary if found, otherwise None.
    """
    sql = """
        SELECT *
        FROM clients
        WHERE email = %(email)s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"email": email})
            row = cur.fetchone()
            return row


def get_client_by_api_key_hash(api_key_hash: str) -> Optional[dict]:
    """Fetch a client by its API key hash.

    Args:
        api_key_hash: The SHA-256 hash of the client's API key.

    Returns:
        The client record as a dictionary if found, otherwise None.
    """
    sql = """
        SELECT *
        FROM clients
        WHERE api_key_hash = %(api_key_hash)s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"api_key_hash": api_key_hash})
            row = cur.fetchone()
            return row
