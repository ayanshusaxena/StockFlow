from sqlalchemy import func, select, text


def test_csv_rejects_malformed_quoting_and_integer_overflow(client):
    malformed = client.post(
        "/api/v1/inventory/import/preview",
        content=b'SKU,Store,Quantity\nEL-001,ST-001,"30',
    )
    assert malformed.status_code == 409
    overflow = client.post(
        "/api/v1/inventory/import/preview",
        content=b"SKU,Store,Quantity\nEL-001,ST-001,2147483648\n",
    )
    assert overflow.status_code == 200
    assert overflow.json()["can_commit"] is False


def test_ambiguous_other_store_does_not_block_csv(client):
    for code, name in (("AMB-A", "Audit Store"), ("AMB-B", "audit store")):
        assert client.post("/api/v1/stores", json={
            "code": code, "name": name, "location": "Audit"
        }).status_code == 201
    preview = client.post(
        "/api/v1/inventory/import/preview",
        content=b"SKU,Store,Quantity\nEL-001,ST-001,30\n",
    )
    assert preview.status_code == 200
    assert preview.json()["can_commit"] is True

from app.db.session import SessionLocal, engine
from app.models import ActivityHistory, StockMovement


def test_csv_preview_commit_updates_balances_and_store_filtered_activity(client):
    content = (
        "SKU,Store,Quantity,Reorder Level\n"
        " el-001 , st-001 ,30,8\n"
        "EL-002,City Centre,0,\n"
    ).encode()
    preview = client.post(
        "/api/v1/inventory/import/preview?filename=stock.csv",
        content=content,
        headers={"Content-Type": "text/csv"},
    )
    assert preview.status_code == 200
    assert preview.json()["can_commit"] is True
    assert preview.json()["accepted_count"] == 2
    assert preview.json()["rejected_count"] == 0

    imported = client.post(
        "/api/v1/inventory/import/commit?filename=stock.csv",
        content=content,
        headers={"Content-Type": "text/csv", "Idempotency-Key": "csv-import-commit-001"},
    )
    assert imported.status_code == 201
    assert imported.json()["imported_count"] == 2
    assert imported.json()["history_entries"] == 2
    replay = client.post(
        "/api/v1/inventory/import/commit?filename=stock.csv",
        content=content,
        headers={"Content-Type": "text/csv", "Idempotency-Key": "csv-import-commit-001"},
    )
    assert replay.status_code == 201
    assert replay.json() == imported.json()
    conflict = client.post(
        "/api/v1/inventory/import/commit?filename=stock.csv",
        content=b"sku,store,quantity\nEL-001,ST-001,5\n",
        headers={"Content-Type": "text/csv", "Idempotency-Key": "csv-import-commit-001"},
    )
    assert conflict.status_code == 409

    products = {item["sku"]: item["id"] for item in client.get("/api/v1/products").json()["items"]}
    stores = {item["code"]: item["id"] for item in client.get("/api/v1/stores").json()["items"]}
    assert client.get(f"/api/v1/inventory/{products['EL-001']}/{stores['ST-001']}").json()["quantity"] == 30
    assert client.get(f"/api/v1/inventory/{products['EL-002']}/{stores['ST-002']}").json()["quantity"] == 0

    central = client.get(
        "/api/v1/inventory/activities", params={"store_id": stores["ST-001"]}
    ).json()["items"]
    assert all(row["store_id"] == stores["ST-001"] for row in central)
    assert any(row["event_type"] == "csv_import" and row["is_batch"] for row in central)

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(StockMovement)) == 5
        assert session.scalar(
            select(func.count()).select_from(ActivityHistory).where(
                ActivityHistory.event_type == "csv_import"
            )
        ) == 3  # one original batch fixture plus two imported rows


def test_csv_all_or_nothing_rejects_every_write_if_any_row_is_invalid(client):
    content = (
        "sku,store_code,quantity\n"
        "EL-001,ST-001,42\n"
        "MISSING,ST-001,9\n"
    ).encode()
    before = client.get("/api/v1/inventory").json()["items"][0]
    preview = client.post("/api/v1/inventory/import/preview", content=content).json()
    assert preview["accepted_count"] == 1
    assert preview["rejected_count"] == 1
    assert preview["can_commit"] is False

    response = client.post(
        "/api/v1/inventory/import/commit",
        content=content,
        headers={"Idempotency-Key": "csv-invalid-commit"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["details"][0]["row_number"] == 3
    after = client.get(f"/api/v1/inventory/{before['product']['id']}/{before['store']['id']}").json()
    assert after["quantity"] == before["quantity"]


def test_csv_reports_duplicate_and_invalid_quantity_rows(client):
    content = (
        "sku,store,quantity\n"
        "EL-001,ST-001,10\n"
        "EL-001,ST-001,11\n"
        "EL-002,ST-002,-2\n"
    ).encode()
    preview = client.post("/api/v1/inventory/import/preview", content=content).json()
    assert preview["accepted_count"] == 1
    assert preview["rejected_count"] == 2
    assert "Duplicate SKU/store" in preview["rejected_rows"][0]["errors"][0]
    assert "whole number" in preview["rejected_rows"][1]["errors"][0]


def test_csv_requires_expected_headers_and_empty_import_is_blocked(client):
    response = client.post("/api/v1/inventory/import/preview", content=b"product,qty\nMouse,2\n")
    assert response.status_code == 409
    empty = client.post(
        "/api/v1/inventory/import/commit",
        content=b"sku,store,quantity\n",
        headers={"Idempotency-Key": "csv-empty-commit"},
    )
    assert empty.status_code == 409


def test_csv_database_failure_rolls_back_balances_and_import_history(client):
    products = {item["sku"]: item["id"] for item in client.get("/api/v1/products").json()["items"]}
    stores = {item["code"]: item["id"] for item in client.get("/api/v1/stores").json()["items"]}
    product_id, store_id = products["EL-001"], stores["ST-001"]
    before = client.get(f"/api/v1/inventory/{product_id}/{store_id}").json()["quantity"]
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE OR REPLACE FUNCTION reject_stockflow_csv_activity() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN IF NEW.event_type = 'csv_import' THEN "
                "RAISE EXCEPTION 'forced import activity failure'; END IF; RETURN NEW; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER reject_stockflow_csv_activity BEFORE INSERT ON activity_history "
                "FOR EACH ROW EXECUTE FUNCTION reject_stockflow_csv_activity()"
            )
        )
    try:
        response = client.post(
            "/api/v1/inventory/import/commit",
            content=b"sku,store,quantity\nEL-001,ST-001,42\n",
            headers={"Idempotency-Key": "csv-rollback-test"},
        )
        assert response.status_code == 500
        assert client.get(f"/api/v1/inventory/{product_id}/{store_id}").json()["quantity"] == before
        with SessionLocal() as session:
            assert session.scalar(
                select(func.count()).select_from(ActivityHistory).where(
                    ActivityHistory.product_id == product_id,
                    ActivityHistory.store_id == store_id,
                    ActivityHistory.event_type == "csv_import",
                )
            ) == 0
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER IF EXISTS reject_stockflow_csv_activity ON activity_history"))
            connection.execute(text("DROP FUNCTION IF EXISTS reject_stockflow_csv_activity()"))
