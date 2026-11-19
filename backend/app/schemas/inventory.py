from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockStatus(StrEnum):
    OUT_OF_STOCK = "out_of_stock"
    BELOW_REORDER = "below_reorder"
    HEALTHY = "healthy"


class ProductBrief(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    price: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class StoreBrief(BaseModel):
    id: int
    code: str
    name: str
    location: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class InventoryRead(BaseModel):
    id: int
    product: ProductBrief
    store: StoreBrief
    quantity: int
    reorder_level: int
    status: StockStatus
    updated_at: datetime


class InventoryPage(BaseModel):
    items: list[InventoryRead]
    skip: int
    limit: int
    total: int


class ReplenishmentItem(BaseModel):
    inventory_id: int
    product_id: int
    sku: str
    product_name: str
    store_id: int
    store_code: str
    store_name: str
    quantity: int
    reorder_level: int
    deficit: int
    suggested_quantity: int
    priority: int


class ReplenishmentPage(BaseModel):
    items: list[ReplenishmentItem]
    total: int


class ImportAcceptedRow(BaseModel):
    row_number: int
    sku: str
    product_name: str
    store_code: str
    store_name: str
    old_quantity: int
    new_quantity: int
    reorder_level: int


class ImportRejectedRow(BaseModel):
    row_number: int
    values: dict[str, str]
    errors: list[str]


class InventoryImportPreview(BaseModel):
    file_name: str
    policy: str
    total_rows: int
    accepted_count: int
    rejected_count: int
    can_commit: bool
    accepted_rows: list[ImportAcceptedRow]
    rejected_rows: list[ImportRejectedRow]


class InventoryImportResult(InventoryImportPreview):
    imported_count: int
    changed_units: int
    history_entries: int


class MovementType(StrEnum):
    SALE = "sale"
    RESTOCK = "restock"
    ADJUSTMENT = "adjustment"


class SaleCreate(BaseModel):
    product_id: int = Field(gt=0, strict=True)
    store_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, strict=True)
    note: str = Field(default="", max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RestockCreate(BaseModel):
    product_id: int = Field(gt=0, strict=True)
    store_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, strict=True)
    note: str = Field(default="", max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AdjustmentCreate(BaseModel):
    product_id: int = Field(gt=0, strict=True)
    store_id: int = Field(gt=0, strict=True)
    quantity_delta: int = Field(strict=True)
    note: str = Field(default="", max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("quantity_delta")
    @classmethod
    def nonzero_adjustment(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_delta must not be zero")
        return value


class MovementRead(BaseModel):
    id: int
    product_id: int
    store_id: int
    movement_type: MovementType
    quantity_delta: int
    quantity_before: int
    quantity_after: int
    note: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovementPage(BaseModel):
    items: list[MovementRead]
    skip: int
    limit: int
    total: int


class ActivityRead(BaseModel):
    id: int
    movement_id: int | None
    product_id: int | None
    store_id: int | None
    event_type: str
    product_name: str
    sku: str | None
    store_name: str
    quantity_delta: int
    note: str
    is_batch: bool
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityPage(BaseModel):
    items: list[ActivityRead]
    skip: int
    limit: int
    total: int
