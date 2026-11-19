# StockFlow backend readiness

**Status:** Prepared for a disposable academic demonstration. Hosted database setup and public smoke tests remain pending.

The audit's confirmed balance coverage defects were remediated. Product and store creation share a PostgreSQL transaction lock. Reactivation provisions missing balances without changing existing quantities. CSV parsing rejects malformed quotes and out-of-range quantities. Unrelated ambiguous store names no longer stop imports. Movement writes reject out-of-range results.

The isolated PostgreSQL 18.6 backend suite passed 53 tests. Frontend type checking and production build passed. A CORS preflight from a representative origin returned HTTP 200 with `Content-Type` and `Idempotency-Key` allowed. Set `CORS_ORIGINS` to the final Vercel origin and verify it again publicly.

The demo seed constants remain unchanged. On a new isolated PostgreSQL database, migrations reached head and two consecutive seed runs each reported 10 products, 3 stores, 30 balances, and 396 units. Hosted seed repeatability must still be checked after creating the separate disposable hosted database. No hosted database or public API was accessed.

The public API is unauthenticated. Use disposable, nonsensitive sample data only. Render Free has no predeploy migration command in this configuration. Run Alembic and the seed once from the developer machine using the exact instructions in `docs/engineering/STOCKFLOW_DEPLOYMENT.md`. Keep the existing development database and the separate `_test` database out of the hosted setup.
