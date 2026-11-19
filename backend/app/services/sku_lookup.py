from collections.abc import Iterable
from typing import TypeVar


T = TypeVar("T")


class DuplicateSKUError(ValueError):
    pass


def build_sku_index(products: Iterable[T], *, sku_getter=lambda product: product.sku) -> dict[str, T]:
    """Build an O(n) normalized SKU index; subsequent lookups are O(1) average case."""
    index: dict[str, T] = {}
    for product in products:
        sku = str(sku_getter(product)).strip().upper()
        if sku in index:
            raise DuplicateSKUError(f"Duplicate SKU encountered: {sku}")
        index[sku] = product
    return index


def find_by_sku(index: dict[str, T], sku: str) -> T | None:
    return index.get(sku.strip().upper())
