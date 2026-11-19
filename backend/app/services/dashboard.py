from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import InventoryBalance, Product, Store
from app.repositories import history as history_repository


def summary(session: Session) -> dict[str, object]:
    balances = session.scalars(
        select(InventoryBalance)
        .join(InventoryBalance.product)
        .join(InventoryBalance.store)
        .where(Product.is_active.is_(True), Store.is_active.is_(True))
    ).all()
    total_units = sum(balance.quantity for balance in balances)
    low = sum(0 < balance.quantity <= balance.reorder_level for balance in balances)
    out = sum(balance.quantity == 0 for balance in balances)
    products = session.scalar(select(func.count()).select_from(Product).where(Product.is_active.is_(True))) or 0
    stores = session.scalar(select(func.count()).select_from(Store).where(Store.is_active.is_(True))) or 0
    categories = session.scalars(
        select(Product.category).where(Product.is_active.is_(True)).distinct()
    ).all()
    recent, _ = history_repository.list_activities(
        session, skip=0, limit=5, product_id=None, store_id=None
    )
    return {
        "total_units": total_units,
        "product_count": products,
        "store_count": stores,
        "category_count": len(categories),
        "healthy_balances": len(balances) - low - out,
        "low_balances": low,
        "out_of_stock_balances": out,
        "total_balances": len(balances),
        "recent_activity": recent,
    }
