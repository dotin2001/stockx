from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.watchlist import WatchlistAdd, WatchlistItemRead
from app.services import watchlist as watchlist_service

router = APIRouter()


@router.get("", response_model=list[WatchlistItemRead])
def list_watchlist(current_user: CurrentUser, db: DbSession) -> list[WatchlistItemRead]:
    return [WatchlistItemRead.model_validate(item) for item in watchlist_service.list_watchlist(db, user=current_user)]


@router.post("", response_model=WatchlistItemRead, status_code=status.HTTP_201_CREATED)
def add_watchlist_item(payload: WatchlistAdd, current_user: CurrentUser, db: DbSession) -> WatchlistItemRead:
    item = watchlist_service.add_watchlist_item(db, user=current_user, product_id=payload.product_id)
    db.commit()
    db.refresh(item)
    return WatchlistItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist_item(item_id: UUID, current_user: CurrentUser, db: DbSession) -> None:
    watchlist_service.remove_watchlist_item(db, user=current_user, item_id=item_id)
    db.commit()
    return None
