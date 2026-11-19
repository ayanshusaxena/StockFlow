 # StockFlow backend workspace

FastAPI backend for products, stores, inventory balances, stock movements, and activity history. See `../docs/architecture/` for the design and `../docs/reports/CHUNK_1_BACKEND_FOUNDATION.md` for implementation details.

The master execution evidence is in `../docs/reports/MASTER_EXECUTION_FINAL_REPORT.md`; SKU/replenishment/CSV behavior is described in `../docs/reports/CHUNK_2_BUSINESS_LOGIC_DATA_MUNGING.md`.

## Local setup

Use Python 3.13–3.15 and PostgreSQL 18 (or a compatible supported PostgreSQL release). The implementation was run with Python 3.15.2 and PostgreSQL 18.6. From this directory:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Create a local PostgreSQL role and databases if needed (choose your own password; do not commit it):

```sql
CREATE ROLE stockflow LOGIN PASSWORD 'replace-with-a-local-password';
CREATE DATABASE stockflow OWNER stockflow;
CREATE DATABASE stockflow_test OWNER stockflow;
```

Edit `.env` with the connection URL for your development database. Run migrations, load fixtures, and start the API:

```powershell
alembic upgrade head
python -m app.db.seed_data
uvicorn app.main:app --reload
```

API docs are at `http://127.0.0.1:8000/docs`; health is at `/health`. Migration and seed commands are intentionally separate; the seed command never creates tables.

The API includes database-backed `/api/v1/dashboard/summary`, `/api/v1/inventory/replenishment`, `/api/v1/products/lookup/{sku}`, and CSV inventory preview/commit endpoints. Movement POST requests require `Idempotency-Key`; exact retries return the original movement, while reusing a key for a different payload returns 409.

CSV requests send the raw UTF-8 CSV body as `text/csv` to `/api/v1/inventory/import/preview` and `/commit`. Required headings are `SKU`, `Store` (store name or code), and `Quantity`; `Reorder Level` is optional. Preview validates references and duplicates. Commit is all-or-nothing: any rejected row prevents every balance change. Successful imports update absolute snapshot quantities and create per-row `csv_import` batch activity records in the same transaction. Commit requires an `Idempotency-Key` and safely replays an identical completed import.

## Tests

Tests require two explicit database identities: a development `DATABASE_URL` and a disposable `TEST_DATABASE_URL`. The guard resolves `DATABASE_URL` from the process first and `backend/.env` otherwise, matching the normal process-over-dotenv precedence. It requires PostgreSQL, an explicit host/database, a loopback test host, a `_test` test database name, and rejects matching resolved host addresses + port + database name. If either identity cannot be established, test setup stops before app/database initialization or destructive cleanup.

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://stockflow:your-local-password@127.0.0.1:5432/stockflow_test"
$env:DATABASE_URL = "postgresql+psycopg://stockflow:your-local-password@127.0.0.1:5432/stockflow"
python -m pytest
```

The test bootstrap validates both identities before setting the app's `DATABASE_URL` to the test target, applies Alembic migrations, and truncates only that validated test database between cases. URL credentials are never included in guard error messages. The process `DATABASE_URL` overrides `.env`; otherwise the guard reads `backend/.env`. See `../docs/reports/CHUNK_1_REMEDIATION_REPORT.md` for test evidence and limitations.
