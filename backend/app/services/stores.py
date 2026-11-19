from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import InventoryBalance, Store
from app.repositories import inventory as inventory_repository
from app.repositories import products as product_repository
from app.repositories import stores as store_repository
from app.schemas.store import StoreCreate, StoreUpdate
from app.services.errors import ConflictError, NotFoundError


def list_stores(
    session: Session, *, skip: int, limit: int, include_inactive: bool
) -> tuple[list[Store], int]:
    return store_repository.list_stores(
        session, skip=skip, limit=limit, include_inactive=include_inactive
    )


def get_store(session: Session, store_id: int) -> Store:
    store = store_repository.get_store(session, store_id)
    if store is None:
        raise NotFoundError("Store not found.")
    return store


def create_store(session: Session, data: StoreCreate) -> Store:
    try:
        with session.begin():
            inventory_repository.lock_balance_provisioning(session)
            store = store_repository.insert_store(
                session,
                Store(code=data.code, name=data.name, location=data.location),
            )
            for product in product_repository.active_products(session):
                reorder_level = inventory_repository.default_reorder_level(session, product.id)
                inventory_repository.insert_balance(
                    session,
                    InventoryBalance(
                        product_id=product.id,
                        store_id=store.id,
                        quantity=0,
                        reorder_level=reorder_level,
                    ),
                )
        session.refresh(store)
        return store
    except IntegrityError as exc:
        raise ConflictError("Store code or name already exists.") from exc


def update_store(session: Session, store_id: int, data: StoreUpdate) -> Store:
    changes = data.model_dump(exclude_unset=True)
    for key in ("code", "name", "location"):
        if changes.get(key) is not None:
            changes[key] = changes[key].strip()
            if not changes[key]:
                raise ConflictError(f"{key} must not be blank.")
    if changes.get("code") is not None:
        changes["code"] = changes["code"].upper()
    try:
        with session.begin():
            if changes.get("is_active") is True:
                inventory_repository.lock_balance_provisioning(session)
            store = store_repository.get_for_update(session, store_id)
            if store is None:
                raise NotFoundError("Store not found.")
            for key, value in changes.items():
                if value is not None:
                    setattr(store, key, value)
            if changes.get("is_active") is True:
                existing = set(session.scalars(select(InventoryBalance.product_id).where(InventoryBalance.store_id == store_id)))
                for product in product_repository.active_products(session):
                    if product.id not in existing:
                        reorder_level = inventory_repository.default_reorder_level(session, product.id)
                        inventory_repository.insert_balance(session, InventoryBalance(product_id=product.id, store_id=store_id, quantity=0, reorder_level=reorder_level))
        session.refresh(store)
        return store
    except IntegrityError as exc:
        raise ConflictError("Store code or name already exists.") from exc


def deactivate_store(session: Session, store_id: int) -> Store:
    with session.begin():
        store = store_repository.get_for_update(session, store_id)
        if store is None:
            raise NotFoundError("Store not found.")
        store.is_active = False
    session.refresh(store)
    return store
