from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ActivityHistory, InventoryBalance, Product, StockMovement, Store


LOCAL_TZ = ZoneInfo("Asia/Kolkata")

STORE_FIXTURES = [
    {"code": "ST-001", "name": "Central Store", "location": "Gwalior"},
    {"code": "ST-002", "name": "City Centre", "location": "Gwalior"},
    {"code": "ST-003", "name": "Riverside Outlet", "location": "Gwalior"},
]

PRODUCT_FIXTURES = [
    ("EL-001", "Wireless Mouse", "Electronics", "799.00", 8),
    ("EL-002", "Mechanical Keyboard", "Electronics", "2499.00", 5),
    ("EL-003", "USB-C Hub", "Accessories", "1499.00", 6),
    ("EL-004", "Laptop Stand", "Accessories", "999.00", 6),
    ("EL-005", "Bluetooth Speaker", "Electronics", "1899.00", 6),
    ("OF-001", "A4 Notebook", "Stationery", "120.00", 15),
    ("OF-002", "Gel Pen Pack", "Stationery", "90.00", 10),
    ("OF-003", "Desk Organiser", "Office Supplies", "349.00", 5),
    ("AC-001", "Phone Charger", "Accessories", "599.00", 6),
    ("AC-002", "USB-C Cable", "Accessories", "299.00", 10),
]

QUANTITIES = [
    [24, 6, 0],
    [11, 3, 7],
    [8, 0, 14],
    [18, 5, 10],
    [4, 9, 0],
    [44, 28, 36],
    [32, 18, 24],
    [9, 2, 12],
    [16, 6, 3],
    [27, 12, 8],
]


def local_time(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=LOCAL_TZ).astimezone(timezone.utc)


ACTIVITY_FIXTURES = [
    {
        "key": "a1", "event": "sale", "sku": "EL-001", "store": "ST-001",
        "delta": -2, "note": "Counter sale recorded", "at": local_time(2025, 6, 18, 10, 42),
    },
    {
        "key": "a2", "event": "restock", "sku": "OF-001", "store": "ST-002",
        "delta": 20, "note": "Stock delivery received", "at": local_time(2025, 6, 18, 9, 18),
    },
    {
        "key": "a3", "event": "adjustment", "sku": "AC-002", "store": "ST-002",
        "delta": -1, "note": "Damaged unit removed", "at": local_time(2025, 6, 17, 16, 20),
    },
    {
        "key": "a4", "event": "csv_import", "sku": None, "store": None,
        "delta": 34, "note": "inventory_june.csv · 6 records",
        "at": local_time(2025, 6, 17, 14, 8), "batch": True,
    },
    {
        "key": "a5", "event": "sale", "sku": "EL-002", "store": "ST-002",
        "delta": -1, "note": "Counter sale recorded", "at": local_time(2025, 6, 17, 11, 35),
    },
    {
        "key": "a6", "event": "restock", "sku": "AC-001", "store": "ST-001",
        "delta": 12, "note": "Stock delivery received", "at": local_time(2025, 6, 16, 15, 12),
    },
]


def seed_database(session: Session) -> dict[str, object]:
    """Insert missing demonstration rows while preserving any existing operational state."""
    with session.begin():
        store_by_code: dict[str, Store] = {}
        for fixture in STORE_FIXTURES:
            store = session.scalar(select(Store).where(Store.code == fixture["code"]))
            if store is None:
                store = Store(**fixture)
                session.add(store)
                session.flush()
            store_by_code[fixture["code"]] = store

        product_by_sku: dict[str, Product] = {}
        for sku, name, category, price, _reorder in PRODUCT_FIXTURES:
            product = session.scalar(select(Product).where(Product.sku == sku))
            if product is None:
                from decimal import Decimal

                product = Product(
                    sku=sku, name=name, category=category, price=Decimal(price)
                )
                session.add(product)
                session.flush()
            product_by_sku[sku] = product

        existing_pairs = set(
            session.execute(
                select(InventoryBalance.product_id, InventoryBalance.store_id)
            ).all()
        )
        for product_index, (sku, _name, _category, _price, reorder) in enumerate(PRODUCT_FIXTURES):
            product = product_by_sku[sku]
            for store_index, store_fixture in enumerate(STORE_FIXTURES):
                store = store_by_code[store_fixture["code"]]
                pair = (product.id, store.id)
                if pair in existing_pairs:
                    continue
                if store_index == 0:
                    updated = local_time(2025, 6, 18, 10, 42)
                elif store_index == 1:
                    updated = local_time(2025, 6, 17, 16, 20)
                else:
                    updated = local_time(2025, 6, 17, 14, 8)
                session.add(
                    InventoryBalance(
                        product_id=product.id,
                        store_id=store.id,
                        quantity=QUANTITIES[product_index][store_index],
                        reorder_level=reorder,
                        updated_at=updated,
                    )
                )
                existing_pairs.add(pair)
        session.flush()

        for fixture in ACTIVITY_FIXTURES:
            if session.scalar(
                select(ActivityHistory.id).where(ActivityHistory.seed_key == fixture["key"])
            ) is not None:
                continue

            product = product_by_sku.get(fixture["sku"]) if fixture["sku"] else None
            store = store_by_code.get(fixture["store"]) if fixture["store"] else None
            movement = None
            if fixture["event"] != "csv_import":
                balance = session.scalar(
                    select(InventoryBalance).where(
                        InventoryBalance.product_id == product.id,
                        InventoryBalance.store_id == store.id,
                    )
                )
                movement = StockMovement(
                    product_id=product.id,
                    store_id=store.id,
                    movement_type=fixture["event"],
                    quantity_delta=fixture["delta"],
                    quantity_before=balance.quantity - fixture["delta"],
                    quantity_after=balance.quantity,
                    note=fixture["note"],
                    seed_key=f"seed-{fixture['key']}",
                    created_at=fixture["at"],
                )
                session.add(movement)
                session.flush()

            session.add(
                ActivityHistory(
                    movement_id=movement.id if movement else None,
                    product_id=product.id if product else None,
                    store_id=store.id if store else None,
                    event_type=fixture["event"],
                    product_name=product.name if product else "Inventory import",
                    sku=product.sku if product else None,
                    store_name=store.name if store else "3 stores",
                    quantity_delta=fixture["delta"],
                    note=fixture["note"],
                    is_batch=fixture.get("batch", False),
                    seed_key=fixture["key"],
                    occurred_at=fixture["at"],
                )
            )

    product_count = session.scalar(select(func.count()).select_from(Product))
    store_count = session.scalar(select(func.count()).select_from(Store))
    balance_count = session.scalar(select(func.count()).select_from(InventoryBalance))
    units = session.scalar(select(func.sum(InventoryBalance.quantity))) or 0
    store_totals = {
        store.name: session.scalar(
            select(func.sum(InventoryBalance.quantity)).where(InventoryBalance.store_id == store.id)
        ) or 0
        for store in store_by_code.values()
    }
    return {
        "products": product_count,
        "stores": store_count,
        "balances": balance_count,
        "units": units,
        "store_totals": store_totals,
    }


def main() -> None:
    with SessionLocal() as session:
        result = seed_database(session)
    print(
        "Seed complete: "
        f"{result['products']} products, {result['stores']} stores, "
        f"{result['balances']} balances, {result['units']} units, "
        f"store totals={result['store_totals']}"
    )


if __name__ == "__main__":
    main()
