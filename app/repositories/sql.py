from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app import models, schemas
from app.repositories.base import InstrumentRepository, PriceRepository


class UnknownSymbolError(ValueError):
    pass


class SqlInstrumentRepository(InstrumentRepository):
    def __init__(self, session: Session):
        self.s = session

    def get(self, symbol):
        row = self.s.get(models.Instrument, symbol)
        return schemas.InstrumentOut.model_validate(row) if row else None

    def list(self, asset_class, limit, after):
        q = select(models.Instrument).order_by(models.Instrument.symbol).limit(limit)
        if asset_class:
            q = q.where(models.Instrument.asset_class == asset_class)
        if after:  # keyset pagination: stable and index-friendly, unlike OFFSET
            q = q.where(models.Instrument.symbol > after)
        return [schemas.InstrumentOut.model_validate(r) for r in self.s.scalars(q)]

    def upsert(self, item):
        row = self.s.merge(models.Instrument(**item.model_dump()))
        self.s.commit()
        return schemas.InstrumentOut.model_validate(row)


class SqlPriceRepository(PriceRepository):
    def __init__(self, session: Session):
        self.s = session

    def upsert_many(self, prices):
        if not prices:
            return 0
        symbols = {p.symbol for p in prices}
        known = set(self.s.scalars(select(models.Instrument.symbol).where(models.Instrument.symbol.in_(symbols))))
        if missing := symbols - known:
            raise UnknownSymbolError(f"unknown symbols: {sorted(missing)}")
        dialect = self.s.bind.dialect.name
        insert = pg_insert if dialect == "postgresql" else sqlite_insert
        rows = [p.model_dump() for p in prices]
        stmt = insert(models.DailyPrice).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "price_date"],
            set_={c: stmt.excluded[c] for c in ("open", "high", "low", "close", "volume")},
        )
        self.s.execute(stmt)
        self.s.commit()
        return len(rows)

    def range(self, symbol, start, end, limit, after):
        P = models.DailyPrice
        q = select(P).where(P.symbol == symbol).order_by(P.price_date).limit(limit)
        if start:
            q = q.where(P.price_date >= start)
        if end:
            q = q.where(P.price_date <= end)
        if after:
            q = q.where(P.price_date > after)
        return [schemas.PriceOut.model_validate(r) for r in self.s.scalars(q)]
