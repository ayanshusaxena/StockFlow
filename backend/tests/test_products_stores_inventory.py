from decimal import Decimal

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import InventoryBalance, Product, Store
from app.db.seed_data import seed_database
from tests.helpers import seeded_ids


def test_product_crud_and_new_product_zero_balances(client):
    response = client.post(
        "/api/v1/products",
        json={
            "sku": "new-101",
            "name": "New Item",
            "category": "Test",
            "price": "12.50",
            "default_reorder_level": 4,
        },
    )
    assert response.status_code == 201
    product = response.json()
    assert product["sku"] == "NEW-101"
    assert Decimal(product["price"]) == Decimal("12.50")

    balances = client.get("/api/v1/inventory", params={"product_id": product["id"]})
    assert balances.status_code == 200
    assert balances.json()["total"] == 3
    assert {row["quantity"] for row in balances.json()["items"]} == {0}
    assert {row["reorder_level"] for row in balances.json()["items"]} == {4}

    update = client.patch(
        f"/api/v1/products/{product['id']}", json={"name": "Renamed Item", "price": "15.00"}
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Renamed Item"
    assert Decimal(update.json()["price"]) == Decimal("15.00")

    deleted = client.delete(f"/api/v1/products/{product['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["is_active"] is False
    assert client.get("/api/v1/products", params={"search": "NEW-101"}).json()["total"] == 0


def test_duplicate_sku_is_rejected_case_insensitively(client):
    response = client.post(
        "/api/v1/products",
        json={"sku": "el-001", "name": "Duplicate", "category": "Test", "price": "1.00"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_store_crud(client):
    created = client.post(
        "/api/v1/stores", json={"code": "st-new", "name": "New Branch", "location": "Gwalior"}
    )
    assert created.status_code == 201
    store = created.json()
    assert store["code"] == "ST-NEW"
    new_store_inventory = client.get("/api/v1/inventory", params={"store_id": store["id"]})
    assert new_store_inventory.status_code == 200
    assert new_store_inventory.json()["total"] == 10
    assert all(row["quantity"] == 0 for row in new_store_inventory.json()["items"])

    updated = client.patch(f"/api/v1/stores/{store['id']}", json={"location": "Indore"})
    assert updated.status_code == 200
    assert updated.json()["location"] == "Indore"

    deleted = client.delete(f"/api/v1/stores/{store['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["is_active"] is False


def test_seeded_inventory_totals_and_filters(client):
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 10
        assert session.scalar(select(func.count()).select_from(Store)) == 3
        assert session.scalar(select(func.count()).select_from(InventoryBalance)) == 30
        assert session.scalar(select(func.sum(InventoryBalance.quantity))) == 396
        totals = {
            store.name: session.scalar(
                select(func.sum(InventoryBalance.quantity)).where(
                    InventoryBalance.store_id == store.id
                )
            )
            for store in session.scalars(select(Store)).all()
        }
        assert totals == {"Central Store": 193, "City Centre": 89, "Riverside Outlet": 114}


    with SessionLocal() as session:
        result = seed_database(session)
        assert result["products"] == 10
        assert result["stores"] == 3
        assert result["balances"] == 30
        assert result["units"] == 396

    all_inventory = client.get("/api/v1/inventory", params={"limit": 200}).json()
    assert all_inventory["total"] == 30
    assert len(all_inventory["items"]) == 30

    product_id, central_id, _city_id = seeded_ids(client)
    filtered = client.get(
        "/api/v1/inventory", params={"product_id": product_id, "store_id": central_id}
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["quantity"] == 24


def test_inventory_search_status_and_balance_detail(client):
    product_id, central_id, _city_id = seeded_ids(client)
    search = client.get("/api/v1/inventory", params={"search": "Wireless Mouse"})
    assert search.json()["total"] == 3
    sku = client.get("/api/v1/inventory", params={"sku": "el-001"})
    assert sku.json()["total"] == 3

    out = client.get("/api/v1/inventory", params={"status": "out_of_stock"})
    assert out.status_code == 200
    assert all(row["quantity"] == 0 for row in out.json()["items"])
    assert out.json()["total"] > 0

    detail = client.get(f"/api/v1/inventory/{product_id}/{central_id}")
    assert detail.status_code == 200
    assert detail.json()["quantity"] == 24


def test_product_edits_do_not_change_inventory(client):
    product_id, central_id, _city_id = seeded_ids(client)
    before = client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()
    updated = client.patch(f"/api/v1/products/{product_id}", json={"name": "Mouse v2"})
    after = client.get(f"/api/v1/inventory/{product_id}/{central_id}").json()
    assert updated.status_code == 200
    assert after["quantity"] == before["quantity"] == 24
    assert after["reorder_level"] == before["reorder_level"] == 8


def test_not_found_product_and_store_endpoints(client):
    assert client.get("/api/v1/products/999999").status_code == 404
    assert client.get("/api/v1/stores/999999").status_code == 404
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import InventoryBalance
from app.schemas.product import ProductCreate
from app.schemas.store import StoreCreate
from app.services import products as product_service, stores as store_service


def test_concurrent_product_and_store_creation_provisions_shared_balance(client):
    gate = Barrier(2)
    def create_product():
        with SessionLocal() as session:
            return product_service.create_product(session, ProductCreate(
                sku="RACE-001", name="Race product", category="Audit", price="1.00"
            )).id

    def create_store():
        with SessionLocal() as session:
            return store_service.create_store(session, StoreCreate(
                code="RACE-001", name="Race store", location="Audit"
            )).id

    # Start both transactions together to exercise the provisioning lock.
    def ready_product():
        gate.wait(timeout=10)
        return create_product()

    def ready_store():
        gate.wait(timeout=10)
        return create_store()

    with ThreadPoolExecutor(max_workers=2) as pool:
        product_future = pool.submit(ready_product)
        store_future = pool.submit(ready_store)
        product_id = product_future.result(timeout=15)
        store_id = store_future.result(timeout=15)
    with SessionLocal() as session:
        assert session.scalar(select(InventoryBalance.id).where(
            InventoryBalance.product_id == product_id,
            InventoryBalance.store_id == store_id,
        )) is not None


def test_reactivation_provisions_only_missing_balances(client):
    product = client.post("/api/v1/products", json={
        "sku": "REACT-001", "name": "Reactivated", "category": "Audit", "price": "1.00"
    }).json()
    client.delete(f"/api/v1/products/{product['id']}")
    store = client.post("/api/v1/stores", json={
        "code": "REACT-001", "name": "Reactivation store", "location": "Audit"
    }).json()
    assert client.patch(f"/api/v1/products/{product['id']}", json={"is_active": True}).status_code == 200
    assert client.get(f"/api/v1/inventory/{product['id']}/{store['id']}").status_code == 200

    inactive_store = client.post("/api/v1/stores", json={
        "code": "REACT-002", "name": "Reactivation store two", "location": "Audit"
    }).json()
    client.delete(f"/api/v1/stores/{inactive_store['id']}")
    later_product = client.post("/api/v1/products", json={
        "sku": "REACT-002", "name": "Later product", "category": "Audit", "price": "1.00"
    }).json()
    assert client.patch(f"/api/v1/stores/{inactive_store['id']}", json={"is_active": True}).status_code == 200
    assert client.get(f"/api/v1/inventory/{later_product['id']}/{inactive_store['id']}").status_code == 200
