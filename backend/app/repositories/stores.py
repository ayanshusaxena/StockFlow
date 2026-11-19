from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Store


def list_stores(
    session: Session, *, skip: int, limit: int, include_inactive: bool
) -> tuple[list[Store], int]:
    statement = select(Store)
    count_statement = select(func.count()).select_from(Store)
    if not include_inactive:
        statement = statement.where(Store.is_active.is_(True))
        count_statement = count_statement.where(Store.is_active.is_(True))
    total = session.scalar(count_statement) or 0
    rows = session.scalars(statement.order_by(Store.code).offset(skip).limit(limit)).all()
    return rows, total


def get_store(session: Session, store_id: int) -> Store | None:
    return session.get(Store, store_id)


def get_for_update(session: Session, store_id: int) -> Store | None:
    return session.scalar(select(Store).where(Store.id == store_id).with_for_update())


def active_stores(session: Session) -> list[Store]:
    return session.scalars(select(Store).where(Store.is_active.is_(True))).all()


def insert_store(session: Session, store: Store) -> Store:
    session.add(store)
    session.flush()
    return store
