# StockFlow

**Inventory, in motion.** StockFlow is a multi-store inventory workspace for maintaining a product catalogue, understanding store-level stock health, recording stock movements, and preparing replenishment from simple reorder rules. Its React frontend is connected to a FastAPI service backed by PostgreSQL.

The repository contains a working academic MVP and local demonstration data. It is not an authenticated or production-hardened inventory service.

## Table of Contents

1. [Project Header and Introduction](#1-project-header-and-introduction)
2. [Project Overview](#2-project-overview)
3. [Problem Statement and Objectives](#3-problem-statement-and-objectives)
4. [Key Features](#4-key-features)
5. [Application Screenshots](#5-application-screenshots)
6. [Technology Stack](#6-technology-stack)
7. [System Architecture](#7-system-architecture)
8. [Database Architecture and Schema](#8-database-architecture-and-schema)
9. [API Architecture and Important Endpoints](#9-api-architecture-and-important-endpoints)
10. [Core Business Logic](#10-core-business-logic)
11. [Data Structures and Algorithms](#11-data-structures-and-algorithms)
12. [Inventory Movement and Transaction Safety](#12-inventory-movement-and-transaction-safety)
13. [CSV Import and Validation Workflow](#13-csv-import-and-validation-workflow)
14. [Idempotency and Error Handling](#14-idempotency-and-error-handling)
15. [Project Directory Structure](#15-project-directory-structure)
16. [Local Development Setup](#16-local-development-setup)
17. [Environment Variables](#17-environment-variables)
18. [Database Migration and Seed Instructions](#18-database-migration-and-seed-instructions)
19. [Running Frontend and Backend](#19-running-frontend-and-backend)
20. [Testing and Verification](#20-testing-and-verification)
21. [Deployment Architecture](#21-deployment-architecture)
22. [Known Limitations and Security Considerations](#22-known-limitations-and-security-considerations)
23. [Future Scope](#23-future-scope)
24. [Related Documentation](#24-related-documentation)
25. [Acknowledgements and Project Information](#25-acknowledgements-and-project-information)

## 1. Project Header and Introduction

The app brings catalogue management and store-specific stock into one interface. Operators can review network health, find products, filter balances by store, record sales/restocks/adjustments, inspect activity, and preview or commit a CSV inventory snapshot.

## 2. Project Overview

StockFlow separates **product definitions** from **inventory balances**. A product can have a different quantity and reorder level at each store. The app's five primary areas are:

| Area | Purpose |
|---|---|
| Overview | Summarize total units and stock health, surface inventory alerts, and show recent activity. |
| Catalogue | Search, sort, filter, create, update, and deactivate product definitions; view per-store stock coverage. |
| Inventory | Filter store-level balances, record contextual stock movements, and inspect movement/activity history. |
| Replenishment | Prioritize out-of-stock and below-reorder balances and present a deterministic suggested quantity. |
| Data Import | Upload a CSV snapshot, preview backend validation, review accepted/rejected rows, and commit eligible imports. |

The browser routes are `/overview`, `/catalogue`, `/inventory`, `/replenishment`, and `/import`; `/` redirects to Overview.

## 3. Problem Statement and Objectives

For a small retailer with multiple locations, one product-level quantity can hide a shortage at a particular store. StockFlow's current objectives are to:

- Keep catalogue attributes distinct from store stock.
- Show stock health at the product/store level.
- Make stock-changing actions explicit and traceable.
- Give operators a transparent, rule-based replenishment queue.
- Validate inventory snapshots before applying them to balances.

The replenishment target is intentionally a simple business rule, not a demand forecast or an AI recommendation.

## 4. Key Features

- Database-backed dashboard summary and recent activity.
- Product and store lifecycle endpoints, including initial zero-balance provisioning for newly created products/stores.
- Per-store inventory filters, stock-status labels, and balance thresholds.
- Sale, restock, and signed adjustment operations with stock checks and movement history.
- Activity history with product/store references and CSV batch records.
- Store-filtered replenishment queue with out-of-stock items prioritized.
- CSV preview and all-or-nothing snapshot commit with row-level validation feedback.
- Persisted idempotency results for movement writes and CSV commits.
- Three selectable visual themes: Ocean, Forest, and Slate.

## 5. Application Screenshots

These are genuine browser captures of the local frontend connected to a separate, temporary PostgreSQL database seeded with demonstration records. The CSV images show a real backend preview and review containing one accepted row and one rejected row; no import was committed. They do not represent a public deployment.

| Screen | Evidence |
|---|---|
| Overview Dashboard | ![StockFlow Overview dashboard: total stock units, store-level health, alerts, and recent activity](docs/assets/screenshots/overview.png) |
| Product Catalogue | ![StockFlow Catalogue with search, category filters, product definitions, and store coverage](docs/assets/screenshots/catalogue.png) |
| Inventory — Stock Balances | ![StockFlow Inventory balances with store context, stock status, reorder thresholds, and actions](docs/assets/screenshots/inventory.png) |
| Inventory — Movement History | ![StockFlow movement history with event type, store, quantity change, and notes](docs/assets/screenshots/inventory-history.png) |
| Replenishment | ![StockFlow replenishment queue separating out-of-stock and below-reorder items](docs/assets/screenshots/replenishment.png) |
| Data Import — Validate & Clean | ![StockFlow CSV validation preview showing accepted and rejected rows from backend parsing](docs/assets/screenshots/data-import.png) |
| Data Import — Review | ![StockFlow CSV review stage showing its all-or-nothing policy and blocked commit for a rejected row](docs/assets/screenshots/data-import-review.png) |

The initial upload screen is also available as [data-import-upload.png](docs/assets/screenshots/data-import-upload.png).

## 6. Technology Stack

### Frontend

| Technology | Use |
|---|---|
| React 19, React Router 7 | UI and client-side routes |
| TypeScript | Application types |
| Vite 8 | Development server and production build |
| Tailwind CSS 4 | Utility styling through the Vite plugin |
| Lucide React | Interface icons |

The frontend calls the API through a shared client and app store; it does not define a separate persistent data store.

### Backend

| Technology | Use |
|---|---|
| Python `>=3.13,<3.16` | Backend runtime requirement |
| FastAPI 0.165, Pydantic 2.14 | HTTP routes and request/response validation |
| SQLAlchemy 2.1, Psycopg 3.3 | ORM and PostgreSQL driver |
| Alembic 1.20 | Versioned schema migrations |
| Uvicorn 0.54 | ASGI server |

Pinned backend runtime and test dependencies are listed in [`backend/requirements-lock.txt`](backend/requirements-lock.txt); project metadata is in [`backend/pyproject.toml`](backend/pyproject.toml).

### Database

PostgreSQL 18 is the database version used for local verification. The schema stores products, stores, store-level balances, movements, activity, and idempotency/import records.

### Development Tools

| Tool | Version/configuration |
|---|---|
| Node.js | 22, recorded in `.mise.toml` |
| pnpm | 10.34.3 through Corepack |
| Python | 3.13–3.15 |
| pytest | 9.2, backend tests |
| oxfmt | Frontend formatter |

There is no frontend lint or frontend test script in the current package manifest. Frontend verification uses the declared TypeScript check and production build scripts.

### Deployment Infrastructure

Render and Vercel configuration files are present. Their presence is **not** evidence that either service is currently deployed; no public service URL or successful public deployment has been verified.

## 7. System Architecture

```mermaid
flowchart LR
  Browser[React application in browser] -->|HTTPS JSON and CSV requests| API[FastAPI on Uvicorn]
  API --> Routes[Versioned API routes]
  Routes --> Schemas[Pydantic schemas]
  Routes --> Services[Business services]
  Services --> Repositories[SQLAlchemy repositories]
  Repositories --> PostgreSQL[(PostgreSQL)]
  Alembic[Alembic migrations] --> PostgreSQL
  Seed[Explicit demo seed command] --> PostgreSQL
  Vercel[Vercel frontend configuration] -. serves built frontend .-> Browser
  Render[Render API configuration] -. hosts API when deployed .-> API
```

In the frontend, `frontend/src/app/api.ts` owns HTTP requests and `frontend/src/app/store.tsx` coordinates shared state and refreshes. The backend separates route handlers, schemas, services, repositories, models, and database setup. Database tables are created by Alembic migrations, not implicitly at application startup.

## 8. Database Architecture and Schema

The core relationship is one balance per product/store pair. A balance stores the current quantity and reorder level; movements describe sale/restock/adjustment deltas, while activity history provides a displayable event feed and also records CSV imports.

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
    int movement_id FK
  }
  IMPORT_BATCHES {
    string idempotency_key PK
    string request_hash
    json result_payload
    timestamptz created_at
  }
```

| Table | Responsibility and notable constraints |
|---|---|
| `products` | Catalogue attributes; unique SKU, nonnegative price, soft-deactivation flag. |
| `stores` | Store code/name/location; unique code and name, soft-deactivation flag. |
| `inventory_balances` | Current stock and reorder level; unique `(product_id, store_id)`, nonnegative values. |
| `stock_movements` | Sale/restock/adjustment ledger with before/after quantities and signed delta; linked to a valid balance. |
| `activity_history` | Store/product-scoped event snapshots, optionally linked to a movement; CSV imports are batch activity rather than movement rows. |
| `idempotency_records` | Movement request fingerprint and original movement reference. |
| `import_batches` | CSV request fingerprint and committed result for safe retries. |

Prices use `NUMERIC(12,2)`; application/database timestamps are timezone-aware and stored in UTC. Four Alembic revisions create the initial schema, query indexes, movement idempotency, and import idempotency. See the [database design](docs/architecture/STOCKFLOW_DATABASE_DESIGN.md) for indexes and migration details.

## 9. API Architecture and Important Endpoints

The default API prefix is `/api/v1`. Interactive OpenAPI documentation is available at `/docs` when the backend is running; `/openapi.json` returns the schema.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Database connectivity check; returns 503 when the database is unavailable. |
| `GET` | `/api/v1/dashboard/summary` | Aggregate units, active entities, stock-health counts, and recent activity. |
| `GET`, `POST` | `/api/v1/products` | List/search/filter products and create a product. |
| `GET` | `/api/v1/products/lookup/{sku}` | Find an active product by normalized SKU. |
| `GET`, `PATCH`, `DELETE` | `/api/v1/products/{product_id}` | Retrieve, update, or soft-deactivate a product. |
| `GET`, `POST` | `/api/v1/stores` | List or create stores. |
| `GET`, `PATCH`, `DELETE` | `/api/v1/stores/{store_id}` | Retrieve, update, or soft-deactivate a store. |
| `GET` | `/api/v1/inventory` | Paginated balances; filter by store, product, SKU, search, or status. |
| `GET` | `/api/v1/inventory/{product_id}/{store_id}` | Retrieve one product/store balance. |
| `POST` | `/api/v1/inventory/movements/sale` | Record a sale. |
| `POST` | `/api/v1/inventory/movements/restock` | Record a restock. |
| `POST` | `/api/v1/inventory/movements/adjustment` | Record a signed adjustment. |
| `GET` | `/api/v1/inventory/movements` | List movement records with optional product/store filters. |
| `GET` | `/api/v1/inventory/activities` | List activity history with optional product/store filters. |
| `GET` | `/api/v1/inventory/replenishment` | Return the prioritized queue; optional store and urgency filters. |
| `POST` | `/api/v1/inventory/import/preview` | Parse and validate a raw `text/csv` request body without writes. |
| `POST` | `/api/v1/inventory/import/commit` | Atomically apply an eligible CSV snapshot. |

List routes use `skip`/`limit` pagination (defaults 0/50; maximum limit 200). Mutation and error details are documented in the [API contract](docs/architecture/STOCKFLOW_API_CONTRACT.md).

## 10. Core Business Logic

- **Stock health:** quantity zero is out of stock; a positive quantity at or below reorder level is below reorder; otherwise it is healthy.
- **Product creation:** creates a zero-quantity balance for each active store, initialized with the supplied default reorder level.
- **Store creation:** creates a zero-quantity balance for each active product and copies that product's current reorder level when available.
- **Lifecycle:** deleting a product or store sets it inactive rather than removing referenced history.
- **Movements:** sales require a positive requested quantity and subtract it; restocks add a positive quantity; adjustments accept a nonzero signed delta. Negative resulting stock is rejected.
- **Replenishment:** only active balances at or below their reorder level enter the queue; out-of-stock and low-stock classes are surfaced separately.
- **CSV imports:** quantities are absolute snapshots, not movement deltas.

## 11. Data Structures and Algorithms

| Operation | Implementation |
|---|---|
| SKU resolution | Normalized in-memory dictionary index: O(n) to build over n products and average O(1) lookup. Duplicate normalized SKUs are rejected rather than selected ambiguously. |
| CSV row processing | `csv.DictReader`, normalized header keys, a set of seen product/store pairs, and a dictionary keyed by product/store balance. This enables row-numbered validation and duplicate detection. |
| Replenishment ordering | Python `heapq`; items are ordered by largest reorder deficit, then higher reorder level, normalized SKU, store code, and stable identifiers. The current implementation is O(n log n) for n candidate balances. |
| Stock updates | PostgreSQL row-level locks serialize concurrent changes to the same balance. Each successful operation commits its balance and history changes together. |

## 12. Inventory Movement and Transaction Safety

A movement request loads the active product/store pair, locks its balance with `SELECT ... FOR UPDATE`, validates the resulting stock, updates the balance, inserts a `stock_movements` row, and writes the corresponding `activity_history` row in one transaction. If validation or persistence fails, the transaction rolls back. Database constraints also guard nonnegative stock and movement arithmetic.

The movement ledger records sale, restock, and adjustment events. CSV snapshot commits write store/product-scoped batch activity rows, not fabricated movement rows. The seed contains representative historical events; it is not a complete ledger explaining every seeded balance.

## 13. CSV Import and Validation Workflow

The four UI stages are **Upload → Validate & Clean → Review → Results**. The browser uploads the raw file to the backend preview endpoint; preview does not write inventory. “Clean” means normalize headers/trim values and resolve references—it does not guess or silently repair unknown products/stores.

| Rule | Behavior |
|---|---|
| Encoding and size | UTF-8 (UTF-8 BOM accepted), maximum 5 MiB and 5,000 data rows. |
| Required columns | `SKU`, `Store` (name or code), and `Quantity`; `Reorder Level` is optional. Header spacing/case is normalized; `Store Code` and `Store Name` are accepted aliases. |
| Values | Active product/store references; quantity and optional reorder level must be nonnegative whole numbers. |
| Row errors | Unknown references, duplicate SKU/store pairs, missing/invalid values, or a balance pair that cannot be resolved are returned with source row numbers. |
| Commit policy | All-or-nothing. Any rejected row or no accepted rows blocks the whole commit. Accepted quantities replace the current snapshot; an optional reorder level also updates the balance. |
| History | A successful commit records one CSV activity entry per imported product/store row in the same transaction. |

## 14. Idempotency and Error Handling

Movement writes and CSV commits require an `Idempotency-Key` header (1–128 characters). The backend stores a request fingerprint and result in the same transaction as the mutation. Repeating an identical operation with the same key returns the original result; reusing the key for a different payload returns a conflict instead of applying another mutation.

The API uses a consistent JSON error envelope. Typical responses are 422 for schema validation, 404 for missing records, 409 for domain conflicts or insufficient stock, and 503 for a database health-check failure. Unexpected server errors are logged and returned as a generic 500 response. CORS configuration is not authentication.

## 15. Project Directory Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route handlers
│   │   ├── core/             # Settings and configuration
│   │   ├── db/               # Sessions and explicit seed command
│   │   ├── models/           # SQLAlchemy tables
│   │   ├── repositories/     # Persistence queries
│   │   ├── schemas/          # Pydantic request/response models
│   │   └── services/         # Business rules and transactions
│   ├── alembic/versions/     # Versioned database migrations
│   ├── tests/                # PostgreSQL-backed API and service tests
│   ├── pyproject.toml
│   └── requirements-lock.txt
├── frontend/
│   ├── src/app/              # Routes, API client, app state, screens
│   ├── src/index.css         # Tailwind setup and global styles
│   ├── package.json
│   └── pnpm-lock.yaml
├── docs/
│   ├── architecture/
│   ├── assets/screenshots/
│   ├── audits/
│   ├── engineering/
│   └── reports/
├── .figma/                   # Figma Make tooling/configuration
├── render.yaml               # Render backend service configuration
└── vercel.json               # Vercel frontend build and SPA rewrite
```

## 16. Local Development Setup

### Prerequisites

- Git.
- Node.js 22 and Corepack (pnpm 10.34.3 is pinned in `.mise.toml`).
- Python 3.13, 3.14, or 3.15.
- PostgreSQL (18 is the locally verified version).

Clone the repository, then install the frontend dependencies from the frontend directory:

```powershell
git clone https://github.com/ayanshusaxena/StockFlow.git
Set-Location StockFlow\frontend
corepack pnpm install --frozen-lockfile
Copy-Item .env.example .env
```

Create a backend virtual environment and install the pinned dependencies:

```powershell
Set-Location ..\backend
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Configure PostgreSQL and the backend environment before running migrations. Keep database credentials local; do not commit `.env` files.

## 17. Environment Variables

| Variable | Required? | Default / example | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Yes for backend | `postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/stockflow` | SQLAlchemy PostgreSQL connection. Use a private local value. |
| `API_V1_PREFIX` | No | `/api/v1` | Versioned API route prefix. |
| `APP_NAME` | No | `StockFlow API` | FastAPI/OpenAPI application title. |
| `CORS_ORIGINS` | No | `http://localhost:8443,http://127.0.0.1:8443` | Comma-separated browser origins allowed by CORS. This is not access control. |
| `VITE_API_BASE_URL` | No | `http://127.0.0.1:8000/api/v1` | Frontend API base URL; set this at frontend build time when the API is elsewhere. |
| `TEST_DATABASE_URL` | Required for backend tests | A separate loopback PostgreSQL database ending in `_test` | Disposable test target; it must not identify the development database. |

Variable names/defaults are defined in [`backend/.env.example`](backend/.env.example), [`frontend/.env.example`](frontend/.env.example), and backend settings. The backend test guard validates both database identities before test setup; tests truncate only the validated test database.

## 18. Database Migration and Seed Instructions

Create two local databases (development and test) and configure their URLs in `backend/.env`. Example SQL (choose and protect your own password):

```sql
CREATE ROLE stockflow LOGIN PASSWORD 'replace-with-a-local-password';
CREATE DATABASE stockflow OWNER stockflow;
CREATE DATABASE stockflow_test OWNER stockflow;
```

From `backend/`, apply the schema and optionally load the demonstration fixtures:

```powershell
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
python -m app.db.seed_data
```

The explicit seed is intended for a local/demo database. On an empty database it creates 10 products, 3 stores, 30 balances, 6 sample activity events, and 396 units. It inserts missing fixture records without resetting existing quantities. Do not run a demo seed against operational data unless that behavior has been reviewed.

## 19. Running Frontend and Backend

Run the API from `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Run the Vite app in a second terminal from `frontend/`:

```powershell
corepack pnpm run dev
```

Vite uses port 8443 by default. The API listens on port 8000 by default; local API documentation is at `http://127.0.0.1:8000/docs` and its database health check is at `http://127.0.0.1:8000/health`. The frontend defaults to the local API URL above; configure `VITE_API_BASE_URL` if it differs.

## 20. Testing and Verification

Frontend checks, from `frontend/`:

```powershell
corepack pnpm run typecheck
corepack pnpm run build
corepack pnpm run format
```

There is no declared frontend lint or unit-test script. Backend tests, from `backend/`, require both `DATABASE_URL` and `TEST_DATABASE_URL` to point to distinct loopback PostgreSQL databases; the latter must end in `_test`:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/stockflow"
$env:TEST_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/stockflow_test"
python -m pytest -q
```

For this README update, the frontend TypeScript check and production build passed, and the backend suite passed **53 tests** against a separate disposable PostgreSQL test database. The browser screenshots above were captured from the local API-backed app; the CSV preview and review were exercised without committing the sample file.

## 21. Deployment Architecture

The repository is configured for a Vercel frontend and a Render API:

| Service | Repository configuration | Required setup |
|---|---|---|
| Vercel | `vercel.json` builds `frontend/`, publishes `frontend/dist`, and rewrites app routes to `index.html`. | Set `VITE_API_BASE_URL` to the actual API URL before building. |
| Render | `render.yaml` defines a Python web service rooted at `backend/`, installs `requirements-lock.txt`, starts Uvicorn on `$PORT`, and checks `/health`. | Supply `DATABASE_URL` and `CORS_ORIGINS` privately; configure the frontend origin. |

```mermaid
flowchart LR
  User[User browser] --> Vercel[Vercel static frontend]
  Vercel -->|VITE_API_BASE_URL| Render[Render FastAPI service]
  Render --> PostgreSQL[(Configured PostgreSQL database)]
```

No live Render or Vercel URLs are verified in this repository. Follow the [deployment guide](docs/engineering/STOCKFLOW_DEPLOYMENT.md) for configuration and public smoke-test steps; do not treat these config files as proof of deployment or operational readiness.

## 22. Known Limitations and Security Considerations

- Authentication, authorization, roles, and tenant isolation are not implemented. Anyone who can reach the API can call its endpoints; do not expose it as a secured multi-user service.
- CORS only controls browser origins and is not an authentication mechanism.
- Production secret management, rate limiting, backups, monitoring/observability, and deployment hardening are not implemented.
- Seeded activity contains fixed example timestamps from June 2025. These are sample records, not current operational or real-time activity.
- Replenishment is a transparent reorder-level heuristic; there is no demand forecasting, supplier ordering, or purchase-order workflow.
- Currency is not explicitly modeled, although product prices are stored to two decimal places.
- The database does not include users, suppliers, barcodes, reservations, or purchase orders.
- The movement history is representative seed data, not a complete historical ledger that explains every seeded balance.
- Import preview is not a reservation: balances may change before commit. Commit re-locks balances and applies the CSV as an absolute snapshot.
- Public deployment, external integrations, and production-scale operations have not been verified.

## 23. Future Scope

Potential follow-up work, subject to product and security decisions:

- Define authentication, authorization, tenancy, and store-level access controls.
- Add supplier and purchase-order workflows.
- Define a currency policy and any needed product metadata such as barcodes.
- Decide whether replenishment should remain rule-based or use approved demand inputs.
- Add production operations controls (secrets, backups, monitoring, rate limits, and deployment verification).
- Add browser-level regression tests and public deployment smoke checks.

These are not implemented features.

## 24. Related Documentation

- [Backend setup and test-safety instructions](backend/README.md)
- [API contract](docs/architecture/STOCKFLOW_API_CONTRACT.md)
- [Database design and migration history](docs/architecture/STOCKFLOW_DATABASE_DESIGN.md)
- [Backend runtime and transaction architecture](docs/architecture/STOCKFLOW_BACKEND_ARCHITECTURE.md)
- [Business logic, replenishment, and CSV behavior](docs/reports/CHUNK_2_BUSINESS_LOGIC_DATA_MUNGING.md)
- [Render and Vercel deployment preparation](docs/engineering/STOCKFLOW_DEPLOYMENT.md)
- [Integrated implementation report](docs/reports/MASTER_EXECUTION_FINAL_REPORT.md)

**Documentation note:** Some phase reports and the older [codebase handover](docs/engineering/STOCKFLOW_CODEBASE_HANDOVER.md) describe the pre-integration frontend and say API integration, replenishment, or CSV import is future work. The current source and the API/database documents linked above reflect the integrated implementation; treat older phase-specific reports as historical evidence, not as the current contract.

## 25. Acknowledgements and Project Information

StockFlow is an academic software-engineering project. It uses the open-source libraries listed above; no external organization endorsement or affiliation is implied. This repository provides implementation and local demo documentation, not a promise of hosted availability or production service levels.
