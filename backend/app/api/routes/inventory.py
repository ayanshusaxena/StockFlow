from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inventory import (
    ActivityPage,
    ActivityRead,
    AdjustmentCreate,
    InventoryPage,
    InventoryRead,
    InventoryImportPreview,
    InventoryImportResult,
    MovementPage,
    MovementRead,
    MovementType,
    ReplenishmentItem,
    ReplenishmentPage,
    RestockCreate,
    SaleCreate,
    StockStatus,
)
from app.services import inventory as inventory_service
from app.services import movements as movement_service
from app.services import replenishment as replenishment_service
from app.services import csv_import as csv_import_service


router = APIRouter(prefix="/inventory", tags=["inventory"])


def _inventory_read(balance) -> InventoryRead:
    return InventoryRead(
        id=balance.id,
        product=balance.product,
        store=balance.store,
        quantity=balance.quantity,
        reorder_level=balance.reorder_level,
        status=inventory_service.inventory_status(balance),
        updated_at=balance.updated_at,
    )


@router.get("", response_model=InventoryPage)
def get_inventory(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    store_id: int | None = Query(default=None, gt=0),
    product_id: int | None = Query(default=None, gt=0),
    sku: str | None = None,
    search: str | None = None,
    stock_status: StockStatus | None = Query(default=None, alias="status"),
    include_inactive: bool = False,
    session: Session = Depends(get_db),
):
    rows, total = inventory_service.list_inventory(
        session,
        skip=skip,
        limit=limit,
        store_id=store_id,
        product_id=product_id,
        sku=sku,
        search=search,
        status=stock_status,
        include_inactive=include_inactive,
    )
    return InventoryPage(
        items=[_inventory_read(row) for row in rows], skip=skip, limit=limit, total=total
    )


@router.post("/movements/sale", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def post_sale(
    data: SaleCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    session: Session = Depends(get_db),
):
    return movement_service.record_movement(
        session,
        product_id=data.product_id,
        store_id=data.store_id,
        movement_type=MovementType.SALE,
        amount=data.quantity,
        note=data.note,
        idempotency_key=idempotency_key,
    )


@router.post("/movements/restock", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def post_restock(
    data: RestockCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    session: Session = Depends(get_db),
):
    return movement_service.record_movement(
        session,
        product_id=data.product_id,
        store_id=data.store_id,
        movement_type=MovementType.RESTOCK,
        amount=data.quantity,
        note=data.note,
        idempotency_key=idempotency_key,
    )


@router.post("/movements/adjustment", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def post_adjustment(
    data: AdjustmentCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    session: Session = Depends(get_db),
):
    return movement_service.record_movement(
        session,
        product_id=data.product_id,
        store_id=data.store_id,
        movement_type=MovementType.ADJUSTMENT,
        amount=data.quantity_delta,
        note=data.note,
        idempotency_key=idempotency_key,
    )


@router.get("/movements", response_model=MovementPage)
def get_movements(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    product_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    session: Session = Depends(get_db),
):
    rows, total = movement_service.list_movements(
        session, skip=skip, limit=limit, product_id=product_id, store_id=store_id
    )
    return MovementPage(items=rows, skip=skip, limit=limit, total=total)


@router.get("/activities", response_model=ActivityPage)
def get_activities(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    product_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    session: Session = Depends(get_db),
):
    rows, total = movement_service.list_activities(
        session, skip=skip, limit=limit, product_id=product_id, store_id=store_id
    )
    return ActivityPage(items=rows, skip=skip, limit=limit, total=total)


@router.get("/replenishment", response_model=ReplenishmentPage)
def get_replenishment(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    store_id: int | None = Query(default=None, gt=0),
    urgency: str | None = Query(default=None, pattern="^(out|low)$"),
    session: Session = Depends(get_db),
):
    rows = replenishment_service.prioritised_replenishment(session, store_id=store_id)
    if urgency == "out":
        rows = [row for row in rows if row["quantity"] == 0]
    elif urgency == "low":
        rows = [row for row in rows if row["quantity"] > 0]
    return ReplenishmentPage(items=rows[skip : skip + limit], skip=skip, limit=limit, total=len(rows))


@router.post("/import/preview", response_model=InventoryImportPreview)
async def preview_import(
    request: Request,
    filename: str = Query(default="inventory.csv", max_length=200),
    session: Session = Depends(get_db),
):
    content = await request.body()
    return csv_import_service.preview_inventory_csv(session, content, filename)


@router.post("/import/commit", response_model=InventoryImportResult, status_code=status.HTTP_201_CREATED)
async def commit_import(
    request: Request,
    filename: str = Query(default="inventory.csv", max_length=200),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    session: Session = Depends(get_db),
):
    content = await request.body()
    return csv_import_service.commit_inventory_csv(
        session, content, filename, idempotency_key
    )


@router.get("/{product_id}/{store_id}", response_model=InventoryRead)
def get_inventory_balance(product_id: int, store_id: int, session: Session = Depends(get_db)):
    balance = inventory_service.get_inventory_balance(session, product_id, store_id)
    return _inventory_read(balance)
