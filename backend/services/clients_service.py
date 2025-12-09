# NimbusFlags/backend/services/clients_service.py
"""Client domain model and authentication helpers for NimbusFlags.

This module centralizes:
- The Client dataclass (internal representation of a tenant).
- Password hashing/verification (bcrypt).
- API key generation + hashing.
- Client registration and lookup helpers.
- Authentication helpers for email/password and session tokens.
"""


from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

import bcrypt

try:
    # When running app.py directly (backend directory on sys.path)
    from services.sessions_service import get_active_session_for_token
except ImportError:  # pragma: no cover - backend package context
    from backend.services.sessions_service import get_active_session_for_token
try:
    # Case 1: imported as part of the `backend` package (tests, tooling, etc.)
    from ..repositories import clients_repo  # type: ignore[import]
except ImportError:
    # Case 2: app is run directly from the `backend` directory
    # and `services` / `repositories` are top-level packages.
    from repositories import clients_repo  # type: ignore[import]


API_KEY_PREFIX = "nf_live_"


@dataclass(frozen=True)
class Client:
    """Domain model for a NimbusFlags client.

    Internal representation used by services and handlers.
    We never store or expose password_hash or api_key_hash on this model.
    """
    id: UUID
    email: str
    subscription_tier: str
    active: bool
    created_at: datetime


class ClientAlreadyExistsError(Exception):
    """Raised when registering a client with an existing email."""
    pass


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        plain_password: The raw password provided by the user.

    Returns:
        str: The bcrypt hash of the password.

    Raises:
        ValueError: If the password is empty.
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")

    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The raw password to verify.
        password_hash: The stored bcrypt hash.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    if not plain_password or not password_hash:
        return False

    password_bytes = plain_password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")

    try:
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except ValueError:
        # In case the stored hash is malformed
        return False


def generate_api_key() -> str:
    """Generate a new API key for a client.

    Format: ``"nf_live_<random_urlsafe_token>"``.

    The whole string (including prefix) will be hashed and stored in DB.
    The plaintext value is returned ONCE to the caller.

    Returns:
        str: The newly generated plaintext API key.
    """
    token = secrets.token_urlsafe(32)
    return f"{API_KEY_PREFIX}{token}"


def hash_api_key(api_key: str) -> str:
    """Hash the API key using SHA-256.

    This is what is stored in the database in ``clients.api_key_hash``.

    Args:
        api_key: The plaintext API key.

    Returns:
        str: Hex digest of the SHA-256 hash of the API key.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _row_to_client(row: dict) -> Client:
    """Convert a raw dict (from psycopg row_factory=dict_row) into a Client.

    Args:
        row: A database row from the ``clients`` table.

    Returns:
        Client: The corresponding Client domain model.
    """
    return Client(
        id=row["id"],
        email=row["email"],
        subscription_tier=row["subscription_tier"],
        active=row["active"],
        created_at=row["created_at"],
    )


def register_client(email: str, password: str) -> tuple[Client, str]:
    """Register a new client.

    Steps:
        - Normalize and validate email.
        - Check if email is already in use.
        - Hash password with bcrypt.
        - Generate an API key (plaintext) and hash it (SHA-256).
        - Persist the client via ``clients_repo.create_client(...)``.
        - Return ``(Client, api_key_plaintext)``.

    Args:
        email: The client email to register.
        password: The plaintext password.

    Raises:
        ClientAlreadyExistsError: If the email is already registered.
        ValueError: For invalid email or empty password.
        RuntimeError: May bubble up from the repository in case of DB issues.

    Returns:
        tuple[Client, str]: The created Client and the plaintext API key.
    """
    normalized_email = email.strip().lower()
    if "@" not in normalized_email:
        raise ValueError("Invalid email format.")

    if not password:
        raise ValueError("Password cannot be empty.")

    existing = clients_repo.get_client_by_email(normalized_email)
    if existing is not None:
        raise ClientAlreadyExistsError(
                    f"Email '{normalized_email}' is already registered."
                )

    password_hash = hash_password(password)

    api_key_plain = generate_api_key()
    api_key_hash = hash_api_key(api_key_plain)

    # For now, everyone starts as "free".
    row = clients_repo.create_client(
        email=normalized_email,
        password_hash=password_hash,
        api_key_hash=api_key_hash,
        subscription_tier="free",
    )

    client = _row_to_client(row)
    return client, api_key_plain


def resolve_client_by_api_key(api_key: str) -> Optional[Client]:
    """Resolve a client from a given API key.

    Behaviour:
        - If the API key is missing or has a wrong prefix -> return ``None``.
        - Hash the API key (SHA-256) and look it up via
          ``clients_repo.get_client_by_api_key_hash()``.
        - If not found or client is inactive -> return ``None``.
        - Else return a ``Client`` instance.

    This is intentionally "forgiving" and returns ``None`` instead of raising,
    so that the HTTP layer can simply translate it to 401/403.

    Args:
        api_key: The plaintext API key provided by the caller.

    Returns:
        Optional[Client]: The resolved Client or ``None`` if not found/invalid.
    """
    if not api_key:
        return None

    if not api_key.startswith(API_KEY_PREFIX):
        return None

    api_key_hash = hash_api_key(api_key)
    row = clients_repo.get_client_by_api_key_hash(api_key_hash)

    if row is None:
        return None

    if not row.get("active", False):
        return None

    return _row_to_client(row)


def deactivate_client(client_id: UUID) -> None:
    """Deactivate a client by its UUID.

    Notes:
        - Current DB schema does NOT have ``deleted_at``.
        - For now, this would eventually just set ``active = false``
            (and maybe rotate the API key).
        - To be implemented later (future sprint), likely with an
            Alembic migration if we add ``deleted_at`` or more audit fields.

    Args:
        client_id: The client's UUID.

    Raises:
        NotImplementedError: Always, until implemented in a future sprint.
    """
    raise NotImplementedError("deactivate_client() is not implemented yet.")


def authenticate_client(email: str, password: str) -> Client | None:
    """Authenticate a client using email and password.

    This is used by the login endpoint to validate credentials
    without exposing password hashes or leaking whether the email
    exists in the system.

    Steps:
      - Normalize the email (strip + lowercase).
      - Lookup the client row by email.
      - Verify the provided password against the stored hash.
      - Map the database row to a Client dataclass.

    Args:
        email: The client email as provided by the user.
        password: The plaintext password entered by the user.

    Returns:
        Client | None: The authenticated Client instance if the
        credentials are valid, otherwise None.
    """
    normalized_email = email.strip().lower()
    row = clients_repo.get_client_by_email(normalized_email)
    if row is None:
        # Do not leak whether the email exists.
        return None

    if not verify_password(password, row["password_hash"]):
        return None

    return _row_to_client(row)


def resolve_client_by_session_token(raw_token: str) -> Client | None:
    """
    Resolve a client from a session token.

    This is used by session-base authentication (dashboard login).

    Steps:
        - Validate the raw token (non-empty, correct prefix) indirectly
        via :func:`get_active_session_for_token`.
        - Look up the session in the ``sessions`` table.
        - Fetch the corresponding client row by ``client_id``.
        - Return a Client dataclass if the account is active.

    Args:
        raw_token: The raw session token as provided by the frontend
            (for exemple in the ``X-Session-Token``header).

    Returns:
        Client | None: The resolved Client if the token is valid,
        not expired and the accout is active; otherwise None.
    """
    if not raw_token:
        return None

    session = get_active_session_for_token(raw_token)
    if session is None:
        return None

    row = clients_repo.get_client_by_id(session.client_id)
    if row is None:
        # Session exists but client row is gone.
        return None

    if not row["active"]:
        # Do not authenticate inactive tenants.
        return None

    return _row_to_client(row)
