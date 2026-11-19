from sqlalchemy.orm import Session

from app.models import InventoryBalance
from app.repositories import inventory as inventory_repository
from app.schemas.inventory import StockStatus
from app.services.errors import NotFoundError


def inventory_status(balance: InventoryBalance) -> StockStatus:
    if balance.quantity == 0:
        return StockStatus.OUT_OF_STOCK
    if balance.quantity <= balance.reorder_level:
        return StockStatus.BELOW_REORDER
    return StockStatus.HEALTHY


def list_inventory(
    session: Session,
    *,
    skip: int,
    limit: int,
    store_id: int | None,
    product_id: int | None,
    sku: str | None,
    search: str | None,
    status: StockStatus | None,
    include_inactive: bool,
):
    return inventory_repository.list_balances(
        session,
        skip=skip,
        limit=limit,
        store_id=store_id,
        product_id=product_id,
        sku=sku,
        search=search,
        status=status,
        include_inactive=include_inactive,
    )


def get_inventory_balance(session: Session, product_id: int, store_id: int) -> InventoryBalance:
    balance = inventory_repository.get_balance(session, product_id, store_id)
    if balance is None:
        raise NotFoundError("Inventory balance not found.")
    return balance
