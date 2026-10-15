from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.config import Settings
from app.main import create_app


def test_sql_endpoints_survive_mongo_outage():
    settings = Settings(database_url="sqlite://", api_keys="k", mongo_timeout_ms=100)
    dead_mongo = MongoClient("mongodb://localhost:1", serverSelectionTimeoutMS=100)
    with TestClient(create_app(settings, mongo_client=dead_mongo), headers={"X-API-Key": "k"}) as c:
        health = c.get("/health").json()
        assert health["status"] == "degraded" and health["checks"]["sql"] == "ok"
        assert c.get("/instruments").status_code == 200
        r = c.get("/events")
        assert r.status_code == 503 and "unavailable" in r.json()["detail"]
