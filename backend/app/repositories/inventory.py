from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, joinedload

from app.models import InventoryBalance, Product, Store
from app.schemas.inventory import StockStatus


def lock_balance_provisioning(session: Session) -> None:
    # One transaction-scoped lock coordinates product/store creation and reactivation.
    session.execute(text("SELECT pg_advisory_xact_lock(731042, 1)"))


def _status_filter(status: StockStatus):
    if status == StockStatus.OUT_OF_STOCK:
        return InventoryBalance.quantity == 0
    if status == StockStatus.BELOW_REORDER:
        return (InventoryBalance.quantity > 0) & (
            InventoryBalance.quantity <= InventoryBalance.reorder_level
        )
    return InventoryBalance.quantity > InventoryBalance.reorder_level


def list_balances(
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
) -> tuple[list[InventoryBalance], int]:
    statement = select(InventoryBalance).join(InventoryBalance.product).join(InventoryBalance.store)
    count_statement = (
        select(func.count())
        .select_from(InventoryBalance)
        .join(InventoryBalance.product)
        .join(InventoryBalance.store)
    )
    filters = []
    if not include_inactive:
        filters.extend([Product.is_active.is_(True), Store.is_active.is_(True)])
    if store_id is not None:
        filters.append(InventoryBalance.store_id == store_id)
    if product_id is not None:
        filters.append(InventoryBalance.product_id == product_id)
    if sku:
        filters.append(Product.sku == sku.strip().upper())
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Product.sku.ilike(term), Product.name.ilike(term)))
    if status:
        filters.append(_status_filter(status))
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    total = session.scalar(count_statement) or 0
    rows = session.scalars(
        statement.options(joinedload(InventoryBalance.product), joinedload(InventoryBalance.store))
        .order_by(Product.sku, Store.code)
        .offset(skip)
        .limit(limit)
    ).all()
    return rows, total


def replenishment_candidates(session: Session, *, store_id: int | None = None):
    statement = (
        select(InventoryBalance)
        .join(InventoryBalance.product)
        .join(InventoryBalance.store)
        .where(
            Product.is_active.is_(True),
            Store.is_active.is_(True),
            InventoryBalance.quantity <= InventoryBalance.reorder_level,
        )
        .options(joinedload(InventoryBalance.product), joinedload(InventoryBalance.store))
    )
    if store_id is not None:
        statement = statement.where(InventoryBalance.store_id == store_id)
    return session.scalars(statement).all()


def get_balance(
    session: Session, product_id: int, store_id: int, *, lock: bool = False
) -> InventoryBalance | None:
    statement = select(InventoryBalance).where(
        InventoryBalance.product_id == product_id,
        InventoryBalance.store_id == store_id,
    )
    if lock:
        statement = statement.with_for_update()
    else:
        statement = statement.options(
            joinedload(InventoryBalance.product), joinedload(InventoryBalance.store)
        )
    return session.scalar(statement)


def default_reorder_level(session: Session, product_id: int) -> int:
    return session.scalar(
        select(InventoryBalance.reorder_level)
        .where(InventoryBalance.product_id == product_id)
        .order_by(InventoryBalance.id)
        .limit(1)
    ) or 0


def insert_balance(session: Session, balance: InventoryBalance) -> InventoryBalance:
    session.add(balance)
    return balance


def set_quantity(balance: InventoryBalance, quantity: int, updated_at) -> None:
    balance.quantity = quantity
    balance.updated_at = updated_at
