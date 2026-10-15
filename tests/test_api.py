import pytest


def test_requires_api_key(client):
    assert client.get("/instruments", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/instruments", headers={"X-API-Key": "other-key"}).status_code == 200


def test_health_is_public(client):
    r = client.get("/health", headers={})
    assert r.json() == {"status": "ok", "checks": {"sql": "ok", "mongo": "ok"}}
    assert "x-request-id" in r.headers


def test_instrument_validation(client):
    bad = {"symbol": "jpm", "name": "x", "asset_class": "Equity", "currency": "USD"}
    assert client.put("/instruments/jpm", json=bad).status_code == 422
    mismatch = {"symbol": "JPM", "name": "x", "asset_class": "Equity", "currency": "USD"}
    assert client.put("/instruments/AAPL", json=mismatch).status_code == 422


def test_keyset_pagination(client):
    for s in ["A", "B", "C", "D", "E"]:
        client.put(f"/instruments/{s}", json={"symbol": s, "name": s, "asset_class": "Equity", "currency": "USD"})
    page1 = client.get("/instruments", params={"limit": 2}).json()
    page2 = client.get("/instruments", params={"limit": 2, "cursor": page1["next_cursor"]}).json()
    page3 = client.get("/instruments", params={"limit": 2, "cursor": page2["next_cursor"]}).json()
    assert [i["symbol"] for i in page1["items"] + page2["items"] + page3["items"]] == list("ABCDE")
    assert page3["next_cursor"] is None


def test_bulk_upsert_is_idempotent_and_updates(seeded):
    again = [
        {"symbol": "JPM", "price_date": "2026-10-05", "open": 120, "high": 125, "low": 119, "close": 124, "volume": 5}
    ]
    assert seeded.post("/prices:bulk", json=again).json() == {"received": 1, "upserted": 1}
    items = seeded.get("/prices/JPM").json()["items"]
    assert len(items) == 5 and float(items[-1]["close"]) == 124


def test_bulk_rejects_bad_bars_and_unknown_symbols(seeded):
    bad_bar = [{"symbol": "JPM", "price_date": "2026-10-09", "open": 10, "high": 9, "low": 8, "close": 10, "volume": 1}]
    assert seeded.post("/prices:bulk", json=bad_bar).status_code == 422
    unknown = [
        {"symbol": "ZZZ", "price_date": "2026-10-09", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1}
    ]
    r = seeded.post("/prices:bulk", json=unknown)
    assert r.status_code == 422 and "ZZZ" in r.json()["detail"]


def test_price_range_filter(seeded):
    items = seeded.get("/prices/JPM", params={"start": "2026-10-02", "end": "2026-10-04"}).json()["items"]
    assert [i["price_date"] for i in items] == ["2026-10-02", "2026-10-03", "2026-10-04"]


def test_returns_analytics(seeded):
    r = seeded.get("/prices/JPM/returns").json()
    assert r["observations"] == 5
    assert r["total_return_pct"] == pytest.approx(20.0)
    assert r["max_drawdown_pct"] == pytest.approx(-10.0)
    assert seeded.get("/prices/NOPE/returns").status_code == 404


def test_events_round_trip_in_mongo(client):
    e = {
        "symbol": "JPM",
        "event_type": "dividend",
        "occurred_at": "2026-10-06T00:00:00",
        "payload": {"amount": 1.4, "currency": "USD"},
    }
    created = client.post("/events", json=e)
    assert created.status_code == 201
    eid = created.json()["id"]
    client.post(
        "/events", json={**e, "event_type": "news", "occurred_at": "2026-10-07T00:00:00", "payload": {"headline": "x"}}
    )
    assert [x["event_type"] for x in client.get("/events", params={"symbol": "JPM"}).json()] == ["news", "dividend"]
    assert client.get(f"/events/{eid}").json()["payload"] == {"amount": 1.4, "currency": "USD"}
    assert client.get("/events/not-an-id").status_code == 404
