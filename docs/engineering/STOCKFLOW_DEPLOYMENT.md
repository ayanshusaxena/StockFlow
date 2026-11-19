# StockFlow deployment

This is a short-lived academic demo. The public API is unauthenticated. Use only disposable sample data. Never enter real or sensitive information.

## Render Free backend

Connect GitHub and use `render.yaml`. The equivalent manual settings are root directory `backend`, build command `pip install -r requirements-lock.txt`, start command `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and health path `/health`. Set `PYTHON_VERSION=3.13.5`. Set `DATABASE_URL` privately to the hosted demo PostgreSQL URL using the `postgresql+psycopg://` scheme. Set `CORS_ORIGINS` to the exact Vercel origin, such as `https://stockflow-demo.vercel.app`, with no trailing slash. The Blueprint selects the free web plan and has no paid predeploy step. Provision a separate hosted PostgreSQL database and check its plan before use.

## One-time migrations and seed from the developer machine

Verify the hosted demo database identity and backup policy. From `backend/`, using the existing Python environment or the pinned requirements:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@HOST:PORT/DEMO_DATABASE'
python -m alembic upgrade head
python -m app.db.seed_data
```

These commands apply pending migrations and load the existing sample fixtures. On a fresh database the expected totals are 10 products, 3 stores, 30 balances, and 396 units. The seed uses stable keys and does not duplicate existing fixture records. Repeat the seed once and confirm the same totals. The hosted demo database must be separate from the existing development database. Tests require their own loopback PostgreSQL database ending in `_test`; never point `TEST_DATABASE_URL` at the hosted database.

## Vercel frontend

Connect the same GitHub repository. `vercel.json` builds `frontend/`, publishes `frontend/dist`, and rewrites direct React Router routes to `index.html`. Set `VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com/api/v1` in Vercel project settings before building. This is a public browser setting. Update Render `CORS_ORIGINS` to the actual Vercel origin. Add exact preview origins separately if needed.

## Public smoke tests

- [ ] Render `/health` reports connected.
- [ ] Fresh seeded `/api/v1/dashboard/summary` reports 10 products, 3 stores, 30 balances, and 396 units.
- [ ] Directly open and refresh `/overview`, `/catalogue`, `/inventory`, `/replenishment`, and `/import` on Vercel.
- [ ] Browser API requests use the HTTPS Render hostname and CORS preflights succeed.
- [ ] On disposable data, post a small restock, check history, and retry its key to confirm one application.
- [ ] Preview and commit a small CSV with a unique key, then inspect history.
- [ ] Record actual public URLs and observed results. Public deployment remains unverified until these checks pass.
