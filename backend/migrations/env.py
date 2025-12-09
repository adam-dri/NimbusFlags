from logging.config import fileConfig
import os  # Added: read DATABASE_URL from environment

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------------------------
# Added: derive the SQLAlchemy URL from DATABASE_URL.
# - DATABASE_URL is used by the app with psycopg (psycopg3).
# - For Alembic / SQLAlchemy we need an URL that points explicitly
#   to the "psycopg" driver instead of psycopg2.
#   So we transform:
#     postgresql://...  ->  postgresql+psycopg://...
# -------------------------------------------------------------------
raw_db_url = os.getenv("DATABASE_URL")
if not raw_db_url:
    raise RuntimeError("DATABASE_URL is not set. Export it before running Alembic.")

if raw_db_url.startswith("postgresql://"):
    sqlalchemy_url = raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    # Fallback: use the URL as-is if it already contains a driver or is custom
    sqlalchemy_url = raw_db_url

config.set_main_option("sqlalchemy.url", sqlalchemy_url)
# -------------------------------------------------------------------

# Add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
