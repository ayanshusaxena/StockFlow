from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ActivityHistory, StockMovement


def list_movements(
    session: Session,
    *,
    skip: int,
    limit: int,
    product_id: int | None,
    store_id: int | None,
) -> tuple[list[StockMovement], int]:
    statement = select(StockMovement)
    count_statement = select(func.count()).select_from(StockMovement)
    filters = []
    if product_id is not None:
        filters.append(StockMovement.product_id == product_id)
    if store_id is not None:
        filters.append(StockMovement.store_id == store_id)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    total = session.scalar(count_statement) or 0
    rows = session.scalars(
        statement.order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return rows, total


def list_activities(
    session: Session,
    *,
    skip: int,
    limit: int,
    product_id: int | None,
    store_id: int | None,
) -> tuple[list[ActivityHistory], int]:
    statement = select(ActivityHistory)
    count_statement = select(func.count()).select_from(ActivityHistory)
    filters = []
    if product_id is not None:
        filters.append(ActivityHistory.product_id == product_id)
    if store_id is not None:
        filters.append(ActivityHistory.store_id == store_id)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    total = session.scalar(count_statement) or 0
    rows = session.scalars(
        statement.order_by(ActivityHistory.occurred_at.desc(), ActivityHistory.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return rows, total


def insert_movement(session: Session, movement: StockMovement) -> StockMovement:
    session.add(movement)
    session.flush()
    return movement


def insert_activity(session: Session, activity: ActivityHistory) -> ActivityHistory:
    session.add(activity)
    session.flush()
    return activity
