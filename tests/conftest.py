import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="wren-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MODEL_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app.core.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    def _make(email="t@example.com", password="hunter2secret"):
        r = client.post("/api/auth/register", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
