def seeded_ids(client):
    product_response = client.get("/api/v1/products", params={"search": "Wireless Mouse"})
    store_response = client.get("/api/v1/stores", params={"limit": 100})
    assert product_response.status_code == 200
    assert store_response.status_code == 200
    product = product_response.json()["items"][0]
    central = next(
        store for store in store_response.json()["items"] if store["code"] == "ST-001"
    )
    city = next(
        store for store in store_response.json()["items"] if store["code"] == "ST-002"
    )
    return product["id"], central["id"], city["id"]
