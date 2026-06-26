# Legacy Frontend — Marketplace / Payments / Buyer Flows

Moved out of `frontend/src/app/` during the capstone re-scope (June 2026)
so they are no longer built or routed by Next.js, while remaining on disk
for the separate **TerraFoma LTD** commercial product. See
`backend/legacy/README.md` for the matching backend rationale — the
revised ALU capstone proposal excludes secondary-market trading,
blockchain settlement, and buyer/checkout flows from the academic
prototype.

## What's here

| Path | Original location | Purpose |
|---|---|---|
| `app/marketplace/page.tsx` | `src/app/marketplace` | Browse/buy listed carbon credits |
| `app/registry/page.tsx` | `src/app/registry` | Public credit registry |
| `app/certificate/[id]/page.tsx` | `src/app/certificate/[id]` | Purchase-certificate viewer |
| `app/purchase-success/page.tsx` | `src/app/purchase-success` | Post-checkout confirmation |
| `app/dashboard/page.tsx` | `src/app/dashboard` | Business/buyer GHG-footprint calculator |
| `app/api/checkout/route.ts` | `src/app/api/checkout` | Polar.sh checkout session creation |
| `app/api/confirm-payment/route.ts` | `src/app/api/confirm-payment` | Payment confirmation callback |
| `app/api/webhooks/polar/route.ts` | `src/app/api/webhooks/polar` | Polar.sh payment webhook handler |
| `app/admin/dashboard/page.tsx` | `src/app/admin/dashboard` | Admin credit-marketplace console (pending/listed/sold/retired credit stats, `tCO2e` totals) — calls `api.getCreditStats()` → `/api/credits/stats`, which lives in the also-relocated `backend/legacy/routers/credits.py` and is no longer registered in `main.py`. Kept here as a unit so the page and the endpoint it depends on move together. |

## Status

- These directories sit outside `frontend/src/app`, so Next.js's file-based
  router no longer builds or serves them — the routes are effectively
  disabled in the capstone app without deleting any code.
- Internal imports (e.g. `@/components/...`, `@/lib/api`) were **not**
  rewritten. They will resolve correctly again only once these files are
  copied back into a project where `@/` still maps to that project's
  `src/` (e.g. if reintegrated into the TerraFoma LTD codebase, or moved
  back under `frontend/src/app/` here).
- The Navbar, home page, and `ProtectedRoute` role checks in the live app
  no longer link to any of these routes.
