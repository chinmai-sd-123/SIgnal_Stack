import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ["OPENAI_API_KEY"] = ""
os.environ["ENABLE_LLM_SUMMARIZATION"] = "false"
os.environ["PUBLIC_BASE_URL"] = "http://test.local"

if os.getenv("DATABASE_URL_TEST"):
    os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL_TEST")
else:
    os.environ["DATABASE_URL"] = ""


def _require_test_db_url():
    return os.getenv("DATABASE_URL_TEST")


@pytest.fixture(scope="session")
def app_with_overrides():
    test_db_url = _require_test_db_url()
    if not test_db_url:
        pytest.skip("DATABASE_URL_TEST not set; skipping integration tests.")

    os.environ["DATABASE_URL"] = test_db_url
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["ENABLE_LLM_SUMMARIZATION"] = "false"
    os.environ["PUBLIC_BASE_URL"] = "http://test.local"

    from app.config import database as db
    from app.main import app

    engine = create_engine(test_db_url)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db.Base.metadata.create_all(bind=engine)

    return app, db, engine, TestingSessionLocal


@pytest.fixture(scope="function")
def db_session(app_with_overrides):
    app, db, engine, TestingSessionLocal = app_with_overrides

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(app_with_overrides, db_session):
    app, db, engine, TestingSessionLocal = app_with_overrides

    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db.get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
