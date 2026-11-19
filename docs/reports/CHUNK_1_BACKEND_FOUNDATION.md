# StockFlow Chunk 1 — Backend Foundation + Core Inventory Operations

**Status:** Implemented and locally verified against PostgreSQL 18.6. No external deployment or paid resources were used.

## 1. Summary of implemented work

- Added a layered FastAPI backend under `backend/` using Python 3.15.2, Pydantic 2, SQLAlchemy 2.x, Psycopg 3, PostgreSQL 18, Alembic, and Pytest.
- Separated API routes, Pydantic schemas, business services, SQLAlchemy repositories, ORM models, and database/configuration code.
- Added normalized product, store, inventory balance, stock movement, and activity history tables with constraints, indexes, and UTC-aware timestamps.
- Added versioned Alembic migrations and a rerunnable, non-resetting seed command mapped from `frontend/src/app/data.ts`.
- Added product/store CRUD, inventory query/filter/detail, movement/activity history, health, and transactional sale/restock/adjustment APIs.
- Added automated PostgreSQL-backed tests that refuse non-loopback databases or databases without a `_test` suffix.
- Kept all frontend source and behavior unchanged. No frontend API integration was started.
- Added backend architecture, database, API contract, setup, and verification documentation.

## 2. Final backend directory tree

```text
backend/
├── .env.example
├── README.md
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 20261119_0001_initial_schema.py
│       └── 20261119_0002_history_query_indexes.py
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/routes/
│   │   ├── products.py
│   │   ├── stores.py
│   │   └── inventory.py
│   ├── core/config.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── seed_data.py
│   ├── repositories/
│   │   ├── products.py
│   │   ├── stores.py
│   │   ├── inventory.py
│   │   └── history.py
│   ├── models/
│   │   ├── product.py
│   │   ├── store.py
│   │   ├── inventory.py
│   │   ├── movement.py
│   │   └── activity.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── product.py
│   │   ├── store.py
│   │   └── inventory.py
│   └── services/
│       ├── errors.py
│       ├── products.py
│       ├── stores.py
│       ├── inventory.py
│       └── movements.py
├── tests/
│   ├── conftest.py
│   ├── helpers.py
│   ├── test_products_stores_inventory.py
│   └── test_inventory_movements.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── requirements-lock.txt
```

`.venv/`, `.env`, caches, and bytecode are local ignored files and are not part of the backend source tree.

## 3. Database schema and relationships

- **products:** integer PK, unique indexed SKU, name/category indexes, `NUMERIC(12,2)` price, active flag, UTC-aware creation/update times, nonnegative-price constraint.
- **stores:** integer PK, unique indexed code and name, location, active flag, UTC-aware times.
- **inventory_balances:** integer PK, product/store FKs, unique product/store pair, integer quantity and reorder level, both constrained nonnegative, UTC-aware `updated_at`.
- **stock_movements:** integer PK, composite FK to an existing product/store balance, type, signed delta, before/after quantities, note, UTC-aware creation time, and seed key. Constraints enforce nonnegative before/after, nonzero delta, `after = before + delta`, recognized movement types, and sign/type consistency.
- **activity_history:** integer PK, optional unique movement FK and optional product/store FKs, event type, display snapshots, signed quantity delta, batch marker, stable seed key, and UTC-aware occurrence time. The CSV import fixture is a batch activity without one product/store/movement.

See `docs/architecture/STOCKFLOW_DATABASE_DESIGN.md` for the ER diagram and index/constraint detail.

## 4. Migration details

1. `20261119_0001_initial_schema` creates the five tables, primary/foreign keys, uniqueness and quantity checks, and baseline indexes.
2. `20261119_0002_history_query_indexes` adds store filtering and unfiltered movement-history indexes.

Actual commands run against the isolated local `stockflow` database:

```text
alembic upgrade head                         PASS; both revisions applied
alembic check                                PASS; No new upgrade operations detected
```

Migrations are explicit. The app does not call `create_all()` on startup.

## 5. API endpoint inventory and examples

Base: `/api/v1`. FastAPI serves `/openapi.json` and `/docs`; `/health` runs a database `SELECT 1`.

| Method | Endpoint | Notes |
|---|---|---|
| GET, POST | `/api/v1/products` | Paginated search/category list; create product and zero balances for active stores. |
| GET, PATCH, DELETE | `/api/v1/products/{product_id}` | Retrieve, edit, or soft-deactivate. |
| GET, POST | `/api/v1/stores` | Paginated list; create store and zero balances for active products. |
| GET, PATCH, DELETE | `/api/v1/stores/{store_id}` | Retrieve, edit, or soft-deactivate. |
| GET | `/api/v1/inventory` | Filters: `store_id`, `product_id`, `sku`, `search`, `status`; pagination. |
| GET | `/api/v1/inventory/{product_id}/{store_id}` | Retrieve one product/store balance. |
| POST | `/api/v1/inventory/movements/sale` | Requires positive integer `quantity`. |
| POST | `/api/v1/inventory/movements/restock` | Requires positive integer `quantity`. |
| POST | `/api/v1/inventory/movements/adjustment` | Requires nonzero signed `quantity_delta`. |
| GET | `/api/v1/inventory/movements` | Paginated/filterable movement history. |
| GET | `/api/v1/inventory/activities` | Paginated/filterable activity history. |

Example sale body:

```json
{"product_id": 1, "store_id": 1, "quantity": 2, "note": "POS sale"}
```

Successful movements return 201 and record signed `quantity_delta`, `quantity_before`, and `quantity_after`. Missing entities return 404; insufficient stock and uniqueness conflicts return 409; invalid input returns structured 422 errors. Full examples and response conventions are in `docs/architecture/STOCKFLOW_API_CONTRACT.md`.

## 6. Sale transaction and concurrency strategy

Sale, restock, and adjustment use a single `Session.begin()` boundary. The service checks active product/store existence, obtains the matching balance with PostgreSQL `SELECT ... FOR UPDATE`, computes and validates the result, updates the balance, inserts a stock movement, and inserts linked activity history before commit. Any domain or database error rolls back every write. A database check also rejects negative balance/movement quantities.

The tested concurrency case starts two independent sessions attempting to sell 15 units from a 24-unit balance. One commits and the other observes the locked, updated row and is rejected; final balance is 9 with one new movement. No idempotency key currently exists, so automatic client retries after an ambiguous response could duplicate a successful operation.

## 7. Seed data reconciliation

Seed source: existing `frontend/src/app/data.ts`. The command was run twice; both runs reported the same result, with no duplicate seed records and no quantity reset:

```text
Seed complete: 10 products, 3 stores, 30 balances, 396 units,
store totals={'Central Store': 193, 'City Centre': 89, 'Riverside Outlet': 114}
```

The five non-import activity fixtures are linked to historical movement rows. The CSV batch activity remains a summary event. Fixture timestamps are converted from Asia/Kolkata to UTC.

## 8. Test cases and actual results

Executed on the isolated loopback `stockflow_test` database using Python 3.15.2 and PostgreSQL 18.6:

```text
python -m pytest -q
......................                                                   [100%]
22 passed in 5.70s
```

Coverage includes product/store CRUD, duplicate SKU, new product balances, store balance provisioning, fixture counts/totals and seed rerun, inventory filtering/search/detail, no stock changes on product edit, sale success/insufficient/invalid quantities/missing entities, restock, positive and negative adjustments, negative-stock prevention, transaction rollback after an injected DB error, movement/activity persistence, concurrent oversell protection, health, structured unknown-route errors, and OpenAPI.

The initial test run enforced a loopback database host and `_test` name and used a temporary PostgreSQL cluster on port 55432. A follow-up remediation strengthened the guard to resolve effective process/`.env` configuration and reject matching database identities before app/database initialization. See `docs/reports/CHUNK_1_REMEDIATION_REPORT.md` for current verification.

## 9. Commands to run the backend

From repository root:

```powershell
Set-Location backend
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
# Edit .env with the local development DATABASE_URL.
alembic upgrade head
python -m app.db.seed_data
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`; health: `http://127.0.0.1:8000/health`.

## 10. Environment configuration required

`backend/.env.example` contains placeholders only. Required `DATABASE_URL` uses SQLAlchemy Psycopg format, for example:

```text
postgresql+psycopg://stockflow:<local-password>@127.0.0.1:5432/stockflow
```

Optional `API_V1_PREFIX` defaults to `/api/v1`; optional `APP_NAME` defaults to `StockFlow API`. For tests, provide a distinct `TEST_DATABASE_URL` to a disposable loopback PostgreSQL database named with `_test`, and a development `DATABASE_URL` via process environment or `.env`. The test guard validates effective URL identities before it initializes the test application.

Python runtime tested: **3.15.2**. PostgreSQL server tested: **18.6**. Direct dependencies are pinned in project files: FastAPI 0.165.0; Pydantic 2.14.4; Pydantic Settings 2.16.3; SQLAlchemy 2.1.9; Psycopg 3.3.9 and psycopg-binary 3.3.9; Alembic 1.20.1; Uvicorn 0.54.0; python-dotenv 1.2.4; Pytest 9.2.0; httpx2 2.16.2. `requirements-lock.txt` pins the tested transitive environment too.

## 11. Known limitations and incomplete work

- Frontend is not connected to these endpoints; no full-stack integration was started.
- Authentication, authorization, tenant/store access control, audit actor identity, CORS policy, rate limiting, and production secret management are not implemented.
- No idempotency token for sale/restock/adjustment requests; retry handling needs a design before network integration.
- Frontend fixtures provide a stock snapshot and six sample activities, not a complete movement ledger. Seeded balances are authoritative opening snapshot values; five linked historical movement rows do not reconstruct every balance from zero.
- No import processing/commit API, replenishment queue API, suppliers, purchase orders, reservations, or user management. Existing frontend import behavior remains a demo.
- Product/store DELETE is soft deactivation. Historical records are retained and identifiers remain reserved.
- Currency is unspecified by the frontend; `NUMERIC(12,2)` stores the displayed price value but does not assert a currency.
- No production deployment, TLS termination, backups, monitoring, or operational recovery plan was created.
- Replenishment threshold semantics are implemented as out-of-stock = zero, below-reorder = positive quantity at or below reorder level, healthy = greater than reorder level. Confirm this rule with product owners before frontend integration.
- Added products provision zero balances using `default_reorder_level` (default 0); newly added stores provision zero balances using each product's existing threshold or zero. These are documented implementation decisions.

## 12. Learning-domain mapping

This independent academic project is inspired by and extends concepts covered in the Walmart Global Tech Advanced Software Engineering Job Simulation. StockFlow was not developed for Walmart and is not an official Forage deliverable.

- **Advanced Data Structures — not meaningfully demonstrated in Chunk 1.** The implementation uses ordinary relational indexes, ORM collections, and pagination. These are appropriate choices but are not evidence of advanced data-structure work; retain this domain as a possible later learning objective.
- **Software Architecture — implemented.** FastAPI routes, Pydantic schemas, services, repositories, ORM models, configuration, and Alembic migrations separate HTTP, validation, business operations, and persistence responsibilities. Inventory mutations have an explicit transactional service boundary.
- **Relational Database Design — implemented.** Normalized products, stores, balances, movements, and activity history use primary/foreign keys, a unique product/store balance pair, a composite movement-to-balance key, checks, and query indexes.
- **Data Munging — demonstrated in a bounded form.** `backend/app/db/seed_data.py` maps flat frontend fixtures into normalized records, parses prices as decimals, converts Asia/Kolkata fixture times to UTC, and uses stable keys and missing-row insertion. A general CSV ingestion/validation pipeline is not implemented and remains future work.

## Live API verification output

The local Uvicorn process started successfully. Actual requests reported:

```text
GET /health                                      200: {"status":"ok","database":"connected"}
GET /api/v1/products?search=Wireless%20Mouse     200: 1 result
GET /api/v1/stores                               200: 3 results
POST .../movements/sale                          201: delta -2
POST .../movements/restock                       201: delta +1
POST .../movements/adjustment                    201: delta +1
GET /api/v1/inventory/1/1                        200: quantity restored to 24
GET /openapi.json                                200: 12 paths including all implemented endpoints
PostgreSQL connection session timezone           UTC
```

The live movement checks ran against the disposable, isolated local cluster and returned the seeded test balance to its prior value.

## 13. Remediation follow-up

The targeted audit findings H-1, M-1, and M-2 were addressed after the original 22-test run. The current test suite has 33 passing tests; it includes fail-closed destructive database target tests, a PostgreSQL-observed row-lock wait test, and a regression proving movement responses do not rely on post-commit refresh. The remediation report records exact commands and verification results: `docs/reports/CHUNK_1_REMEDIATION_REPORT.md`.
