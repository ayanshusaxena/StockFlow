import heapq

from sqlalchemy.orm import Session

from app.repositories import inventory as inventory_repository


def prioritised_replenishment(session: Session, *, store_id: int | None = None) -> list[dict[str, object]]:
    """Sort by largest reorder deficit, then reorder level, SKU, and store code.

    The heap is built in O(n log n); stable business keys make results deterministic.
    No demand prediction or sales velocity is inferred.
    """
    heap: list[tuple[tuple[object, ...], object]] = []
    for balance in inventory_repository.replenishment_candidates(session, store_id=store_id):
        product = balance.product
        store = balance.store
        deficit = max(balance.reorder_level - balance.quantity, 0)
        priority_key = (
            -deficit,
            -balance.reorder_level,
            product.sku.casefold(),
            store.code.casefold(),
            product.id,
            store.id,
        )
        heapq.heappush(heap, (priority_key, balance))

    result: list[dict[str, object]] = []
    while heap:
        key, balance = heapq.heappop(heap)
        product = balance.product
        store = balance.store
        deficit = max(balance.reorder_level - balance.quantity, 0)
        result.append(
            {
                "inventory_id": balance.id,
                "product_id": product.id,
                "sku": product.sku,
                "product_name": product.name,
                "store_id": store.id,
                "store_code": store.code,
                "store_name": store.name,
                "quantity": balance.quantity,
                "reorder_level": balance.reorder_level,
                "deficit": deficit,
                "suggested_quantity": max(balance.reorder_level * 2 - balance.quantity, 0),
                "priority": len(result) + 1,
            }
        )
    return result
