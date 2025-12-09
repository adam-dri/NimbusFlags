# NimbusFlags/backend/repositories/db.py
"""Database connection utilities for NimbusFlags.

This module exposes a small helper to obtain PostgreSQL connections
using psycopg with dict-style rows.
"""


from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Make sure .env is configured."
    )


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Yield a psycopg connection configured with dict-style rows.

    The connection uses `dict_row` as row factory so that queries
    return dictionaries instead of tuples. The connection is always
    closed properly, even if an exception occurs.

    Yields:
        psycopg.Connection: An open database connection.
    """
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            yield conn
    except psycopg.OperationalError as exc:
        raise RuntimeError("Database connection failed.") from exc
