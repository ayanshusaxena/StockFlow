# StockFlow

StockFlow is a multi-store inventory and replenishment management system. The React frontend uses the FastAPI/PostgreSQL service for catalogue, inventory, movement history, replenishment, dashboard summaries, and CSV inventory imports.

## Frontend setup

Requirements: Node.js 22 and pnpm 10.34.3 (versions are recorded in `.mise.toml`).

```powershell
Set-Location frontend
corepack pnpm install --frozen-lockfile
Copy-Item .env.example .env
corepack pnpm run dev
```

The API base defaults to `http://127.0.0.1:8000/api/v1`; set `VITE_API_BASE_URL` in `frontend/.env` when the backend uses another address. Vite uses port `8443` by default. Useful commands from `frontend/`:

```powershell
corepack pnpm run typecheck
corepack pnpm run build
corepack pnpm run preview
corepack pnpm run format
```

The app has five primary routes: `/overview`, `/catalogue`, `/inventory`, `/replenishment`, and `/import`. The root route redirects to `/overview`.

## Repository layout

- `frontend/` — React 19, React Router 7, TypeScript, Vite 8, Tailwind CSS 4 app and its lockfile/configuration.
- `backend/` — FastAPI API, SQLAlchemy models/services, Alembic migrations, seed data, and PostgreSQL-backed tests. See its README.
- `docs/audits/` — frontend acceptance audit and its runtime screenshots.
- `docs/architecture/` — backend architecture, database design, and API contract.
- `docs/engineering/` — frontend engineering handover.
- `docs/reports/` — implementation, remediation, and master execution reports.
- `.figma/` — Figma Make integration scripts and site configuration, retained at the repository root.

See [the codebase handover](docs/engineering/STOCKFLOW_CODEBASE_HANDOVER.md) for architecture, models, limitations, and backend integration boundaries.

## Backend quick start

Use Python 3.13–3.15 and PostgreSQL. From `backend/`, create a virtual environment, install the pinned backend dependencies, copy `.env.example` to `.env`, and configure `DATABASE_URL`. Start the backend in its own terminal:

```powershell
alembic upgrade head
python -m app.db.seed_data
uvicorn app.main:app --reload
```

The API docs are served at `http://127.0.0.1:8000/docs`. For tests, set `TEST_DATABASE_URL` to a separate loopback PostgreSQL database ending in `_test`, then run `python -m pytest`; the test suite refuses a non-loopback or non-test database.

Movement writes and CSV import commits require an `Idempotency-Key`. CSV imports use UTF-8 headers `SKU`, `Store` (name or code), `Quantity`, and optional `Reorder Level`; any rejected row blocks the whole batch. Authentication and authorization are not implemented, so keep the API on a trusted local/demo network and do not expose this MVP as a secured multi-user service.

See [backend setup](backend/README.md) and the [Chunk 1 report](docs/reports/CHUNK_1_BACKEND_FOUNDATION.md) for full commands, verification evidence, and known limits.

For GitHub, Render Free and Vercel setup, environment variables, migrations and public verification, see the [deployment preparation guide](docs/engineering/STOCKFLOW_DEPLOYMENT.md).

For the integrated implementation evidence and outstanding review items, see the [business logic and CSV report](docs/reports/CHUNK_2_BUSINESS_LOGIC_DATA_MUNGING.md) and the [master execution report](docs/reports/MASTER_EXECUTION_FINAL_REPORT.md).
