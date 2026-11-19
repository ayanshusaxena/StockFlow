def test_dashboard_summary_and_sku_lookup_are_database_backed(client):
    summary = client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["total_units"] == 396
    assert summary.json()["product_count"] == 10
    assert summary.json()["store_count"] == 3
    assert summary.json()["out_of_stock_balances"] == 3

    lookup = client.get("/api/v1/products/lookup/%20el-001%20")
    assert lookup.status_code == 200
    assert lookup.json()["sku"] == "EL-001"
    assert client.get("/api/v1/products/lookup/MISSING").status_code == 404


def test_replenishment_api_filters_and_returns_deterministic_priority(client):
    all_items = client.get("/api/v1/inventory/replenishment?limit=200").json()
    assert all_items["total"] > 0
    assert all(
        row["quantity"] <= row["reorder_level"] for row in all_items["items"]
    )
    assert all(
        row["deficit"] == row["reorder_level"] - row["quantity"]
        for row in all_items["items"]
    )
    assert [row["priority"] for row in all_items["items"]] == list(
        range(1, len(all_items["items"]) + 1)
    )

    out_items = client.get("/api/v1/inventory/replenishment?urgency=out").json()["items"]
    assert out_items
    assert all(row["quantity"] == 0 for row in out_items)
    low_items = client.get("/api/v1/inventory/replenishment?urgency=low").json()["items"]
    assert all(0 < row["quantity"] <= row["reorder_level"] for row in low_items)

    stores = client.get("/api/v1/stores").json()["items"]
    central_id = next(row["id"] for row in stores if row["code"] == "ST-001")
    central = client.get(
        f"/api/v1/inventory/replenishment?store_id={central_id}&urgency=out"
    ).json()["items"]
    assert all(row["store_id"] == central_id and row["quantity"] == 0 for row in central)


def test_movement_write_requires_an_idempotency_key(client):
    product = client.get("/api/v1/products/lookup/EL-001").json()
    store = client.get("/api/v1/stores").json()["items"][0]
    response = client.post(
        "/api/v1/inventory/movements/sale",
        json={"product_id": product["id"], "store_id": store["id"], "quantity": 1},
        headers={"Idempotency-Key": ""},
    )
    assert response.status_code == 422


def test_cors_allows_local_vite_origin_and_movement_headers(client):
    response = client.options(
        "/api/v1/inventory/movements/sale",
        headers={
            "Origin": "http://localhost:8443",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,idempotency-key",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8443"

