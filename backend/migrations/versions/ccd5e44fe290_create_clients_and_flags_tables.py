from alembic import op


# revision identifiers, used by Alembic.
revision = "create_clients_and_flags"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create clients and flags tables."""
    # Create clients table
    op.execute(
        """
        CREATE TABLE clients (
            id UUID PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            api_key_hash TEXT NOT NULL UNIQUE,
            subscription_tier TEXT NOT NULL DEFAULT 'free',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT clients_subscription_tier_check
                CHECK (subscription_tier IN ('free', 'essential', 'premium', 'ultimate'))
        );
        """
    )

    # Create flags table
    op.execute(
        """
        CREATE TABLE flags (
            id UUID PRIMARY KEY,
            client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            enabled BOOLEAN NOT NULL,
            conditions JSONB NOT NULL DEFAULT '[]',
            parameters JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT flags_client_key_unique UNIQUE (client_id, key)
        );
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS flags;")
    op.execute("DROP TABLE IF EXISTS clients;")
