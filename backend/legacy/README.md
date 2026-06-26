# Legacy Module — Marketplace / Credit-Issuance / Payments

## Why this folder exists

The ALU BSc Software Engineering capstone proposal for TerraFoma (revised
version, June 2026) narrows the academic prototype to three components:

1. A locally-calibrated above-ground biomass (AGB) estimation model fusing
   Sentinel-1, Sentinel-2, and GEDI LiDAR data, validated against field plots
   in **Bugesera** (grassland/savanna) and **Rulindo** (agroforestry),
   Rwanda.
2. A lightweight monitoring dashboard for project registration, field-data
   upload, and audit-trail visualisation.
3. An uncertainty-reporting module accompanying every biomass estimate.

The proposal explicitly places the following **out of scope** for the
capstone: secondary-market credit trading, blockchain settlement, automated
carbon-credit issuance, buyer matching/settlement, and full registry
integration. Soil organic carbon and biodiversity co-benefits are likewise
excluded.

The code in this folder implements exactly those excluded capabilities. It
is **not deleted** — it is moved here, unmodified in logic, because it
remains directly useful to **TerraFoma LTD**, the separate commercial
venture operating in Rwanda. That commercial product is explicitly out of
scope for this academic Gem/repository and must not be conflated with the
capstone research prototype (see project custom instructions). Keeping this
code intact and clearly labeled means it can be lifted back out into the
commercial codebase without having to be reconstructed from git history.

## What's here

| File | Original location | Purpose |
|---|---|---|
| `routers/credits.py` | `backend/routers/credits.py` | Carbon-credit CRUD, listing, status transitions |
| `routers/transactions.py` | `backend/routers/transactions.py` | Buyer purchase transactions |
| `routers/certificates.py` | `backend/routers/certificates.py` | PDF purchase-certificate generation/download |
| `routers/dashboard.py` | `backend/routers/dashboard.py` | Business/buyer GHG-footprint calculator |
| `routers/plots_enhanced.py` | `backend/routers/plots_enhanced.py` | Alternate plot-analysis router built on `CarbonCreditEngine` (was already unregistered in `main.py`, not part of the live app) |
| `models/credit.py` | `backend/models/credit.py` | `CreditCreate` / `CreditResponse` / `CreditStats` Pydantic models |
| `models/transaction.py` | `backend/models/transaction.py` | `TransactionCreate` / `TransactionResponse` Pydantic models |
| `services/carbon_credit_engine.py` | `backend/services/carbon_credit_engine.py` | End-to-end segmentation → biomass → carbon → risk → **credit issuance** pipeline |
| `services/certificate_generator.py` | `backend/services/certificate_generator.py` | Purchase-certificate PDF rendering |
| `create_sample_credits.py` | `backend/create_sample_credits.py` | One-off seed script generating demo `carbon_credits` rows with `status: "listed"` for a marketplace UI; its `SAMPLE_PROJECTS` list is Kenya-region data (Aberdare, Mt Kenya, Kakamega, Mau, Loita, etc.) predating the Rwanda/Bugesera-Rulindo re-scope. Missed by the initial legacy sweep since it lives at the `backend/` root rather than under `routers/`/`services/`/`models/`; relocated here on a later pass for the same reason as everything else in this folder. |

## Status

- **Not imported by `backend/main.py`.** None of these routers are mounted
  on the live FastAPI app as of the re-scope (see `main.py` router list).
- **Import paths are preserved as-is** from their original location (e.g.
  `from models.credit import ...`, `from backend.services.carbon_credit_engine
  import ...`). They were not rewired to the new `legacy/` package path,
  since this code is archived for reference/reuse rather than actively
  maintained inside the capstone app. Re-activating any of these files
  (here or inside the TerraFoma LTD codebase) will require restoring those
  import paths relative to wherever the file is reintroduced.
- The underlying Supabase tables this code depends on (`carbon_credits`,
  `transactions`) are **left in `backend/data/schema.sql` untouched** — no
  destructive schema migration was run. The live capstone app still writes
  interim verification records into `carbon_credits` (see
  `routers/scan.py`, `routers/landowner.py`) pending introduction of the
  proposal's dedicated `Verification` entity; it does not use the
  marketplace listing/sale/settlement fields.

## Re-integrating into TerraFoma LTD

To reuse this code commercially: copy the relevant files back into a
standalone backend, restore their original import roots (`models.*`,
`services.*`, `routers.*` resolved against that project's own `backend/`
root), and reconnect `app.include_router(...)` calls in that project's
`main.py`. Nothing here was deleted or rewritten — only relocated.
