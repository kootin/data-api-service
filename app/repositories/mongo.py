import time
from functools import wraps

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import AutoReconnect, NetworkTimeout

from app import schemas
from app.repositories.base import EventRepository


def retry(times: int = 3, backoff: float = 0.2):
    """Retry transient MongoDB failures with exponential backoff."""

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            for attempt in range(times):
                try:
                    return fn(*a, **kw)
                except (AutoReconnect, NetworkTimeout):
                    if attempt == times - 1:
                        raise
                    time.sleep(backoff * 2**attempt)

        return wrapper

    return deco


class MongoEventRepository(EventRepository):
    def __init__(self, collection: Collection):
        self.c = collection

    def ensure_indexes(self) -> None:
        self.c.create_index([("symbol", ASCENDING), ("occurred_at", DESCENDING)])
        self.c.create_index([("event_type", ASCENDING)])

    @staticmethod
    def _out(doc) -> schemas.EventOut:
        doc = dict(doc)
        return schemas.EventOut(id=str(doc.pop("_id")), **doc)

    @retry()
    def add(self, event):
        doc = event.model_dump()
        res = self.c.insert_one(doc)
        return self._out({**doc, "_id": res.inserted_id})

    @retry()
    def find(self, symbol, event_type, limit):
        q = {}
        if symbol:
            q["symbol"] = symbol
        if event_type:
            q["event_type"] = event_type
        cur = self.c.find(q).sort("occurred_at", DESCENDING).limit(limit)
        return [self._out(d) for d in cur]

    def get(self, event_id: str):
        doc = self.c.find_one({"_id": ObjectId(event_id)}) if ObjectId.is_valid(event_id) else None
        return self._out(doc) if doc else None
