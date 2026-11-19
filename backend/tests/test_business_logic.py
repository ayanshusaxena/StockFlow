from types import SimpleNamespace

import pytest

from app.services import replenishment
from app.services.sku_lookup import DuplicateSKUError, build_sku_index, find_by_sku


def test_sku_lookup_normalizes_sku_and_returns_product():
    product = SimpleNamespace(sku="EL-001", name="Mouse")
    index = build_sku_index([product])
    assert find_by_sku(index, " el-001 ") is product


def test_sku_lookup_returns_none_for_missing_sku():
    assert find_by_sku(build_sku_index([]), "NO-SUCH-SKU") is None


def test_sku_index_rejects_duplicate_normalized_skus():
    with pytest.raises(DuplicateSKUError, match="Duplicate SKU"):
        build_sku_index([SimpleNamespace(sku="EL-001"), SimpleNamespace(sku=" el-001 ")])


def _balance(sku, store_code, quantity, reorder, *, product_id=1, store_id=1):
    product = SimpleNamespace(id=product_id, sku=sku, name=f"Product {sku}")
    store = SimpleNamespace(id=store_id, code=store_code, name=f"Store {store_code}")
    return SimpleNamespace(
        id=product_id * 100 + store_id,
        product_id=product_id,
        store_id=store_id,
        quantity=quantity,
        reorder_level=reorder,
        product=product,
        store=store,
    )


def test_replenishment_orders_largest_deficit_then_stable_sku_store(monkeypatch):
    rows = [
        _balance("SKU-B", "ST-002", 1, 5, product_id=2, store_id=2),
        _balance("SKU-A", "ST-003", 1, 5, product_id=1, store_id=3),
        _balance("SKU-A", "ST-001", 1, 5, product_id=1, store_id=1),
        _balance("SKU-Z", "ST-001", 0, 10, product_id=3, store_id=1),
    ]
    monkeypatch.setattr(
        replenishment.inventory_repository,
        "replenishment_candidates",
        lambda _session, store_id=None: [row for row in rows if store_id is None or row.store_id == store_id],
    )
    result = replenishment.prioritised_replenishment(object())
    assert [row["sku"] for row in result] == ["SKU-Z", "SKU-A", "SKU-A", "SKU-B"]
    assert [row["store_code"] for row in result[1:3]] == ["ST-001", "ST-003"]
    assert [row["priority"] for row in result] == [1, 2, 3, 4]
    assert result[0]["suggested_quantity"] == 20


def test_replenishment_filters_store_and_empty_queue(monkeypatch):
    rows = [_balance("SKU-A", "ST-001", 0, 6, store_id=1)]
    monkeypatch.setattr(
        replenishment.inventory_repository,
        "replenishment_candidates",
        lambda _session, store_id=None: [row for row in rows if store_id is None or row.store_id == store_id],
    )
    assert replenishment.prioritised_replenishment(object(), store_id=2) == []

