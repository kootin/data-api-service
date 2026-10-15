"""Market data API: relational time series in SQL, semi-structured events in MongoDB."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db import Database
from app.deps import require_api_key
from app.repositories.mongo import MongoEventRepository
from app.routers import events, market

log = logging.getLogger("data-api")
logging.basicConfig(level=logging.INFO, format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":%(message)s}')


def create_app(settings: Settings | None = None, mongo_client=None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = Database(settings.database_url)
        client = mongo_client or MongoClient(settings.mongo_url, serverSelectionTimeoutMS=settings.mongo_timeout_ms)
        app.state.mongo = client
        app.state.events = MongoEventRepository(client[settings.mongo_db]["events"])
        try:
            app.state.events.ensure_indexes()
        except PyMongoError as e:
            # Degrade instead of refusing to start: SQL endpoints keep serving, /health reports mongo down.
            log.warning('"mongo unavailable at startup, indexes not ensured: %s"', type(e).__name__)
        yield
        app.state.db.engine.dispose()
        client.close()

    app = FastAPI(title="Market Data API", version="0.1.0", lifespan=lifespan)
    app.dependency_overrides[get_settings] = lambda: settings

    @app.exception_handler(PyMongoError)
    async def mongo_unavailable(request: Request, exc: PyMongoError):
        return JSONResponse(status_code=503, content={"detail": "event store unavailable, retry later"})

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id", uuid.uuid4().hex)
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        log.info(
            '"%s %s -> %s in %.1fms rid=%s"',
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - t0) * 1000,
            rid,
        )
        return response

    @app.get("/health", tags=["ops"])
    def health(request: Request):
        checks = {}
        try:
            with request.app.state.db.engine.connect() as c:
                c.execute(text("SELECT 1"))
            checks["sql"] = "ok"
        except Exception as e:  # noqa: BLE001 - report, don't crash the probe
            checks["sql"] = f"error: {type(e).__name__}"
        try:
            request.app.state.mongo.admin.command("ping")
            checks["mongo"] = "ok"
        except Exception as e:  # noqa: BLE001
            checks["mongo"] = f"error: {type(e).__name__}"
        return {"status": "ok" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}

    secured = [Depends(require_api_key)]
    app.include_router(market.router, dependencies=secured)
    app.include_router(events.router, dependencies=secured)
    return app


app = create_app()
