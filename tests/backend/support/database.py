from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
LOCAL_TEST_ENV_FILE = BACKEND_ROOT / ".env.test"

TEST_DATABASE_ENV_NAME = "TEST_DATABASE_URL"
EXPECTED_TEST_DATABASE_SUFFIX = "_test"


def _read_env_value(
    path: Path,
    key: str,
) -> str | None:
    if not path.is_file():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        name, separator, value = line.partition("=")

        if separator and name.strip() == key:
            return value.strip().strip('"').strip("'")

    return None


def get_test_database_url() -> str:
    database_url = os.environ.get(TEST_DATABASE_ENV_NAME)

    if not database_url:
        database_url = _read_env_value(
            LOCAL_TEST_ENV_FILE,
            TEST_DATABASE_ENV_NAME,
        )

    if not database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is required. Run ./scripts/db/setup-test-db.sh first."
        )

    parsed_url = make_url(database_url)
    _validate_test_database_url(parsed_url)

    return database_url


def _validate_test_database_url(
    parsed_url: URL,
) -> None:
    if parsed_url.get_backend_name() != "postgresql":
        raise RuntimeError("Backend tests require PostgreSQL.")

    database_name = parsed_url.database or ""

    if not database_name.endswith(EXPECTED_TEST_DATABASE_SUFFIX):
        raise RuntimeError(
            "Refusing to run database tests against "
            "a database whose name does not end in '_test'."
        )


def configure_test_environment() -> str:
    database_url = get_test_database_url()

    # Force every application import during pytest to use the
    # isolated database, regardless of backend/.env.
    os.environ["DATABASE_URL"] = database_url
    os.environ["APP_ENV"] = "test"

    return database_url


def create_test_engine(
    database_url: str,
) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def upgrade_test_database() -> None:
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))

    command.upgrade(
        alembic_config,
        "head",
    )


def create_transactional_session(
    engine: Engine,
) -> tuple[Session, object, object]:
    connection = engine.connect()
    outer_transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    return (
        session,
        outer_transaction,
        connection,
    )
