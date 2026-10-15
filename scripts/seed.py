"""Seed the running API with instruments, ~1 year of synthetic daily bars and a few events."""

import argparse
import math
import random
from datetime import date, datetime, timedelta

import httpx

INSTRUMENTS = [
    {"symbol": "JPM", "name": "JPMorgan Chase & Co", "asset_class": "Equity", "currency": "USD"},
    {"symbol": "AAPL", "name": "Apple Inc", "asset_class": "Equity", "currency": "USD"},
    {"symbol": "TLT", "name": "iShares 20+ Year Treasury Bond ETF", "asset_class": "Fund", "currency": "USD"},
]


def bars(symbol: str, start: date, days: int, s0: float, rng: random.Random):
    price, d = s0, start
    out = []
    while len(out) < days:
        d += timedelta(days=1)
        if d.weekday() >= 5:
            continue
        o = price
        c = o * math.exp(rng.gauss(0.0003, 0.015))
        h, lo = max(o, c) * (1 + abs(rng.gauss(0, 0.004))), min(o, c) * (1 - abs(rng.gauss(0, 0.004)))
        out.append(
            {
                "symbol": symbol,
                "price_date": d.isoformat(),
                "open": round(o, 4),
                "high": round(h, 4),
                "low": round(lo, 4),
                "close": round(c, 4),
                "volume": rng.randint(1_000_000, 20_000_000),
            }
        )
        price = c
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--api-key", default="dev-key")
    a = p.parse_args()
    rng = random.Random(3)
    with httpx.Client(base_url=a.url, headers={"X-API-Key": a.api_key}, timeout=30) as c:
        for inst in INSTRUMENTS:
            c.put(f"/instruments/{inst['symbol']}", json=inst).raise_for_status()
            r = c.post("/prices:bulk", json=bars(inst["symbol"], date(2025, 10, 1), 252, rng.uniform(80, 250), rng))
            print(inst["symbol"], r.raise_for_status().json())
        c.post(
            "/events",
            json={
                "symbol": "JPM",
                "event_type": "dividend",
                "occurred_at": datetime(2026, 10, 6).isoformat(),
                "payload": {"amount": 1.40, "currency": "USD", "ex_date": "2026-10-06"},
            },
        ).raise_for_status()
        c.post(
            "/events",
            json={
                "symbol": "AAPL",
                "event_type": "rating_change",
                "occurred_at": datetime(2026, 10, 9).isoformat(),
                "payload": {"agency": "Example Research", "from": "Hold", "to": "Buy"},
            },
        ).raise_for_status()
        print(c.get("/prices/JPM/returns").json())


if __name__ == "__main__":
    main()
