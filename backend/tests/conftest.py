"""Shared pytest fixtures.

SAFETY: tests only ever touch TEST_DATABASE_URL (a local database whose name
contains "test"). DATABASE_URL is overridden before the app is imported, so
the test suite can never reach the real Supabase database.
"""

import os
from collections.abc import Iterator

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, to_sqlalchemy_url


class _TestEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")
    test_database_url: str | None = None


TEST_DATABASE_URL = _TestEnv().test_database_url
if TEST_DATABASE_URL:
    _name = make_url(to_sqlalchemy_url(TEST_DATABASE_URL)).database or ""
    if "test" not in _name:
        raise RuntimeError("TEST_DATABASE_URL must point at a database whose name contains 'test'.")

# Point the app at the test database (or at nothing) BEFORE importing it.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "postgresql://unused@127.0.0.1:1/unused_test"
os.environ["ENVIRONMENT"] = "test"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

requires_db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set in backend/.env")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Build a fresh schema with the real Alembic migrations (so migrations are tested too)."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set in backend/.env")
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.downgrade(config, "base")  # drop leftovers from an earlier run
    command.upgrade(config, "head")

    test_engine = create_engine(to_sqlalchemy_url(TEST_DATABASE_URL))
    yield test_engine
    test_engine.dispose()
    command.downgrade(config, "base")


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session inside a transaction that is rolled back after each test.

    join_transaction_mode="create_savepoint": code under test may call
    commit(); that only releases a SAVEPOINT, and the outer transaction is
    still rolled back at the end, so tests never affect one another.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def seeded_db(db: Session) -> Session:
    from app.services.seeding import load_seed_records, seed_applications

    seed_applications(db, load_seed_records(get_settings().seed_data_dir))
    return db


@pytest.fixture
def client(seeded_db: Session) -> Iterator["TestClient"]:  # noqa: F821
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    # Make every request use the test session instead of opening its own.
    app.dependency_overrides[get_db] = lambda: seeded_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
