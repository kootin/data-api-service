from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import analytics, schemas
from app.config import Settings, get_settings
from app.deps import instruments, prices
from app.repositories.sql import SqlInstrumentRepository, SqlPriceRepository, UnknownSymbolError

router = APIRouter(tags=["market data"])


@router.put("/instruments/{symbol}", response_model=schemas.InstrumentOut)
def put_instrument(symbol: str, body: schemas.InstrumentIn, repo: SqlInstrumentRepository = Depends(instruments)):
    if body.symbol != symbol:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "path symbol and body symbol differ")
    return repo.upsert(body)


@router.get("/instruments", response_model=schemas.Page)
def list_instruments(
    asset_class: str | None = None,
    limit: int = Query(100, ge=1),
    cursor: str | None = None,
    repo: SqlInstrumentRepository = Depends(instruments),
    settings: Settings = Depends(get_settings),
):
    limit = min(limit, settings.max_page_size)
    items = repo.list(asset_class, limit, cursor)
    return schemas.Page(items=items, next_cursor=items[-1].symbol if len(items) == limit else None)


@router.get("/instruments/{symbol}", response_model=schemas.InstrumentOut)
def get_instrument(symbol: str, repo: SqlInstrumentRepository = Depends(instruments)):
    if not (item := repo.get(symbol)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{symbol} not found")
    return item


@router.post("/prices:bulk", response_model=schemas.BulkResult, status_code=status.HTTP_200_OK)
def bulk_prices(body: list[schemas.PriceIn], repo: SqlPriceRepository = Depends(prices)):
    try:
        n = repo.upsert_many(body)
    except UnknownSymbolError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    return schemas.BulkResult(received=len(body), upserted=n)


@router.get("/prices/{symbol}", response_model=schemas.Page)
def get_prices(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(500, ge=1),
    cursor: date | None = None,
    repo: SqlPriceRepository = Depends(prices),
    settings: Settings = Depends(get_settings),
):
    limit = min(limit, settings.max_page_size)
    items = repo.range(symbol, start, end, limit, cursor)
    return schemas.Page(items=items, next_cursor=items[-1].price_date.isoformat() if len(items) == limit else None)


@router.get("/prices/{symbol}/returns", response_model=schemas.ReturnsOut)
def get_returns(
    symbol: str, start: date | None = None, end: date | None = None, repo: SqlPriceRepository = Depends(prices)
):
    rows = repo.range(symbol, start, end, limit=10_000, after=None)
    try:
        return analytics.returns_summary(symbol, rows)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"not enough prices for {symbol}") from e
