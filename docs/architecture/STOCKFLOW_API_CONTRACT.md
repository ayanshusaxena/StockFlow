# StockFlow API Contract — Integrated MVP

**Status:** Implemented local API contract for the integrated academic MVP. It is not a public or authenticated API.

Base path: `/api/v1`. OpenAPI JSON: `/openapi.json`. Interactive docs: `/docs`.

## Conventions

- Internal product and store identifiers are positive integers. SKU and store code remain unique business identifiers.
- List responses use `{ "items": [...], "skip": 0, "limit": 50, "total": 0 }`. `skip` defaults to 0; `limit` defaults to 50 and is capped at 200.
- Money is represented as decimal values with two fractional digits and stored as `NUMERIC(12,2)`.
- Timestamps are timezone-aware UTC values.
- `status` for a balance is `out_of_stock` when quantity is zero; `below_reorder` when positive quantity is at or below reorder level; otherwise `healthy`.
- Validation failures return 422; missing records return 404; duplicate/insufficient-stock conflicts return 409. Errors share `{ "error": { "code": "...", "message": "...", "details": [...] } }`.
- Movement writes and CSV commits require an `Idempotency-Key` header (1–128 characters). Exact retries return the stored result; conflicting reuse returns 409.
- CORS is configured for local Vite origins by default. CORS does not authenticate callers. There is no auth, tenant context, or role-based access control.

## Endpoint inventory

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Database `SELECT 1` health check; 503 if unavailable. |
| GET | `/api/v1/dashboard/summary` | Database-backed total units, active counts, stock health, and recent activity. |
| GET | `/api/v1/products` | Search by SKU/name, filter by category, paginate; inactive omitted unless requested. |
| GET | `/api/v1/products/lookup/{sku}` | Normalized active SKU lookup; 404 if missing or inactive. |
| POST | `/api/v1/products` | Create unique SKU and zero balances for active stores. |
| GET | `/api/v1/products/{product_id}` | Retrieve product. |
| PATCH | `/api/v1/products/{product_id}` | Edit catalogue fields/active state; no stock mutation. |
| DELETE | `/api/v1/products/{product_id}` | Soft-deactivate product and retain history. |
| GET | `/api/v1/stores` | Paginated active stores by default. |
| POST | `/api/v1/stores` | Create store and zero balances for each active product. |
| GET | `/api/v1/stores/{store_id}` | Retrieve store. |
| PATCH | `/api/v1/stores/{store_id}` | Edit store fields/active state. |
| DELETE | `/api/v1/stores/{store_id}` | Soft-deactivate store and retain history. |
| GET | `/api/v1/inventory` | Paginate/filter by `store_id`, `product_id`, `sku`, `search`, `status`; include inactive with `include_inactive=true`. |
| GET | `/api/v1/inventory/{product_id}/{store_id}` | Retrieve one balance. |
| POST | `/api/v1/inventory/movements/sale` | Atomic sale and history write. |
| POST | `/api/v1/inventory/movements/restock` | Atomic restock and history write. |
| POST | `/api/v1/inventory/movements/adjustment` | Atomic signed adjustment and history write. |
| GET | `/api/v1/inventory/movements` | Paginated movement history; filter by product/store. |
| GET | `/api/v1/inventory/activities` | Paginated activity history; filter by product/store. |
| GET | `/api/v1/inventory/replenishment` | Heap-prioritized active low/out-of-stock queue; optional `store_id` and `urgency=out|low`. |
| POST | `/api/v1/inventory/import/preview` | Raw UTF-8 CSV body (`text/csv`); validates required columns, active SKU/store references, quantities, duplicate SKU/store pairs, and reports accepted/rejected rows without writes. |
| POST | `/api/v1/inventory/import/commit` | Same CSV body and required `Idempotency-Key`; all-or-nothing snapshot update and store-scoped batch activity records. |

## Movement examples

Sale request:

```json
{
  "product_id": 1,
  "store_id": 1,
  "quantity": 2,
  "note": "POS sale"
}
```

Successful request also includes `Idempotency-Key: <unique-operation-key>`. A retry with the same key and identical request returns the original movement; reuse with a different payload returns 409.

Successful response (UTC timestamp abbreviated):

```json
{
  "id": 6,
  "product_id": 1,
  "store_id": 1,
  "movement_type": "sale",
  "quantity_delta": -2,
  "quantity_before": 24,
  "quantity_after": 22,
  "note": "POS sale",
  "created_at": "2026-11-19T15:10:00Z"
}
```

Restock uses a positive `quantity`. Adjustment uses a nonzero signed `quantity_delta`; a negative result is rejected. Both return the same movement shape with 201 on success.

Insufficient-stock response:

```json
{
  "error": {
    "code": "insufficient_stock",
    "message": "Insufficient stock: 1 available, 2 requested.",
    "details": null
  }
}
```

## Product creation example

```json
{
  "sku": "NEW-101",
  "name": "New Item",
  "category": "Accessories",
  "price": "12.50",
  "default_reorder_level": 4
}
```

The new product gets a zero-quantity row per active store at reorder level 4. Ordinary product PATCH requests do not update any balance or threshold.

## CSV inventory snapshot contract

Required headers are `SKU`, `Store` (store name or store code), and `Quantity`; `Reorder Level` is optional. Headers are case/spacing insensitive. Quantities are nonnegative integers. Active products and stores only are accepted, and duplicate SKU/store pairs reject the later row. Files are limited to 5 MiB and 5,000 data rows.

The preview response separates accepted and rejected rows with source row numbers and row-level errors. Commit uses an all-or-nothing policy: no rows are applied if there are no accepted rows or any rejected row. Accepted rows set the inventory quantity as an absolute snapshot, apply an optional reorder level, and write one `csv_import` activity record per row in the same transaction. The CSV endpoint does not create stock movement rows because the movement model intentionally represents sale, restock, and adjustment events only. Repeated identical commits with the same key return the saved result; a different file with that key returns 409.

## Replenishment ordering

Only active balance records with quantity at or below reorder level are included. Order is largest `reorder_level - quantity` deficit first, then higher reorder level, normalized SKU, store code, and stable numeric identifiers. Suggested quantity is `max(2 × reorder_level - quantity, 0)`. This is a deterministic inventory rule, not demand forecasting.
