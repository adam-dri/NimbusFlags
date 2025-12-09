"""add_sessions_table

Revision ID: 4829abd40b76
Revises: create_clients_and_flags
Create Date: 2025-12-02 19:01:17.095374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4829abd40b76'
down_revision: Union[str, None] = 'create_clients_and_flags'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE sessions (
            id UUID PRIMARY KEY,
            client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            revoked BOOLEAN NOT NULL DEFAULT FALSE
        );
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_sessions_token_hash ON sessions (token_hash);
        """
    )

    op.execute(
        """
        CREATE INDEX ix_sessions_client_id ON sessions (client_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sessions_client_id;")
    op.execute("DROP INDEX IF EXISTS uq_sessions_token_hash;")
    op.execute("DROP TABLE IF EXISTS sessions;")