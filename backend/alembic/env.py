"""
Alembic migration environment.

Key decisions:
- Reads the database URL from app.core.config.settings (single source of truth).
- Imports Base.metadata so Alembic can auto-detect model changes.
  Every ORM model must be imported somewhere that is reachable from
  app.models.__init__ before autogenerate runs, otherwise Alembic
  cannot see the tables.
- Supports both offline (SQL script) and online (live DB) migration modes.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
# settings provides the real DATABASE_URL
from app.core.config import settings

# Base carries all ORM metadata.
from app.database.base import Base  # noqa: F401

# Import the models package so every ORM model is registered on
# Base.metadata before autogenerate inspects it.
# Adding a new model to app/models/__init__.py is all that is needed
# to include it in future migrations.
import app.models  # noqa: F401

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Inject the real database URL — overrides the placeholder in alembic.ini
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode — emit SQL to stdout without connecting
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render ALTER TABLE statements for column changes
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connect to the real database
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
