"""API contracts (Pydantic v2). Validation lives here, not in the handlers."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InstrumentIn(BaseModel):
    symbol: str = Field(pattern=r"^[A-Z0-9.]{1,16}$")
    name: str = Field(min_length=1, max_length=128)
    asset_class: Literal["Equity", "Bond", "FX", "Commodity", "Fund"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class InstrumentOut(InstrumentIn):
    model_config = ConfigDict(from_attributes=True)


class PriceIn(BaseModel):
    symbol: str
    price_date: date
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: int = Field(ge=0)

    @model_validator(mode="after")
    def check_bar(self):
        if not (self.low <= min(self.open, self.close) and self.high >= max(self.open, self.close)):
            raise ValueError("low must be <= open/close <= high")
        return self


class PriceOut(PriceIn):
    model_config = ConfigDict(from_attributes=True)


class BulkResult(BaseModel):
    received: int
    upserted: int


class Page(BaseModel):
    items: list[Any]
    next_cursor: str | None = None


class ReturnsOut(BaseModel):
    symbol: str
    start: date
    end: date
    observations: int
    total_return_pct: float
    annualised_volatility_pct: float
    max_drawdown_pct: float


class EventIn(BaseModel):
    """Semi-structured documents (corporate actions, news, ratings) go to MongoDB."""

    symbol: str
    event_type: Literal["dividend", "split", "rating_change", "news"]
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class EventOut(EventIn):
    id: str
