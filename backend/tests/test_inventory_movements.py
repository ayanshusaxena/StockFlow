from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, current_thread
from time import monotonic, sleep

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models import ActivityHistory, InventoryBalance, StockMovement
from app.schemas.inventory import MovementType
from app.services import movements as movement_service
from app.services.errors import InsufficientStockError
from app.services.movements import record_movement
from tests.helpers import seeded_ids


def test_sale_commits_balance_movement_and_activity(client):
    product_id, central_id, _city_id = seeded_ids(client)
    response = client.post(
        "/api/v1/inventory/movements/sale",
        json={"product_id": product_id, "store_id": central_id, "quantity": 4, "note": "POS"},
    )
    assert response.status_code == 201
    movement = response.json()
    assert movement["movement_type"] == "sale"
    assert movement["quantity_delta"] == -4
    assert movement["quantity_before"] == 24
    assert movement["quantity_after"] == 20

    balance = client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()
    assert balance["quantity"] == 20
    movements = client.get(
        "/api/v1/inventory/movements", params={"product_id": product_id, "store_id": central_id}
    ).json()
    assert movements["total"] == 2  # one retained fixture movement and the new sale
    assert movements["items"][0]["id"] == movement["id"]
    activities = client.get(
        "/api/v1/inventory/activities", params={"product_id": product_id, "store_id": central_id}
    ).json()
    assert activities["items"][0]["movement_id"] == movement["id"]
    assert activities["items"][0]["quantity_delta"] == -4


def test_sale_exceeding_available_stock_is_rejected_without_changes(client):
    product_id, central_id, _city_id = seeded_ids(client)
    response = client.post(
        "/api/v1/inventory/movements/sale",
        json={"product_id": product_id, "store_id": central_id, "quantity": 25},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"
    assert client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()["quantity"] == 24


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2"])
def test_sale_quantity_requires_positive_integer(client, quantity):
    product_id, central_id, _city_id = seeded_ids(client)
    response = client.post(
        "/api/v1/inventory/movements/sale",
        json={"product_id": product_id, "store_id": central_id, "quantity": quantity},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("field", ["product_id", "store_id"])
def test_sale_requires_existing_product_and_store(client, field):
    product_id, central_id, _city_id = seeded_ids(client)
    body = {"product_id": product_id, "store_id": central_id, "quantity": 1}
    body[field] = 999999
    response = client.post("/api/v1/inventory/movements/sale", json=body)
    assert response.status_code == 404
    assert client.get("/api/v1/inventory/movements").json()["total"] == 5


def test_restock_increases_balance_and_records_history(client):
    product_id, _central_id, city_id = seeded_ids(client)
    before = client.get(f"/api/v1/inventory/{product_id}/{city_id}").json()["quantity"]
    response = client.post(
        "/api/v1/inventory/movements/restock",
        json={"product_id": product_id, "store_id": city_id, "quantity": 5},
    )
    assert response.status_code == 201
    assert response.json()["quantity_delta"] == 5
    assert response.json()["quantity_after"] == before + 5
    assert client.get(f"/api/v1/inventory/{product_id}/{city_id}").json()["quantity"] == before + 5


@pytest.mark.parametrize(("delta", "expected"), [(3, 27), (-2, 22)])
def test_positive_and_negative_adjustments(client, delta, expected):
    product_id, central_id, _city_id = seeded_ids(client)
    response = client.post(
        "/api/v1/inventory/movements/adjustment",
        json={"product_id": product_id, "store_id": central_id, "quantity_delta": delta},
    )
    assert response.status_code == 201
    assert response.json()["quantity_after"] == expected


def test_adjustment_cannot_make_stock_negative_or_be_zero(client):
    product_id, _central_id, _city_id = seeded_ids(client)
    stores = client.get("/api/v1/stores", params={"limit": 100}).json()["items"]
    riverside_id = next(store["id"] for store in stores if store["code"] == "ST-003")
    response = client.post(
        "/api/v1/inventory/movements/adjustment",
        json={"product_id": product_id, "store_id": riverside_id, "quantity_delta": -1},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"
    zero = client.post(
        "/api/v1/inventory/movements/adjustment",
        json={"product_id": product_id, "store_id": riverside_id, "quantity_delta": 0},
    )
    assert zero.status_code == 422


def test_database_failure_rolls_back_balance_movement_and_activity(client):
    product_id, central_id, _city_id = seeded_ids(client)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE OR REPLACE FUNCTION reject_stockflow_test_activity() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'forced test failure'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER reject_stockflow_test_activity BEFORE INSERT ON activity_history "
                "FOR EACH ROW EXECUTE FUNCTION reject_stockflow_test_activity()"
            )
        )
    try:
        response = client.post(
            "/api/v1/inventory/movements/sale",
            json={"product_id": product_id, "store_id": central_id, "quantity": 3},
        )
        assert response.status_code == 500
        assert client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()["quantity"] == 24
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(StockMovement)) == 5
            assert session.scalar(select(func.count()).select_from(ActivityHistory)) == 6
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER IF EXISTS reject_stockflow_test_activity ON activity_history"))
            connection.execute(text("DROP FUNCTION IF EXISTS reject_stockflow_test_activity()"))


def test_movement_response_does_not_depend_on_post_commit_refresh(client, monkeypatch):
    product_id, central_id, _city_id = seeded_ids(client)

    def reject_refresh(*_args, **_kwargs):
        raise AssertionError("record_movement must not refresh after commit")

    monkeypatch.setattr(Session, "refresh", reject_refresh)
    with SessionLocal() as session:
        movement = record_movement(
            session,
            product_id=product_id,
            store_id=central_id,
            movement_type=MovementType.SALE,
            amount=3,
            note="response data is known before commit",
        )

    assert movement.id is not None
    assert (movement.quantity_before, movement.quantity_delta, movement.quantity_after) == (24, -3, 21)
    assert movement.note == "response data is known before commit"
    assert client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()["quantity"] == 21
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(StockMovement)) == 6
        assert session.scalar(select(func.count()).select_from(ActivityHistory)) == 7


def test_movement_idempotency_replays_success_and_rejects_conflicting_reuse(client):
    product_id, central_id, _city_id = seeded_ids(client)
    key = "movement-replay-001"
    payload = {"product_id": product_id, "store_id": central_id, "quantity": 2, "note": "POS"}
    first = client.post(
        "/api/v1/inventory/movements/sale", json=payload, headers={"Idempotency-Key": key}
    )
    replay = client.post(
        "/api/v1/inventory/movements/sale", json=payload, headers={"Idempotency-Key": key}
    )
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()["quantity"] == 22

    conflict = client.post(
        "/api/v1/inventory/movements/sale",
        json={**payload, "quantity": 3},
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409
    assert "different request" in conflict.json()["error"]["message"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(StockMovement)) == 6
        assert session.scalar(select(func.count()).select_from(ActivityHistory)) == 7


def test_concurrent_requests_with_same_movement_idempotency_key_apply_once(client):
    product_id, central_id, _city_id = seeded_ids(client)
    gate = Barrier(2)

    def submit_same_operation():
        gate.wait(timeout=5)
        with SessionLocal() as session:
            return movement_service.record_movement(
                session,
                product_id=product_id,
                store_id=central_id,
                movement_type=MovementType.SALE,
                amount=15,
                idempotency_key="concurrent-retry-001",
            ).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _index: submit_same_operation(), range(2)))
    assert ids[0] == ids[1]
    assert client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()["quantity"] == 9
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(StockMovement)) == 6
        assert session.scalar(select(func.count()).select_from(ActivityHistory)) == 7


def test_postgres_row_lock_prevents_concurrent_oversell(client, monkeypatch):
    product_id, central_id, _city_id = seeded_ids(client)
    with SessionLocal() as session:
        initial_movements = session.scalar(
            select(func.count()).select_from(StockMovement).where(
                StockMovement.product_id == product_id,
                StockMovement.store_id == central_id,
            )
        )
        initial_activities = session.scalar(
            select(func.count()).select_from(ActivityHistory).where(
                ActivityHistory.product_id == product_id,
                ActivityHistory.store_id == central_id,
            )
        )
    original_get_balance = movement_service.inventory_repository.get_balance
    holder_locked = Event()
    release_holder = Event()
    challenger_at_balance = Event()
    worker_pids: dict[str, int] = {}

    def synchronized_get_balance(session, requested_product_id, requested_store_id, *, lock=False):
        if lock and current_thread().name.endswith("_0"):
            worker_pids[current_thread().name] = session.scalar(text("SELECT pg_backend_pid()"))
            result = original_get_balance(
                session, requested_product_id, requested_store_id, lock=lock
            )
            holder_locked.set()
            if not release_holder.wait(timeout=8):
                raise TimeoutError("test did not release the transaction holding the balance lock")
            return result
        if lock and current_thread().name.endswith("_1"):
            worker_pids[current_thread().name] = session.scalar(text("SELECT pg_backend_pid()"))
            challenger_at_balance.set()
        return original_get_balance(session, requested_product_id, requested_store_id, lock=lock)

    monkeypatch.setattr(
        movement_service.inventory_repository, "get_balance", synchronized_get_balance
    )

    def sell_fifteen():
        with SessionLocal() as session:
            session.execute(text("SET lock_timeout = '6s'"))
            session.commit()
            try:
                movement_service.record_movement(
                    session,
                    product_id=product_id,
                    store_id=central_id,
                    movement_type=MovementType.SALE,
                    amount=15,
                    note="concurrency test",
                )
                return "sold"
            except InsufficientStockError:
                return "rejected"

    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="stock-sale")
    holder = pool.submit(sell_fifteen)
    challenger = None
    saw_lock_wait = False
    try:
        assert holder_locked.wait(timeout=5), "first transaction never acquired its row lock"
        challenger = pool.submit(sell_fifteen)
        assert challenger_at_balance.wait(timeout=5), "second transaction never reached the balance row"
        assert worker_pids["stock-sale_0"] != worker_pids["stock-sale_1"]

        deadline = monotonic() + 5
        while monotonic() < deadline:
            challenger_pid = worker_pids.get("stock-sale_1")
            if challenger_pid is not None:
                with engine.connect() as connection:
                    wait_type = connection.scalar(
                        text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                        {"pid": challenger_pid},
                    )
                if wait_type == "Lock":
                    saw_lock_wait = True
                    break
            sleep(0.02)
        assert saw_lock_wait, "second PostgreSQL session was not observed waiting on the held row lock"
    finally:
        # Always release the lock holder, including assertion and timeout paths.
        release_holder.set()
        try:
            holder_result = holder.result(timeout=10)
            challenger_result = challenger.result(timeout=10) if challenger is not None else None
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

    assert sorted([holder_result, challenger_result]) == ["rejected", "sold"]
    balance = client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()
    assert balance["quantity"] == 9
    with SessionLocal() as session:
        assert session.scalar(
            select(func.count()).select_from(StockMovement).where(
                StockMovement.product_id == product_id,
                StockMovement.store_id == central_id,
            )
        ) == initial_movements + 1
        assert session.scalar(
            select(func.count()).select_from(ActivityHistory).where(
                ActivityHistory.product_id == product_id,
                ActivityHistory.store_id == central_id,
            )
        ) == initial_activities + 1


def test_health_and_openapi(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "connected"}
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/inventory/movements/sale" in schema.json()["paths"]
    missing_route = client.get("/not-a-route")
    assert missing_route.status_code == 404
    assert missing_route.json()["error"]["code"] == "not_found"
