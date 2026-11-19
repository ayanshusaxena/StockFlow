# StockFlow Chunk 1 Remediation Report

**Date:** 2026-11-19  
**Scope:** Remediation of H-1, M-1, and M-2 from `docs/audits/CHUNK_1_TARGETED_BACKEND_AUDIT.md`  
**Recommendation:** PASS for Chunk 1 review and explicit acceptance. Do not begin Chunk 2 until this report is reviewed and accepted.

## 1. H-1 — destructive test database protection

Added `backend/tests/database_safety.py` and moved validation to the top of `backend/tests/conftest.py`. The guard runs before changing `DATABASE_URL` and before importing application/database modules, running Alembic, or enabling the autouse truncate fixture.

The guard resolves `DATABASE_URL` from the process environment first, then `backend/.env`, matching process-over-dotenv precedence. It requires both a test URL and an effective development URL; checks that the test backend is PostgreSQL, the test host resolves only to loopback, and the database name ends in `_test`; then compares resolved host address sets, effective port, and database name. Different URL driver names, credentials, or `localhost`/`127.0.0.1` spellings do not bypass the identity check. An unparseable URL, unresolved host, missing host/database, or missing development identity fails closed. Usernames/passwords are not included in guard errors.

Added ten focused tests covering a valid isolated database, exact conflict, `.env` conflict, process environment precedence, localhost/IPv4 alias collision with different drivers/credentials, missing test URL, missing development identity, non-loopback host, unresolved-host fail-closed behavior, and a database name without `_test`. These are in `backend/tests/test_database_safety.py`.

The test instructions now require both URLs and explain the guard in `backend/README.md`. The actual destructive test run used only the temporary loopback `stockflow_test` database on port 55432; the separate temporary development identity was `stockflow` on that disposable cluster. The user's regular PostgreSQL service was not used.

## 2. M-1 — deterministic concurrency regression

Reworked `test_postgres_row_lock_prevents_concurrent_oversell` in `backend/tests/test_inventory_movements.py`:

1. Two worker threads create independent SQLAlchemy sessions and record distinct PostgreSQL backend PIDs; the test asserts those PIDs differ.
2. The first worker executes the real locked balance query, then pauses while its transaction still owns that row lock.
3. The second worker reaches the same balance query using its own backend.
4. The test polls `pg_stat_activity` for the second backend and requires `wait_event_type = 'Lock'` before it releases the first worker.
5. The first worker commits its sale of 15; the second then sees 9 remaining and rejects its sale of 15.

The test asserts exactly one sale and one rejection, balance 9, and one additional movement and activity record. The explicit lock-wait assertion makes absence of lock contention fail the test. The release event is set in `finally`, worker results have timeouts, and the executor is shut down in a nested `finally` so failure paths release the holder.

Observed verification: this deterministic test passed against PostgreSQL 18.6 at READ COMMITTED isolation as part of both the focused tests and full suite. A separate negative-control run with production locking deliberately disabled was not performed; the test's required lock-wait assertion and one-success/one-rejection assertion would fail on that path.

## 3. M-2 — post-commit refresh ambiguity

Removed `session.refresh(movement)` from `backend/app/services/movements.py::record_movement`. The movement and activity inserts are flushed inside the existing transaction, so the movement's generated ID and response fields are already available. The session is configured with `expire_on_commit=False`; the function can return this populated object after commit without another database call. There is no retry added, and the existing balance/movement/activity atomic transaction remains unchanged.

Added `test_movement_response_does_not_depend_on_post_commit_refresh`: it patches `Session.refresh` to raise if called, records a movement, then checks the returned movement fields, persisted stock, movement count, and activity count. It passed. The existing injected activity-insert failure test also passed and confirms the three writes still roll back together.

Movement writes still have no idempotency key. Before a frontend/API client automatically retries sale, restock, or adjustment requests, define an idempotency key at the movement write request boundary, scoped at minimum to the authenticated tenant/store context when that exists. Persist the key and outcome atomically with the movement, and return the original outcome for duplicate requests. This is a future integration design item, not part of this remediation.

## 4. Verification commands and results

All database verification used the temporary PostgreSQL 18.6 cluster at `127.0.0.1:55432`, database `stockflow_test`; observed transaction isolation was READ COMMITTED. From `backend/` in PowerShell, the full suite command was:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/stockflow_test"
$env:DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/stockflow"
python -m pytest -q
```

Results:

- `python -m pytest -q` — **33 passed in 9.96s**.
- `python -m pytest -q tests/test_database_safety.py tests/test_inventory_movements.py::test_postgres_row_lock_prevents_concurrent_oversell tests/test_inventory_movements.py::test_movement_response_does_not_depend_on_post_commit_refresh tests/test_inventory_movements.py::test_database_failure_rolls_back_balance_movement_and_activity` — **13 passed in 3.55s** (ten guard tests and three focused behavior tests).
- `alembic check` with the isolated test URL — **No new upgrade operations detected**.
- `python -c "import app.main; print('app.main import OK')"` with the test URL — **passed**.
- `python -m pip check` in the project environment — **No broken requirements found**.
- A new Python 3.15 virtual environment was created at a temporary path and `python -m pip install -r requirements-lock.txt` completed with **Successfully installed** for every locked package. This was a real installation, not a dry run.
- The temporary PostgreSQL server was stopped after verification; port 55432 had no remaining listener.

No separate Uvicorn process startup was run in remediation. The backend import and complete TestClient suite passed.

## 5. Files changed

- `backend/tests/database_safety.py` — new fail-closed effective URL resolver and identity comparison.
- `backend/tests/conftest.py` — run validation before environment mutation/app/database initialization.
- `backend/tests/test_database_safety.py` — ten focused database guard tests.
- `backend/tests/test_inventory_movements.py` — deterministic PostgreSQL lock-wait test and post-commit refresh regression.
- `backend/app/services/movements.py` — remove unnecessary post-commit refresh.
- `backend/README.md` — corrected setup/test database safety instructions.
- `docs/audits/CHUNK_1_TARGETED_BACKEND_AUDIT.md` — status and evidence updated for the remediated findings.
- `docs/reports/CHUNK_1_BACKEND_FOUNDATION.md` — current test setup and remediation follow-up added.
- `docs/reports/CHUNK_1_REMEDIATION_REPORT.md` — this report.

No frontend files, database models, migrations, dependency pins, or lockfiles changed. No documentation files were moved or deleted.

## 6. Remaining limitations

- No movement idempotency mechanism exists yet; retry semantics must be decided before clients retry writes automatically.
- The no-lock negative-control test was not executed separately, though the deterministic test requires PostgreSQL to report an actual lock wait.
- No separate live Uvicorn process smoke test was run as part of remediation; app import, Alembic, and TestClient API tests passed.
- Existing Chunk 1 scope limitations remain: no frontend integration, replenishment execution, CSV import pipeline, authentication, or production operations setup.

## 7. Final recommendation

**PASS — Chunk 1 remediation is complete and verified. Submit this report for explicit review and acceptance. Do not start Chunk 2 or Chunk 3 until the user accepts this report.**
