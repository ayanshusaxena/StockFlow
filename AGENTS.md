# StockFlow workspace instructions

<!-- postman-cli:installation:start -->
Postman CLI is installed on this device and can be used for API engineering work when backend work is authorized.
<!-- postman-cli:installation:end -->

StockFlow is a React + Vite + Tailwind CSS project running inside Figma Make. Its frontend lives in `frontend/`; `.figma/` remains at the repository root. A Vite server can be started from `frontend/` with `corepack pnpm run dev` (port 8443 by default).

## Project structure

- `frontend/src/main.tsx` is the entrypoint; it imports `frontend/src/index.css` and mounts `frontend/src/App.tsx` into `#root`.
- `frontend/src/App.tsx` re-exports `frontend/src/app/App.tsx`.
- `frontend/src/app/App.tsx` provides shared state and routing.
- `frontend/src/app/routes.tsx` contains the app shell and five primary routes.
- `frontend/src/app/data.ts` contains model types and demonstration data.
- `frontend/src/app/store.tsx` contains in-memory state.
- `frontend/index.html` is the Vite HTML shell.
- `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/tsconfig.json`, and `frontend/vite.config.ts` hold the frontend configuration.
- `.figma/` contains Figma Make scripts and configuration. Those scripts change to `frontend/` before running frontend commands.
- `.mise.toml` records Node.js and pnpm toolchain versions.

Only follow imports or inspect other files when needed, when a documented path is missing, or when the repository contradicts this guide.

## Dependencies

- Runtime: React 19, React DOM 19, React Router 7, and Lucide icons.
- Styling: Tailwind CSS v4 through `@tailwindcss/vite`.
- Build tooling: Vite 8, TypeScript, and `@vitejs/plugin-react`.
- Formatting: oxfmt.

## Styling

`frontend/src/main.tsx` imports `frontend/src/index.css`, so global font wiring belongs there. Keep CSS `@import` statements first, then add any `@font-face` rules and font-family defaults there.

Use Tailwind utility classes directly in JSX and put global CSS or Tailwind v4 theme customization in `frontend/src/index.css`. This project does not need a Tailwind config or PostCSS config. Tailwind emits utility classes in `@layer utilities`, and CSS outside any cascade layer overrides every layer regardless of specificity. Put global element styles such as resets and defaults for `body`, headings, buttons, or inputs inside `@layer base` so utility classes on those elements still apply. Tailwind Preflight already applies `box-sizing: border-box`, removes default margins, and sets `font: inherit` on form controls; do not repeat those rules.

Preserve the current layouts, typography, colors, theme tokens, navigation architecture, and business logic unless a task explicitly requests a change. See `docs/engineering/STOCKFLOW_CODEBASE_HANDOVER.md` before planning backend integration; frontend fixtures do not define approved API contracts.
