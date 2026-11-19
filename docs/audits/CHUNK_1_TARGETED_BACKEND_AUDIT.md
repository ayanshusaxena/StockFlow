# StockFlow Chunk 1 Targeted Backend Audit

**Audit date:** 2026-11-19  
**Original audit verdict:** CONDITIONAL PASS  
**Current verdict after remediation:** PASS (all three findings addressed and verified; see `docs/reports/CHUNK_1_REMEDIATION_REPORT.md`).  
**Acceptance recommendation:** Submit Chunk 1 for explicit review and acceptance. Do not begin Chunk 2 until that acceptance is given.

## 1. Executive verdict

The audit verified that the current movement service encloses balance mutation, movement insertion, and activity insertion in one SQLAlchemy transaction; the balance query requests a PostgreSQL row lock; the schema encodes the key quantity and relationship invariants; migrations match ORM metadata; seed insertion is transactional and non-resetting; and the existing test suite passes against a disposable PostgreSQL 18.6 database at READ COMMITTED isolation.

A **High** test-safety finding and two **Medium** findings were recorded in the original review. The remediation now resolves and validates the effective process/.env database URLs before initializing application modules, compares host addresses/port/database names, verifies PostgreSQL and loopback constraints, and has guard-specific tests. The concurrency test now pauses the first transaction while it holds the row lock and observes the second backend waiting in PostgreSQL. Movement response construction no longer performs a post-commit refresh. See finding-by-finding status below and the remediation report for test evidence.

The initial audit made documentation-only changes. The subsequent remediation changed backend test safety, the movement service, and focused tests; it did not change frontend code, migrations, or dependencies. No Chunk 2 work was started.

## 2. Scope and inspected files

Inspected the actual source and configuration, not only prior reports:

- Runtime/configuration: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/db/session.py`, `backend/app/db/base.py`, `backend/app/db/seed_data.py`.
- API and behavior: `backend/app/api/routes/{products,stores,inventory}.py`, `backend/app/schemas/{common,product,store,inventory}.py`, `backend/app/services/{products,stores,inventory,movements,errors}.py`, and repositories under `backend/app/repositories/`.
- Models and migrations: `backend/app/models/{product,store,inventory,movement,activity}.py`, `backend/alembic/env.py`, `backend/alembic/versions/20261119_0001_initial_schema.py`, and `20261119_0002_history_query_indexes.py`.
- Tests: `backend/tests/conftest.py`, `helpers.py`, `test_products_stores_inventory.py`, `test_inventory_movements.py`.
- Remediation tests: `backend/tests/database_safety.py` and `backend/tests/test_database_safety.py`.
- Dependency/setup files: `backend/pyproject.toml`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/requirements-lock.txt`, `backend/alembic.ini`, `backend/.env.example`, `backend/README.md`.
- Frontend fixture source: `frontend/src/app/data.ts`.
- Documentation and links: root `README.md`, docs architecture, engineering handover, audits and runtime evidence, and `docs/reports/CHUNK_1_BACKEND_FOUNDATION.md`.

## 3. Findings by severity

### Critical

None found in the inspected Chunk 1 scope.

### High

#### H-1 — Test bootstrap does not prove the destructive target is isolated

- **What was inspected:** environment loading and destructive test setup in `backend/tests/conftest.py` and `backend/app/core/config.py`; test database instructions in `backend/README.md`.
- **Observed:** `conftest.py` lines 13–28 validates that `TEST_DATABASE_URL` is loopback and its database name ends with `_test`, then compares it only with `os.environ.get("DATABASE_URL")`. At line 29 it overwrites `DATABASE_URL` with the test URL. `Settings` in `app/core/config.py` lines 8–12 separately supports `.env`. Since application settings are created after the overwrite/import at `conftest.py` lines 32–35, a `.env` URL is hidden from the comparison. The autouse fixture then truncates all five tables with `RESTART IDENTITY CASCADE` (`conftest.py` lines 39–46). URL aliases and connection options are not canonicalized to establish database identity either.
- **Why it matters:** an accidental/mistyped `TEST_DATABASE_URL` pointing at a valuable loopback database with an `_test` suffix can pass the guard and have its tables truncated. In particular, the current guard does not prove the user's configured development database differs from the destructive test target.
- **Severity:** High.
- **Action before Chunk 2:** Required. Resolve and compare the effective application URL before mutating environment, use explicit safeguards against development DB identities, and add a test proving `.env` and URL-alias cases are rejected. This audit did not patch the guard.
- **Remediation status:** Resolved in `backend/tests/database_safety.py` and `backend/tests/conftest.py`. Validation runs before changing `DATABASE_URL` or importing app/database modules. It honors process-over-dotenv precedence, requires explicit development and test URLs, rejects non-PostgreSQL/non-loopback/non-`_test` targets, resolves address aliases and compares port/database, and fails closed on unresolved hosts. Ten focused guard tests cover the requested scenarios. See remediation report.

### Medium

#### M-1 — Concurrent oversell test does not guarantee overlapping transactions

- **What was inspected:** `backend/tests/test_inventory_movements.py::test_postgres_row_lock_prevents_concurrent_oversell` and `backend/app/services/movements.py::record_movement`.
- **Observed:** the test uses a `Barrier(2)` at lines 146–152, then each worker opens its own `SessionLocal` and calls the service. This correctly uses two independent sessions, but the barrier is before the operation. One worker may complete its transaction before the other reads the balance. The assertion of one success/one rejection and final quantity 9 can pass under that sequential schedule.
- **Why it matters:** the result proves the expected final outcome for that run, but does not reliably prove the test would catch removal/breakage of `SELECT FOR UPDATE` under a real competing-read race.
- **Severity:** Medium.
- **Action before Chunk 2:** Required to claim deterministic concurrency coverage; add a controlled synchronization point after both transactions reach the contested operation (or another deterministic lock-contention check). The actual repository query does request `FOR UPDATE` (see Section 6).
- **Remediation status:** Resolved in `test_postgres_row_lock_prevents_concurrent_oversell`. The first worker pauses after acquiring the row lock; the second uses a separate session/backend PID, and the test observes its `pg_stat_activity.wait_event_type` become `Lock` before releasing the first transaction. It asserts one sale, one rejection, final quantity 9, and one added movement/activity. The no-lock path cannot satisfy the observed-wait assertion.

#### M-2 — Post-commit refresh failure can report failure after a committed movement

- **What was inspected:** `backend/app/services/movements.py::record_movement`, lines 34–83.
- **Observed:** the `with session.begin()` transaction commits before `session.refresh(movement)` at line 83; refresh remains inside the `try` whose SQLAlchemy errors are translated to `DatabaseOperationError`.
- **Why it matters:** if the post-commit refresh fails, the caller can receive an error even though stock and history have committed. A client retry can apply the operation again because movement APIs have no idempotency key (a limitation already stated in the foundation report).
- **Severity:** Medium (low-probability operational edge, with duplicate-effect potential on retries).
- **Action before Chunk 2:** Address or explicitly design the idempotency/retry boundary before clients automatically retry movement writes. No patch made.
- **Remediation status:** The post-commit refresh was removed; the flushed ORM row already contains its generated identifier and response fields, and the session uses `expire_on_commit=False`. A focused regression makes `Session.refresh` raise if invoked and verifies the movement still returns accurate persisted values. The separate idempotency/retry design remains a future integration requirement.

### Low

None found that blocks Chunk 1 acceptance independently of the findings above.

## 4. Verified claims and claims not independently established

**Verified during this audit:**

- The initial audit's 22-test result is historical; after remediation, 33 tests pass on PostgreSQL 18.6 at READ COMMITTED.
- Alembic metadata check reports no new upgrade operations.
- `app.main` imports when supplied a database URL.
- The locked dependency file can be resolved by pip's `--dry-run --ignore-installed` on this Python 3.15 environment; `pip check` is clean.
- The two migrations create the current model schema and the second revision adds the history query indexes.
- Test fixture row-count and totals assertions run in the suite; previous run output in the implementation report records the seed counts and totals. The test suite reseeds before each test and verifies seed reruns.
- The current temporary test database had PostgreSQL `READ COMMITTED` isolation.

**Not independently established in this audit:**

- A genuinely clean virtual environment installation was not performed; pip dry-run dependency resolution is evidence of resolvability, not a completed clean install.
- The application was imported, but a separate live Uvicorn launch and HTTP smoke test were not repeated in this audit. The prior report's live API output remains historical evidence, not newly reproduced here.
- The concurrency test now proves a competing backend is waiting on the held PostgreSQL row lock.
- This audit did not exercise deployment, production database safety, backups, or operations.

## 5. Transaction and concurrency audit

`backend/app/services/movements.py::record_movement` (lines 19–89) validates the movement amount before opening `session.begin()`. Inside that transaction it checks product/store existence and active status, fetches the matching balance with `lock=True`, computes signed delta, rejects a negative result, updates the balance, flushes the movement row, and flushes its activity row. Transaction exit commits the combined writes; a database exception during these writes rolls the transaction back and is translated to a domain database error. Domain errors are re-raised without partial writes.

`backend/app/repositories/inventory.py::get_balance` (lines 64–80) filters by both `product_id` and `store_id` and applies `.with_for_update()` when requested. With PostgreSQL READ COMMITTED, a competing `SELECT FOR UPDATE` on the same row waits for the first transaction; once it acquires the row, the command sees the latest committed row version and the subsequent quantity check prevents the second oversell. This conclusion is based on source semantics and the observed PostgreSQL isolation setting. `test_database_failure_rolls_back_balance_movement_and_activity` (test file lines 115–143) injects a failing activity insert after the earlier writes and checks that all three state changes roll back.

The concurrency test opens separate sessions but its initial barrier does not guarantee overlap at the locked read; see M-1. Therefore the implementation's lock path is present and appropriate, but deterministic race regression coverage is incomplete.

## 6. Database and migration audit

The ORM models and migration revisions were compared directly:

- Products use integer primary keys, unique indexed SKU, indexed name/category, `NUMERIC(12,2)` nonnegative price, and active/timestamp fields.
- Stores have unique indexed code and name.
- Inventory balances have foreign keys to product/store, unique `(product_id, store_id)`, a store index, nonnegative quantity and reorder level; deletion is restricted.
- Stock movements use a composite foreign key to the unique product/store balance pair, nonzero signed delta, valid type and sale/restock sign checks, nonnegative before/after quantities, and `quantity_after = quantity_before + quantity_delta`. Indexes cover product/store/created time and created time. Seed keys are nullable unique.
- Activity records retain optional linked IDs with `SET NULL`, unique optional movement linkage and seed key, event check, timestamps, and lookup indexes.
- Timestamps use timezone-aware columns and UTC-aware application defaults. The engine's connection hook sets PostgreSQL session timezone to UTC; fixture local times explicitly convert Asia/Kolkata to UTC.
- Revision `20261119_0001` creates tables, keys, checks and base indexes; downgrade removes dependent tables in reverse dependency order. Revision `20261119_0002` adds store balance and movement history query indexes and downgrades by dropping those indexes.

`alembic check` against the isolated test database returned “No new upgrade operations detected.” This is corroborative only; the direct ORM and migration inspection above is the integrity evidence. No schema defect was found in the inspected constraints.

## 7. Seed integrity audit

`backend/app/db/seed_data.py::seed_database` wraps fixture inserts in one `session.begin()` transaction. Store codes and product SKUs are stable lookup keys; missing records are inserted, existing product/store rows are reused, and only missing product/store balance pairs are created. Existing inventory quantities are not overwritten. Activity rows use stable `a1`–`a6` keys, linked movement rows use matching `seed-a*` keys, and the CSV import is intentionally a batch activity without a product/store movement. Decimal fixture prices and timezone conversion are explicit.

The frontend seed matrix is 10 products × 3 stores = 30 quantities. It sums to 396 units: Central Store 193, City Centre 89, Riverside Outlet 114. The existing implementation report records two identical seed runs with these totals; the test suite includes seed rerun/count/totals coverage. PostgreSQL transactional DDL/DML defaults and the single transaction mean an interrupted seed transaction rolls back its inserts; rerun can safely fill missing fixtures. Existing rows are not reset. No seed integrity defect was found in the inspected logic.

## 8. Dependency and runtime audit

Inspected `pyproject.toml`, all three requirements files, and backend setup instructions. Direct versions match the stated environment: Python `>=3.13,<3.16`; FastAPI 0.165.0; Pydantic 2.14.4; SQLAlchemy 2.1.9; Psycopg 3.3.9; Alembic 1.20.1; Uvicorn 0.54.0; Pytest 9.2.0. The lock file pins the resolved transitive set, including `httpx2==2.16.2` and `httpcore2==2.16.2`.

`httpx2` is explicitly listed in project test dependencies and is present in the lock. The full test suite using FastAPI `TestClient` passes with it in the current environment. The initial audit used a dependency dry run; the remediation later completed a real clean Python 3.15 virtual environment installation from `requirements-lock.txt`, with clean `pip check`.

## 9. Test isolation and coverage audit

`backend/tests/conftest.py` enforces presence of `TEST_DATABASE_URL`, a loopback host, and `_test` suffix before migration and the autouse truncation. It then points the app at that test URL. This is meaningful protection but does not guarantee effective URL separation from `.env` or normalized aliases; see H-1. The current checkout had no `backend/.env`, and tests were run only against `127.0.0.1:55432/stockflow_test`, a temporary database.

Coverage includes product/store CRUD and validation, provisioning, pagination/filtering/search, inventory details, movement type and quantity validation, insufficient stock, movement/activity persistence, transactional rollback, seed totals/rerun, health and OpenAPI. Remediation added ten database-target guard tests and focused post-commit response behavior coverage, and made the row-lock contention test deterministic. The suite passes all 33 tests.

## 10. API contract and application behavior

Compared route handlers, schemas, service functions, OpenAPI setup, and `docs/architecture/STOCKFLOW_API_CONTRACT.md`. Request/response validation is expressed through Pydantic schemas; create routes return 201; unknown resources return 404; insufficient stock and conflicts return 409; validation errors return structured 422; list routes use bounded skip/limit pagination and documented filters. Products and stores are soft-deactivated; active listings/movement creation exclude inactive entities, while detail behavior can still expose retained records. New products provision zero balances for active stores and new stores provision zero balances for active products; product edits do not mutate quantities. Movement and activity snapshots are inserted together.

The live OpenAPI description has 12 paths per the prior report. This audit did not relaunch Uvicorn to independently recheck the HTTP document. No material route/schema contract mismatch was found in static comparison. Import processing and replenishment execution remain frontend-only/demo functionality and are outside Chunk 1.

## 11. Documentation changes made

- Corrected Section 12 in `docs/reports/CHUNK_1_BACKEND_FOUNDATION.md`: it now maps the four simulation learning domains to evidenced Chunk 1 work, explicitly marks Advanced Data Structures as not demonstrated and general CSV munging as future work, and states StockFlow is independent academic work rather than a Walmart/Forage deliverable.
- Corrected `backend/README.md` test safety instructions to describe the effective database identity guard and require both URLs.
- This audit now records remediation status; the detailed results are in `docs/reports/CHUNK_1_REMEDIATION_REPORT.md`.
- No files were moved or removed. Existing architecture/API docs, frontend audit evidence, and the implementation report remain in their current canonical directories.

## 12. Final documentation tree

```text
docs/
├── architecture/
│   ├── README.md
│   ├── STOCKFLOW_API_CONTRACT.md
│   ├── STOCKFLOW_BACKEND_ARCHITECTURE.md
│   └── STOCKFLOW_DATABASE_DESIGN.md
├── audits/
│   ├── CHUNK_1_TARGETED_BACKEND_AUDIT.md
│   ├── STOCKFLOW_FINAL_FRONTEND_AUDIT.md
│   └── runtime-final-evidence/ (historical screenshots and probes retained)
├── engineering/
│   └── STOCKFLOW_CODEBASE_HANDOVER.md
└── reports/
    ├── CHUNK_1_BACKEND_FOUNDATION.md
    └── CHUNK_1_REMEDIATION_REPORT.md
```

Root `README.md` is the project entry point; `backend/README.md` contains backend setup instructions. The API contract is already in the recommended architecture directory. No redundant documentation copies were identified for deletion.

## 13. Remaining limitations and recommended next actions

- Decide whether movement write APIs need idempotency keys and define client retry behavior before network clients rely on automatic retry.
- Movement idempotency keys and client retry behavior remain a future API integration decision.
- A separate live Uvicorn process smoke test was not part of this remediation; imports and TestClient/API tests passed.
- Import/replenishment workflows, authentication/users, currency policy, operational deployment/security/backups, and a complete movement ledger are not part of Chunk 1.

## 14. Explicit Chunk 1 acceptance recommendation

**PASS — submit Chunk 1 for explicit acceptance.** H-1, M-1, and M-2 have been remediated and verified as documented in `docs/reports/CHUNK_1_REMEDIATION_REPORT.md`. Review and explicitly accept the remediation report before starting Chunk 2. No Chunk 2 or Chunk 3 work was started.

## 15. Verification commands and results

Executed from `backend/` using the isolated temporary PostgreSQL database:

- Initial audit: `python -m pytest -q` — **22 passed in 5.74s** (historical result).
- Remediation: `python -m pytest -q` — **33 passed in 10.42s**.
- `alembic check` — **No new upgrade operations detected**.
- `python -c "import app.main"` with `DATABASE_URL` supplied — **passed**.
- `python -m pip check` — **No broken requirements found**.
- Remediation: clean Python 3.15 venv `python -m pip install -r requirements-lock.txt` — **completed successfully**.
- PostgreSQL probe — **PostgreSQL 18.6, READ COMMITTED, database `stockflow_test`**.

The temporary PostgreSQL listener was stopped after the checks. No frontend checks were needed or run; frontend source was not changed.
