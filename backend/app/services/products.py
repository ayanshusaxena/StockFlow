from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import InventoryBalance, Product
from app.repositories import inventory as inventory_repository
from app.repositories import products as product_repository
from app.repositories import stores as store_repository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.errors import ConflictError, NotFoundError


def list_products(
    session: Session,
    *,
    skip: int,
    limit: int,
    search: str | None,
    category: str | None,
    include_inactive: bool,
) -> tuple[list[Product], int]:
    return product_repository.list_products(
        session,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        include_inactive=include_inactive,
    )


def get_product(session: Session, product_id: int) -> Product:
    product = product_repository.get_product(session, product_id)
    if product is None:
        raise NotFoundError("Product not found.")
    return product


def get_product_by_sku(session: Session, sku: str) -> Product:
    product = product_repository.get_by_sku(session, sku.strip().upper())
    if product is None or not product.is_active:
        raise NotFoundError("Active product not found for SKU.")
    return product


def create_product(session: Session, data: ProductCreate) -> Product:
    try:
        with session.begin():
            inventory_repository.lock_balance_provisioning(session)
            if product_repository.get_by_sku(session, data.sku) is not None:
                raise ConflictError(f"SKU '{data.sku}' already exists.")
            product = product_repository.insert_product(
                session,
                Product(sku=data.sku, name=data.name, category=data.category, price=data.price),
            )
            for store in store_repository.active_stores(session):
                inventory_repository.insert_balance(
                    session,
                    InventoryBalance(
                        product_id=product.id,
                        store_id=store.id,
                        quantity=0,
                        reorder_level=data.default_reorder_level,
                    ),
                )
        session.refresh(product)
        return product
    except IntegrityError as exc:
        raise ConflictError(f"SKU '{data.sku}' already exists or conflicts with a unique value.") from exc


def update_product(session: Session, product_id: int, data: ProductUpdate) -> Product:
    changes = data.model_dump(exclude_unset=True)
    for key in ("sku", "name", "category"):
        if changes.get(key) is not None:
            changes[key] = changes[key].strip()
            if not changes[key]:
                raise ConflictError(f"{key} must not be blank.")
    if changes.get("sku") is not None:
        changes["sku"] = changes["sku"].upper()
    try:
        with session.begin():
            if changes.get("is_active") is True:
                inventory_repository.lock_balance_provisioning(session)
            product = product_repository.get_for_update(session, product_id)
            if product is None:
                raise NotFoundError("Product not found.")
            for key, value in changes.items():
                if value is not None:
                    setattr(product, key, value)
            if changes.get("is_active") is True:
                existing = set(session.scalars(select(InventoryBalance.store_id).where(InventoryBalance.product_id == product_id)))
                for store in store_repository.active_stores(session):
                    if store.id not in existing:
                        inventory_repository.insert_balance(session, InventoryBalance(product_id=product_id, store_id=store.id, quantity=0, reorder_level=0))
        session.refresh(product)
        return product
    except IntegrityError as exc:
        raise ConflictError("The SKU or product name conflicts with an existing record.") from exc


def deactivate_product(session: Session, product_id: int) -> Product:
    with session.begin():
        product = product_repository.get_for_update(session, product_id)
        if product is None:
            raise NotFoundError("Product not found.")
        product.is_active = False
    session.refresh(product)
    return product
