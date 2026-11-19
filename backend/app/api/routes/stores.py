from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.store import StoreCreate, StorePage, StoreRead, StoreUpdate
from app.services import stores as store_service


router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=StorePage)
def get_stores(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    include_inactive: bool = False,
    session: Session = Depends(get_db),
):
    rows, total = store_service.list_stores(
        session, skip=skip, limit=limit, include_inactive=include_inactive
    )
    return StorePage(items=rows, skip=skip, limit=limit, total=total)


@router.post("", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
def post_store(data: StoreCreate, session: Session = Depends(get_db)):
    return store_service.create_store(session, data)


@router.get("/{store_id}", response_model=StoreRead)
def get_store(store_id: int, session: Session = Depends(get_db)):
    return store_service.get_store(session, store_id)


@router.patch("/{store_id}", response_model=StoreRead)
def patch_store(store_id: int, data: StoreUpdate, session: Session = Depends(get_db)):
    return store_service.update_store(session, store_id, data)


@router.delete("/{store_id}", response_model=StoreRead)
def delete_store(store_id: int, response: Response, session: Session = Depends(get_db)):
    response.status_code = status.HTTP_200_OK
    return store_service.deactivate_store(session, store_id)
