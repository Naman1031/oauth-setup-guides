"""Create the local test database named in TEST_DATABASE_URL, if it doesn't exist.

Usage (from backend/):  python -m scripts.create_test_database
Reads TEST_DATABASE_URL from backend/.env, so the password never has to be typed on the command line.
"""

import sys

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import BACKEND_DIR, to_sqlalchemy_url


class TestDbSettings(BaseSettings):
    __test__ = False  # tell pytest this is not a test class
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")
    test_database_url: str


def main() -> int:
    url = make_url(to_sqlalchemy_url(TestDbSettings().test_database_url))  # type: ignore[call-arg]
    name = url.database or ""
    if "test" not in name:
        print("Refusing: the test database name must contain 'test'.", file=sys.stderr)
        return 1
    # Connect to the default 'postgres' database to create the new one.
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name})
        if exists:
            print(f"Database {name!r} already exists.")
        else:
            # Database names can't be bound parameters; `name` is checked to be a plain identifier.
            if not name.replace("_", "").isalnum():
                print("Refusing: database name must be letters, digits and underscores.", file=sys.stderr)
                return 1
            conn.execute(text(f'CREATE DATABASE "{name}"'))
            print(f"Created database {name!r}.")
    admin.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
