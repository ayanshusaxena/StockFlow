# StockFlow Codebase Handover

**Status:** Frontend remains a demonstration-only client. Backend Chunk 1 is implemented independently under `backend/`; frontend API integration has not started. See `docs/reports/CHUNK_1_BACKEND_FOUNDATION.md` for backend verification and known limits.

## 1. Existing application architecture

The frontend is a React 19 single-page application built with Vite 8, TypeScript 5.7, React Router 7, and Tailwind CSS 4. `frontend/index.html` loads `frontend/src/main.tsx`, which mounts `frontend/src/App.tsx` and the global stylesheet. `src/App.tsx` is a compatibility re-export. `src/app/App.tsx` wraps the router in `StoreProvider`. The router, shell, shared UI helpers, and all five page implementations currently live together in `src/app/routes.tsx`.

The five primary routes are `/overview`, `/catalogue`, `/inventory`, `/replenishment`, and `/import`; `/` redirects to `/overview`, and unknown paths show a not-found page. Inventory includes Stock Balances and Movement History views. Navigation and theme selection are client-side state.

The sibling `backend/` directory now contains the Chunk 1 FastAPI/PostgreSQL service, Alembic migrations, repositories, and tests. The API is not called by the React app; the two parts remain independently runnable.

Figma Make configuration remains in the repository-root `.figma/` directory. Its scripts change into `frontend/` before invoking package commands. `frontend/vite.config.ts` loads the site configuration from `../.figma/make/site.json` and retains the existing Figma plugins, Tailwind plugin, React plugin, and `@` source alias.

## 2. Final directory structure

```text
StockFlow/
├── .figma/                         # Figma Make configuration and launcher scripts
├── backend/
│   ├── app/                        # FastAPI routes, services, repositories, ORM, schemas
│   ├── alembic/                    # Versioned PostgreSQL migrations
│   ├── tests/                      # Isolated PostgreSQL tests
│   └── README.md
├── docs/
│   ├── audits/
│   │   ├── STOCKFLOW_FINAL_FRONTEND_AUDIT.md
│   │   └── runtime-final-evidence/ # Existing audit screenshots
│   ├── architecture/              # Backend architecture, database design, API contract
│   ├── engineering/
│   │   └── STOCKFLOW_CODEBASE_HANDOVER.md
│   └── reports/
│       └── CHUNK_1_BACKEND_FOUNDATION.md
├── frontend/
│   ├── public/                     # Static assets (favicon)
│   ├── src/
│   │   ├── app/                    # Router pages, fixtures, and in-memory store
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   └── vite.config.ts
├── .gitignore
├── .mise.toml                      # Node and pnpm tool versions
├── AGENTS.md                       # Workspace contributor instructions
└── README.md
```

## 3. Important files

- `frontend/src/main.tsx` — React DOM entrypoint and stylesheet import.
- `frontend/src/App.tsx` — compatibility re-export for the app component.
- `frontend/src/app/App.tsx` — provides shared state and React Router.
- `frontend/src/app/routes.tsx` — app shell, five page workflows, dialogs, and route definitions. It is a large single file and is a likely future maintenance boundary; split only when feature work warrants it.
- `frontend/src/app/data.ts` — TypeScript domain-shaped models and demonstration fixtures.
- `frontend/src/app/store.tsx` — React context state and in-memory product/inventory/activity mutations.
- `frontend/src/index.css` — Manrope font import, theme tokens, global base rules, component styling, and responsive breakpoints.
- `frontend/public/favicon.png` — static favicon.
- `frontend/vite.config.ts` — Vite, React, Tailwind, alias, dev server settings, and Figma Make plugins.
- `frontend/package.json` and `frontend/pnpm-lock.yaml` — package scripts and locked dependency graph.
- `frontend/tsconfig.json` — strict TypeScript settings and `@/*` alias.
- `docs/audits/STOCKFLOW_FINAL_FRONTEND_AUDIT.md` — detailed prior live-browser audit and screenshots. Treat findings as a baseline to verify, not as a replacement for source inspection.
- `backend/app/` — Chunk 1 backend route, schema, service, repository, model, configuration, session, and seed layers.
- `backend/alembic/` — explicit migration history; app startup does not create tables.
- `backend/tests/` — PostgreSQL-backed tests guarded to loopback databases ending in `_test`.
- `docs/architecture/STOCKFLOW_BACKEND_ARCHITECTURE.md`, `STOCKFLOW_DATABASE_DESIGN.md`, and `STOCKFLOW_API_CONTRACT.md` — current backend design and implemented Chunk 1 contract.
- `docs/reports/CHUNK_1_BACKEND_FOUNDATION.md` — actual test, migration, seed, and runtime results.

## 4. Existing frontend data models

`data.ts` defines:

- `Theme`: `"ocean" | "forest" | "slate"`.
- `Product`: `sku`, `name`, `category`, and numeric `price`.
- `Store`: `id`, `name`, and `location`.
- `InventoryRow`: a product-shaped record plus `id`, `store`, `storeId`, `quantity`, `reorder`, and `updated`.
- `Activity`: `id`, `time`, movement/import `type`, product display name, optional SKU, store display name, numeric `change`, note, and optional `batch` marker.

Fixtures define three Gwalior stores, ten products, thirty product/store inventory rows, and six activity examples. These are frontend fixture shapes, not approved persistence schemas. In particular, `store` and `product` names are denormalized into inventory/activity display records; future API representation and identity rules need agreement.

## 5. State management

`StoreProvider` initializes React `useState` from the fixture arrays. `useAppStore()` exposes `products`, `inventory`, `activities`, `addProduct`, and `recordMovement` to routes. Product creation appends a product only. A movement looks up one inventory row, applies Sale/Restock/Adjustment arithmetic, blocks a negative result, updates that row, and prepends an activity. State is shared while the app remains mounted but is neither persisted nor synchronized; refresh resets it to fixtures. The new backend is a separate service and does not change these client-side behaviors. Theme, mobile navigation, dialogs, filters, and import-stage selections are page-local UI state.

## 6. Existing functionality

- Overview aggregates fixture and current in-session balances, shows stock health, alerts, and recent activity.
- Catalogue supports product search, category filtering, sorting, coverage display, and an add-product form.
- Inventory supports store/search/status filtering, SKU filtering via query string, balance/history tabs, and Sale/Restock/Adjustment dialogs.
- Replenishment groups out-of-stock and below-reorder rows, suggests a restock amount based on twice the reorder level, and opens a contextual restock action.
- Data Import presents upload, validation/cleaning, review, and results stages.
- Ocean, Forest, and Slate visual themes are available. Layout adapts to desktop, tablet, and mobile.

The details above describe UI behavior; they do not imply server-side persistence or completed operations.

## 7. Known frontend limitations and technical debt

The current audit (`docs/audits/STOCKFLOW_FINAL_FRONTEND_AUDIT.md`) records these behaviors and accessibility findings; recheck against the current app when changing them:

- CSV upload stages use fixed demonstration rows/counts. Uploaded file contents are not parsed, and the success screen does not commit inventory changes.
- The frontend demo does not add local inventory rows when a product is created. The separate Chunk 1 API provisions zero balances, but the frontend is not integrated with it.
- Overview urgency links pass `urgency=out|low`, but the replenishment page does not apply that query filter.
- Multi-store batch activity can appear in store-filtered movement history; batch ownership/filter semantics are unresolved.
- Frontend mutations still reset on refresh. The backend API and PostgreSQL persistence exist for Chunk 1, but the frontend is not integrated; authentication, authorization, and cross-client synchronization are not implemented.
- Fixture timestamps and some displayed dates are fixed/stale; activity and inventory timestamps are display strings rather than normalized date values.
- Dialogs have modal semantics and Escape dismissal, but the audit found that keyboard focus can leave an open dialog. Full focus entry, containment, and restoration need work.
- `routes.tsx` contains the app shell and all feature screens in one large module. Automated test and lint scripts are not currently defined.
- The audit also flags small secondary text, long mobile lists, incomplete exhaustive contrast/accessibility coverage, and potentially misleading import success copy.

## 8. Future backend integration requirements

The implemented Chunk 1 contract is documented at `docs/architecture/STOCKFLOW_API_CONTRACT.md`; it is not a complete integration or public contract. Before frontend integration, backend and frontend engineers should agree on:

1. Confirm the implemented identity scheme: generated integer product/store IDs, SKU/store code business keys, and one balance per product/store pair. Agree on how display snapshots and price changes should behave over time.
2. Product/store provisioning rules: Chunk 1 creates zero balances for active stores on product creation, and for active products on store creation. Confirm whether opening quantities need a separate workflow.
3. Confirm the implemented movement semantics before integration: positive sale/restock request quantities, signed adjustment deltas, no negative balance, row locking, and UTC timestamps. Actor/audit fields and idempotency for retries remain undefined.
4. Replenishment rules: reorder thresholds, suggested quantity formula, urgency filters, and whether values are server-calculated or client-calculated.
5. CSV import lifecycle: actual parsing and validation ownership, row-level errors, cleaning/review edits, commit semantics, duplicate handling, atomicity/partial success, batch records, and truthful result counts.
6. Query and pagination needs for catalogue, inventory, and movement history, including store scope and filter/sort parameters.
7. Loading, empty, validation, authorization, conflict, and network error states, plus authentication and tenant/store access rules.
8. Persistence expectations and contract/version strategy. Map API responses into the existing view model only after confirming these decisions; avoid treating fixture display strings as canonical API fields.

Likely frontend service boundaries are product catalogue reads/creation, store reads, inventory balance reads, movement creation/history reads, replenishment queue reads, and import upload/validation/commit. The first four are represented in the current backend contract; replenishment and import remain future work. The current React context store should eventually consume the API while preserving UI behavior, with explicit request lifecycle and error state.

## 9. Install, run, and build

Use Node.js 22 and pnpm 10.34.3 as recorded in `.mise.toml`. From the repository root:

```powershell
Set-Location frontend
corepack pnpm install --frozen-lockfile
corepack pnpm run dev
corepack pnpm run typecheck
corepack pnpm run build
```

`dev` serves on port 8443 by default. `pnpm run preview` serves the built frontend. The audit and screenshots are retained under `docs/audits/`.

For backend setup, migrations, isolated test database requirements, and API commands, see `backend/README.md` and `docs/reports/CHUNK_1_BACKEND_FOUNDATION.md`.
