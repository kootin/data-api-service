"""Repository interfaces. Handlers depend on these, not on a database driver."""

from abc import ABC, abstractmethod
from datetime import date

from app import schemas


class InstrumentRepository(ABC):
    @abstractmethod
    def get(self, symbol: str) -> schemas.InstrumentOut | None: ...

    @abstractmethod
    def list(self, asset_class: str | None, limit: int, after: str | None) -> list[schemas.InstrumentOut]: ...

    @abstractmethod
    def upsert(self, item: schemas.InstrumentIn) -> schemas.InstrumentOut: ...


class PriceRepository(ABC):
    @abstractmethod
    def upsert_many(self, prices: list[schemas.PriceIn]) -> int: ...

    @abstractmethod
    def range(
        self, symbol: str, start: date | None, end: date | None, limit: int, after: date | None
    ) -> list[schemas.PriceOut]: ...


class EventRepository(ABC):
    @abstractmethod
    def add(self, event: schemas.EventIn) -> schemas.EventOut: ...

    @abstractmethod
    def find(self, symbol: str | None, event_type: str | None, limit: int) -> list[schemas.EventOut]: ...
