from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.repositories.mongo import MongoEventRepository
from app.repositories.sql import SqlInstrumentRepository, SqlPriceRepository


def require_api_key(x_api_key: str | None = Header(default=None), settings: Settings = Depends(get_settings)) -> str:
    if x_api_key not in settings.api_key_set:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing or invalid X-API-Key")
    return x_api_key


def get_session(request: Request) -> Iterator[Session]:
    yield from request.app.state.db.session()


def instruments(session: Session = Depends(get_session)) -> SqlInstrumentRepository:
    return SqlInstrumentRepository(session)


def prices(session: Session = Depends(get_session)) -> SqlPriceRepository:
    return SqlPriceRepository(session)


def events(request: Request) -> MongoEventRepository:
    return request.app.state.events
