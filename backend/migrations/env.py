"""Alembic migration environment: tells Alembic which database and which models."""

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (registers the models on Base.metadata)
from app.core.config import get_settings, to_sqlalchemy_url
from app.db.session import Base

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    # Tests pass a URL explicitly (config.attributes); otherwise use DATABASE_URL.
    explicit = config.attributes.get("database_url")
    return to_sqlalchemy_url(explicit) if explicit else get_settings().database_url


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: print the SQL instead of running it."""
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config({"sqlalchemy.url": database_url()}, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
