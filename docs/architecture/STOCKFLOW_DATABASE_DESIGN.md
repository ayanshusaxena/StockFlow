# StockFlow Database Design

**Database:** PostgreSQL 18 tested; SQLAlchemy 2.x models; Alembic-managed schema. Monetary values use `NUMERIC(12,2)`. Timestamps use timezone-aware PostgreSQL `TIMESTAMP WITH TIME ZONE`; connections are set to UTC.

## Entity relationships

```mermaid
erDiagram
  PRODUCTS ||--o{ INVENTORY_BALANCES : has
  STORES ||--o{ INVENTORY_BALANCES : holds
  INVENTORY_BALANCES ||--o{ STOCK_MOVEMENTS : records
  STOCK_MOVEMENTS ||--o| ACTIVITY_HISTORY : summarizes
  PRODUCTS ||--o{ ACTIVITY_HISTORY : snapshots
  STORES ||--o{ ACTIVITY_HISTORY : snapshots
  STOCK_MOVEMENTS ||--o| IDEMPOTENCY_RECORDS : replays
  PRODUCTS {
    int id PK
    string sku UK
    string name
    string category
    decimal price
    boolean is_active
    timestamptz created_at
    timestamptz updated_at
  }
  STORES {
    int id PK
    string code UK
    string name UK
    string location
    boolean is_active
  }
  INVENTORY_BALANCES {
    int id PK
    int product_id FK
    int store_id FK
    int quantity
    int reorder_level
    timestamptz updated_at
  }
  STOCK_MOVEMENTS {
    int id PK
    int product_id FK
    int store_id FK
    string movement_type
    int quantity_delta
    int quantity_before
    int quantity_after
    timestamptz created_at
  }
  ACTIVITY_HISTORY {
    int id PK
    int movement_id FK
    int product_id FK
    int store_id FK
    string event_type
    int quantity_delta
    boolean is_batch
    timestamptz occurred_at
  }
  IDEMPOTENCY_RECORDS {
    string key PK
    string request_hash
    int movement_id FK UK
  }
  IMPORT_BATCHES {
    string idempotency_key PK
    string request_hash
    json result_payload
    timestamptz created_at
  }
```

`stock_movements(product_id, store_id)` has a composite foreign key to the matching unique inventory balance pair. Activity stores nullable entity references and display snapshots. Committed CSV imports record one store-scoped batch activity per imported row; the original seed CSV summary remains a global batch activity without one store.

## Constraints and indexes

- Products: primary key; unique indexed SKU; nonnegative decimal price; indexed name and category; soft-delete flag.
- Stores: primary key; unique indexed store code and name; soft-delete flag.
- Inventory balances: foreign keys to product and store; unique `(product_id, store_id)`; nonnegative integer quantity and reorder level; store filter index.
- Stock movements: composite foreign key to a balance; valid type; nonzero signed delta; before/after nonnegative; `quantity_after = quantity_before + quantity_delta`; sale delta is negative, restock delta positive; indexed by product/store/time and by time; nullable unique seed key.
- Activity history: nullable foreign keys to movement/product/store with `SET NULL` on hard deletion; valid event type; one activity per non-null movement; occurrence/product/store indexes; nullable unique seed key.
- Idempotency records: primary idempotency key, request fingerprint, and unique movement reference. The row and stock mutation share one transaction.
- Import batches: primary idempotency key, content fingerprint, JSON result, and creation timestamp. The import result and inventory snapshot changes share one transaction.

Products, stores, and balances referenced by movement history are normally soft-deactivated, not hard-deleted.

## Migration history

1. `20261119_0001_initial_schema` creates products, stores, balances, movements, activity history, constraints, and baseline indexes.
2. `20261119_0002_history_query_indexes` adds the store-only balance index and unfiltered movement timestamp index.
3. `20261119_0003_movement_idempotency` creates idempotency key records for movement writes.
4. `20261119_0004_import_batch_idempotency` stores CSV import retry results.

Schema changes are applied with `alembic upgrade head`. `alembic check` was run against PostgreSQL and detected no differences between model metadata and the migrated schema. `Base.metadata.create_all()` is not used as a deployment or migration strategy.

## Seed mapping and reconciliation

The initial demonstration snapshot is retained as explicit fixture constants in `backend/app/db/seed_data.py`; the frontend no longer embeds a second in-memory copy. The seed contains 10 products, 3 stores, 30 balances, 6 activity examples, and 5 linked historical movement records. Prices become decimal amounts, SKUs and store identifiers become unique keys, each balance holds its own reorder level, and fixture Asia/Kolkata timestamps are converted to UTC.

The frontend fixtures are a current stock snapshot plus a few sample activity rows, not a complete movement ledger. The seed therefore preserves the snapshot quantities and representative history, but historical movements do not fully explain every balance from an opening quantity of zero. Future reconciliation should begin from an agreed opening-balance date and a complete movement source.

On the tested clean database the totals were:

| Store | Units |
|---|---:|
| Central Store | 193 |
| City Centre | 89 |
| Riverside Outlet | 114 |
| **Total** | **396** |

Seed reruns add missing fixture rows only; they do not reset existing quantities or overwrite existing products/stores. Stable `seed_key` values prevent duplicate activity and movement fixtures.

## Deliberate boundaries

The relational model does not yet include users, permissions, tenants, suppliers, purchase orders, barcode data, tax/currency metadata, or inventory reservations. Product price uses two decimal places; currency remains unspecified. Authentication and authorization are not implemented.
