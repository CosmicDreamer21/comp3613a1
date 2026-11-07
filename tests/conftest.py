import os
import tempfile
from pathlib import Path

# Point the app at a throw-away database BEFORE the app is imported
_TMP = tempfile.mkdtemp(prefix="studentstay-tests-")
os.environ["DATABASE_URI"] = "sqlite:///" + Path(_TMP, "test.db").as_posix()
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789"
os.environ["ENV"] = "ci"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402


@pytest.fixture()
def db():
    """A clean database for every test."""
    import app.models  # noqa: F401  (registers the tables)
    from app.database import engine

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(db):
    from app.main import app

    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client