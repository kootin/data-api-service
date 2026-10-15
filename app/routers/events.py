from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import schemas
from app.deps import events
from app.repositories.mongo import MongoEventRepository

router = APIRouter(prefix="/events", tags=["events (MongoDB)"])


@router.post("", response_model=schemas.EventOut, status_code=status.HTTP_201_CREATED)
def add_event(body: schemas.EventIn, repo: MongoEventRepository = Depends(events)):
    return repo.add(body)


@router.get("", response_model=list[schemas.EventOut])
def find_events(
    symbol: str | None = None,
    event_type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    repo: MongoEventRepository = Depends(events),
):
    return repo.find(symbol, event_type, limit)


@router.get("/{event_id}", response_model=schemas.EventOut)
def get_event(event_id: str, repo: MongoEventRepository = Depends(events)):
    if not (e := repo.get(event_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "event not found")
    return e
