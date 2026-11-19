import os
from uuid import uuid4
from pathlib import Path

import pytest
from tests.database_safety import validate_test_database


BACKEND_DIR = Path(__file__).resolve().parents[1]
# Validate both the process environment and backend/.env before importing app/db
# modules or changing DATABASE_URL. Nothing that creates an engine runs above this line.
test_database_url = validate_test_database(os.environ, BACKEND_DIR / ".env")
os.environ["DATABASE_URL"] = test_database_url

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from fastapi.testclient import TestClient


alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
command.upgrade(alembic_config, "head")

from app.db.seed_data import seed_database  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


class StockFlowTestClient(TestClient):
    def request(self, method, url, *args, **kwargs):
        if method.upper() == "POST" and "/movements/" in str(url):
            headers = dict(kwargs.pop("headers", {}) or {})
            headers.setdefault("Idempotency-Key", str(uuid4()))
            kwargs["headers"] = headers
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(autouse=True)
def reset_test_database():
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE import_batches, idempotency_records, activity_history, "
                "stock_movements, inventory_balances, products, stores RESTART IDENTITY CASCADE"
            )
        )
    with SessionLocal() as session:
        seed_database(session)
    yield


@pytest.fixture
def client():
    with StockFlowTestClient(app) as test_client:
        yield test_client
