from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from support.database import (
    configure_test_environment,
    create_test_engine,
    create_transactional_session,
    upgrade_test_database,
)

TEST_DATABASE_URL = configure_test_environment()


@pytest.fixture(
    scope="session",
    autouse=True,
)
def migrated_test_database() -> Iterator[None]:
    upgrade_test_database()
    yield


@pytest.fixture(scope="session")
def test_engine(
    migrated_test_database: None,
) -> Iterator[Engine]:
    engine = create_test_engine(TEST_DATABASE_URL)

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(
    test_engine: Engine,
) -> Iterator[Session]:
    session, transaction, connection = create_transactional_session(test_engine)

    try:
        yield session
    finally:
        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()


@pytest.fixture
def client(
    db_session: Session,
) -> Iterator[TestClient]:
    from app.db.session import get_db
    from app.main import app

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(
            get_db,
            None,
        )
