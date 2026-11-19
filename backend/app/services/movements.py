import hashlib
import json

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import ActivityHistory, IdempotencyRecord, StockMovement
from app.models.product import utc_now
from app.repositories import history as history_repository
from app.repositories import inventory as inventory_repository
from app.repositories import products as product_repository
from app.repositories import stores as store_repository
from app.schemas.inventory import MovementType
from app.services.errors import (
    ConflictError,
    DatabaseOperationError,
    InsufficientStockError,
    NotFoundError,
)

MAX_STORED_QUANTITY = 2_147_483_647


def record_movement(
    session: Session,
    *,
    product_id: int,
    store_id: int,
    movement_type: MovementType,
    amount: int,
    note: str = "",
    idempotency_key: str | None = None,
) -> StockMovement:
    if movement_type in (MovementType.SALE, MovementType.RESTOCK) and amount <= 0:
        raise ConflictError("Sale and restock quantity must be a positive integer.")
    if movement_type == MovementType.ADJUSTMENT and amount == 0:
        raise ConflictError("Adjustment quantity_delta must not be zero.")
    if abs(amount) > MAX_STORED_QUANTITY:
        raise ConflictError("Movement quantity exceeds the supported range.")

    try:
        with session.begin():
            idempotency_record = None
            if idempotency_key is not None:
                if not idempotency_key.strip() or len(idempotency_key) > 128:
                    raise ConflictError("Idempotency-Key must contain 1 to 128 characters.")
                idempotency_key = idempotency_key.strip()
                fingerprint = hashlib.sha256(
                    json.dumps(
                        [product_id, store_id, movement_type.value, amount, note.strip()],
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                inserted_key = session.scalar(
                    postgresql_insert(IdempotencyRecord)
                    .values(key=idempotency_key, request_hash=fingerprint)
                    .on_conflict_do_nothing(index_elements=[IdempotencyRecord.key])
                    .returning(IdempotencyRecord.key)
                )
                if inserted_key is None:
                    existing = session.get(IdempotencyRecord, idempotency_key)
                    if existing is None:
                        raise DatabaseOperationError()
                    if existing.request_hash != fingerprint:
                        raise ConflictError("Idempotency-Key was already used for a different request.")
                    if existing.movement_id is None:
                        raise DatabaseOperationError()
                    prior_movement = session.get(StockMovement, existing.movement_id)
                    if prior_movement is None:
                        raise DatabaseOperationError()
                    return prior_movement
                idempotency_record = session.get(IdempotencyRecord, idempotency_key)

            product = product_repository.get_product(session, product_id)
            if product is None or not product.is_active:
                raise NotFoundError("Active product not found.")
            store = store_repository.get_store(session, store_id)
            if store is None or not store.is_active:
                raise NotFoundError("Active store not found.")
            balance = inventory_repository.get_balance(session, product_id, store_id, lock=True)
            if balance is None:
                raise NotFoundError("Inventory balance not found for this product and store.")

            delta = -amount if movement_type == MovementType.SALE else amount
            previous = balance.quantity
            result = previous + delta
            if result < 0:
                raise InsufficientStockError(
                    f"Insufficient stock: {previous} available, {abs(delta)} requested."
                )
            if result > MAX_STORED_QUANTITY:
                raise ConflictError("Resulting stock exceeds the supported range.")

            now = utc_now()
            inventory_repository.set_quantity(balance, result, now)
            movement = history_repository.insert_movement(
                session,
                StockMovement(
                    product_id=product_id,
                    store_id=store_id,
                    movement_type=movement_type.value,
                    quantity_delta=delta,
                    quantity_before=previous,
                    quantity_after=result,
                    note=note.strip(),
                    created_at=now,
                ),
            )
            if idempotency_record is not None:
                idempotency_record.movement_id = movement.id
            history_repository.insert_activity(
                session,
                ActivityHistory(
                    movement_id=movement.id,
                    product_id=product.id,
                    store_id=store.id,
                    event_type=movement_type.value,
                    product_name=product.name,
                    sku=product.sku,
                    store_name=store.name,
                    quantity_delta=delta,
                    note=note.strip(),
                    occurred_at=now,
                ),
            )
        return movement
    except (NotFoundError, ConflictError):
        raise
    except (IntegrityError, SQLAlchemyError) as exc:
        raise DatabaseOperationError() from exc


def list_movements(
    session: Session,
    *,
    skip: int,
    limit: int,
    product_id: int | None,
    store_id: int | None,
) -> tuple[list[StockMovement], int]:
    return history_repository.list_movements(
        session, skip=skip, limit=limit, product_id=product_id, store_id=store_id
    )


def list_activities(
    session: Session,
    *,
    skip: int,
    limit: int,
    product_id: int | None,
    store_id: int | None,
) -> tuple[list[ActivityHistory], int]:
    return history_repository.list_activities(
        session, skip=skip, limit=limit, product_id=product_id, store_id=store_id
    )
