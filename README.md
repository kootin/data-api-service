# data-api-service

A production-shaped FastAPI service for market data. Relational time series live in SQL (Postgres or SQLite). Semi-structured corporate events live in MongoDB. It ships with a Docker image and a three-job CI pipeline.

## Posting skills this demonstrates

From JPMorgan Chase's **Lead Data Engineer** posting:

| Posting asks for | Where it shows up here |
| --- | --- |
| Strong Python, including web frameworks such as FastAPI and REST API development | `app/`: typed routers, Pydantic v2 contracts, dependency injection, API-key auth, keyset pagination |
| Strong experience with both relational and NoSQL databases | Prices and instruments in SQLAlchemy 2.0 (Postgres `ON CONFLICT` upserts). Dividends, splits, ratings and news go to MongoDB as free-form documents with compound indexes |
| Object-oriented programming and design patterns | The repository pattern (`repositories/base.py` interfaces with SQL and Mongo implementations), an app factory, a retry decorator, and a settings object |
| Application resiliency and security | Startup and SQL endpoints survive a MongoDB outage (503 on events, `degraded` health), retry with backoff on transient Mongo errors, a non-root container, a healthcheck, and request-id logging |
| CI/CD, Docker image builds, Git | GitHub Actions runs **lint + unit tests**, an **integration** job against real Postgres 16 and Mongo 7 service containers, and a **Docker build**. The Dockerfile is a multi-stage build |
| Data modeling | Composite keys, date indexes, and validation that rejects impossible OHLC bars before they reach the database |

## API

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Checks SQL and Mongo; returns `ok` or `degraded` (no auth) |
| PUT | `/instruments/{symbol}` | Creates or updates an instrument |
| GET | `/instruments?asset_class=&limit=&cursor=` | Keyset-paginated list |
| POST | `/prices:bulk` | Idempotent bulk upsert of daily bars (unknown symbols and bad bars are rejected with 422) |
| GET | `/prices/{symbol}?start=&end=&limit=&cursor=` | Time-series range |
| GET | `/prices/{symbol}/returns` | Total return, annualized volatility and max drawdown |
| POST/GET | `/events`, `/events/{id}` | Corporate events stored in MongoDB |

Interactive docs are at `http://localhost:8000/docs`.

## Run it

```bash
# Everything in containers (Postgres + Mongo + API)
make up && make seed
curl -H "X-API-Key: dev-key" localhost:8000/prices/JPM/returns

# Or locally with SQLite (Mongo optional; events return 503 without it)
pip install -e ".[dev]"
make dev
make lint test
```

Smoke test against a real Postgres 16, with MongoDB deliberately down:

```
GET /health          {"status":"degraded","checks":{"sql":"ok","mongo":"error: ServerSelectionTimeoutError"}}
POST /prices:bulk    {'received': 252, 'upserted': 252}   × 3 symbols
GET /prices/JPM/returns  {'observations': 252, 'total_return_pct': 83.12, 'annualised_volatility_pct': 29.22, 'max_drawdown_pct': -10.62}
GET /events          503
```

## Why two databases

Daily bars are uniform, relational and queried by key and range, which is what SQL is good at. Corporate events are heterogeneous: a dividend has an amount and an ex-date, a rating change has an agency and from/to grades, and news has a headline and a source. Forcing them into one table means a sparse schema or a migration for every new event type. A document store with a `(symbol, occurred_at)` index serves the access pattern directly.
