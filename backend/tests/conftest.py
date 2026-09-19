from __future__ import annotations

import pytest

from app.config import settings
from app.main import app
from app.seed import reset_and_seed
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    settings.database_path = tmp_path / "app.db"
    reset_and_seed()
    with TestClient(app) as test_client:
        yield test_client
