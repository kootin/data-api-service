import mongomock
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    settings = Settings(database_url="sqlite://", api_keys="test-key,other-key")
    app = create_app(settings, mongo_client=mongomock.MongoClient())
    with TestClient(app, headers={"X-API-Key": "test-key"}) as c:
        yield c


@pytest.fixture
def seeded(client):
    client.put(
        "/instruments/JPM",
        json={"symbol": "JPM", "name": "JPMorgan Chase & Co", "asset_class": "Equity", "currency": "USD"},
    )
    closes = [100, 110, 99, 105, 120]
    body = [
        {
            "symbol": "JPM",
            "price_date": f"2026-10-0{i + 1}",
            "open": c,
            "high": c + 1,
            "low": c - 1,
            "close": c,
            "volume": 1000,
        }
        for i, c in enumerate(closes)
    ]
    assert client.post("/prices:bulk", json=body).status_code == 200
    return client
