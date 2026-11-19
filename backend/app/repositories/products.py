from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Product


def list_products(
    session: Session,
    *,
    skip: int,
    limit: int,
    search: str | None,
    category: str | None,
    include_inactive: bool,
) -> tuple[list[Product], int]:
    statement = select(Product)
    count_statement = select(func.count()).select_from(Product)
    filters = []
    if not include_inactive:
        filters.append(Product.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Product.sku.ilike(term), Product.name.ilike(term)))
    if category:
        filters.append(Product.category.ilike(category.strip()))
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    total = session.scalar(count_statement) or 0
    rows = session.scalars(statement.order_by(Product.sku).offset(skip).limit(limit)).all()
    return rows, total


def get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)


def get_by_sku(session: Session, sku: str) -> Product | None:
    return session.scalar(select(Product).where(Product.sku == sku))


def get_for_update(session: Session, product_id: int) -> Product | None:
    return session.scalar(select(Product).where(Product.id == product_id).with_for_update())


def insert_product(session: Session, product: Product) -> Product:
    session.add(product)
    session.flush()
    return product


def active_products(session: Session) -> list[Product]:
    return session.scalars(select(Product).where(Product.is_active.is_(True))).all()
