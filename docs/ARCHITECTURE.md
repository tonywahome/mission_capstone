# TerraFoma System Architecture

This document describes the architecture of the re-scoped academic prototype — the locally-calibrated AGB estimation engine, uncertainty-reporting module, and registration/verification dashboard. It does not describe the marketplace/payments architecture of the separate TerraFoma LTD commercial product; that code still exists in this repository under `backend/legacy/` and `frontend/legacy/`, unmodified, and is documented separately in `backend/legacy/README.md` and `frontend/legacy/README.md`. See the top-level `README.md`'s "Legacy Code / TerraFoma LTD" section for why it was kept rather than deleted.

This file replaces an earlier version that described a now-superseded in-memory-database prototype (`InMemoryDB`/`InMemoryTable`, Kenya sample credits, a Random Forest model with R²=0.53) that predates the current Supabase-backed, multi-sensor architecture entirely. None of that content is current and it has been removed rather than carried forward.

---

## Overview

TerraFoma's live system has three components:

1. **Backend API** — FastAPI, backed by Supabase (PostgreSQL + PostGIS), with seven live routers (auth, registration, scan, landowner, notifications, plots, monitoring).
2. **Frontend** — Next.js dashboard for the three roles (Steward, Verifier/Analyst, Research-Administrator) plus a public landing page.
3. **ML pipeline** — a multi-sensor (Sentinel-1 + Sentinel-2 + GEDI) biomass model, served from a pickled artifact at inference time and trained offline by a standalone script.

---

## System Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                         │
│   Landing  │  Login/Signup  │  Steward (register, scan,            │
│            │                │  pending-scans, monitoring)          │
│            │                │  Verifier-Analyst (verification      │
│            │                │  queue)  │  Admin (requests)         │
│                       │  API Client (lib/api.ts)  │                │
└───────────────────────┼──────────────────────────────────────────────┘
                         │  HTTPS / JSON
┌───────────────────────▼──────────────────────────────────────────────┐
│                          Backend (FastAPI)                           │
│  routers/  auth · registration · scan · landowner ·                  │
│            notifications · plots · monitoring                        │
│                         │                                            │
│  services/ biomass_estimator · gee_feature_extractor ·                │
│            gee_biomass_baseline · carbon_calculator · risk_scorer ·   │
│            location_service · privacy · experiment_tracker            │
│                         │                                            │
│  ml/models/biomass_model_v1.pkl  (loaded once, cached at module load) │
└───────────────────────┬───────────────────────────────────────────────┘
                         │
        ┌────────────────┼─────────────────┬───────────────────┐
        ▼                ▼                 ▼                   ▼
   Supabase        Google Earth        NASA GEDI          Mapbox GL
 (PostgreSQL +       Engine          (via GEE / direct       (frontend
   PostGIS)      (Sentinel-1/2)         L4A/L4B)              tiles)
```

---

## Backend Components

### Routers (`backend/routers/`) — live, registered in `main.py`

| Router | Responsibility |
|---|---|
| `auth.py` | Signup/login/logout/session lookup. SHA-256 password hashing, `sessions` table for tokens. Transparently remaps legacy role strings (`landowner`/`business`/`buyer`/`admin`) to the proposal's roles (`steward`/`verifier_analyst`/`research_admin`) in both directions. |
| `registration.py` | Steward-submitted plot registration requests. |
| `scan.py` | Triggers a satellite scan for a plot: feature extraction → biomass prediction (with uncertainty) → carbon calculation → risk/integrity scoring → an interim verification record. |
| `landowner.py` | `/pending-scans` (steward-scoped), `/verification-queue` (verifier_analyst, district-scoped, fails open), `/approve-listing`, `/my-credits`. |
| `notifications.py` | In-app notification center: list, unread count, mark-read. |
| `plots.py` | Land plot CRUD and GeoJSON export. |
| `monitoring.py` | Weekly NDVI/biomass health checks and change detection per plot. |

`backend/legacy/routers/` (`credits.py`, `transactions.py`, `certificates.py`, `dashboard.py`, `plots_enhanced.py`) exist on disk but are **not imported by `main.py`** — any request to their endpoints (e.g. `/api/credits/stats`) returns 404. `frontend/src/lib/api.ts` retains client wrappers for several of these (`getCredits`, `getCreditStats`, `createTransaction`, `getCertificateURL`, etc.); they are dead code as of this re-scope and the one live caller (`StatsBar.tsx`) has been switched to static research-context copy instead.

### Services (`backend/services/`)

- **`biomass_estimator.py`** — loads `ml/models/biomass_model_v1.pkl` once at import time (module-level cache, not per-request), and `predict_biomass_from_features()` returns a dict with `biomass_mean`, `biomass_lower_90`, `biomass_upper_90`, and `uncertainty_pct` — i.e. the uncertainty-reporting module is implemented as an extension of the point-estimate prediction call, not a separate endpoint.
- **`gee_feature_extractor.py`** — `extract_sentinel_features()` queries Sentinel-2 (and, where available, Sentinel-1 SAR and GEDI) via Earth Engine for a given plot geometry; falls back to `_mock_features()` when GEE is unreachable so the scan flow degrades gracefully rather than failing closed on every demo run.
- **`gee_biomass_baseline.py`** — GEDI L4B global baseline lookup (Verra/Gold Standard-accepted), with a Rwanda elevation-based fallback.
- **`carbon_calculator.py`**, **`risk_scorer.py`** — carbon-value and risk/integrity scoring, retained from the original pipeline; pricing output is computed but not surfaced as a marketplace price under the current scope (the interim verification record stores it for schema continuity only).
- **`location_service.py`** — derives a human-readable region/district from submitted geometry.
- **`privacy.py`** — Section 3.6 safeguards 1 (coordinate rounding, fail-closed) and 2 (role resolution feeding district-scoped access). See "Security" below.
- **`experiment_tracker.py`** — Section 3.7: flat JSON/CSV run records under `backend/ml/experiment_runs/`, written by `train_biomass_model.py`.
- **`mock_data.py`** — `REGION_ELEVATION` terrain priors for Bugesera and Rulindo, used by demo/fallback feature generation.

### Models (`backend/models/`)

- **`user.py`** — `VALID_ROLES = ("steward", "verifier_analyst", "research_admin")`; `precise_location_consent: bool` on both create and response schemas (Section 3.6 safeguard 3).
- **`land_plot.py`** — `IN_SCOPE_DISTRICTS = ("Bugesera", "Rulindo")`, `IN_SCOPE_LAND_USE = ("agroforestry", "grassland")`; `ALL_LAND_USE` retains `forest`/`cropland`/`wetland` for backward compatibility with demo data and legacy rows. `district` is a field distinct from the free-text `region`.
- **`risk.py`** — `ScanRequest`/`ScanResponse` schemas used by `scan.py`.

---

## Data Flow: Scan and Interim Verification

This is the one true end-to-end pipeline in the live system (`backend/routers/scan.py`):

```
1.  POST /api/scan  { plot_id?, owner_id, geometry, land_use }
2.  location_service.get_location_from_geometry()       → district/region string
3.  gee_feature_extractor.extract_sentinel_features()    → Sentinel-2 (+ S1/GEDI where available)
4.  biomass_estimator.predict_biomass_from_features()    → biomass_mean, 90% PI bounds, uncertainty_pct
5.  biomass_estimator.biomass_to_tco2e()                 → AGB × 0.47 × 3.667 (IPCC)
6.  risk_scorer.calculate_risk_score()                   → drought/wildfire/composite risk
7.  biomass_estimator.calculate_integrity_score()         → MRV-quality composite score
8.  carbon_calculator.calculate_credit_price()            → computed, stored, not marketplace-surfaced
9.  INSERT scan_results   (includes biomass_lower_90/upper_90/uncertainty_pct, sensors_used flags)
10. INSERT carbon_credits status='pending_approval'       → interim verification record, NOT a listing
```

Step 10 is explicitly an interim measure: the code comment in `scan.py` notes that this supersedes once the proposal's dedicated `verifications` table (added as a schema-only scaffold by `migration_capstone_rescope.sql`) is actually wired up. No credit is issued, listed, or matched to a buyer anywhere in this flow — that logic exists only in `backend/legacy/services/carbon_credit_engine.py`, which is not called from any live router.

### Verification Queue Flow

```
1.  GET /api/landowner/verification-queue?verifier_id=...
2.  Look up verifier's users.assigned_district
3.  Query carbon_credits/land_plots, filtered to that district if set,
    else ALL districts (fail-open — see Security)
4.  Verifier-Analyst calls POST /api/landowner/approve-listing to confirm
    or flag a record
```

---

## Database

Core tables from `backend/data/schema.sql`: `users`, `land_plots`, `scan_results`, `carbon_credits`, `risk_assessments`, `transactions`, `audit_log`, `industrial_profiles`. Additional tables/columns added by migrations: `registration_requests`, `notifications`, `sessions` (auth), and — additively, via `migration_capstone_rescope.sql` — `users.assigned_district`, `users.precise_location_consent`, `users.data_retention_until`, `land_plots.district`, a widened `users.role` and `carbon_credits.status` CHECK constraint, and a schema-only `verifications` table (Section 3.4 entity, not yet written to).

Every change in `migration_capstone_rescope.sql` is additive: widened CHECK constraints retain every legacy value, new columns are nullable or default to the least-permissive value, and `verifications` is `CREATE TABLE IF NOT EXISTS`. This means `backend/legacy/` code and any pre-existing rows continue to validate against the schema unchanged — there is no destructive migration in this repository.

---

## Security

### Role-Based Access (Section 3.6 safeguards 1 & 2)

`backend/services/privacy.py` is the single module implementing both of the proposal's data-minimization safeguards, and it deliberately implements them with **opposite fallback directions**:

- **Coordinate rounding (safeguard 1, fail-closed).** `round_coordinate()` / `round_geojson_geometry()` round to 3 decimal places (~111 m) for every role except `research_admin`. Any error in resolving the caller's role or in the rounding logic itself results in rounded (less informative) output, never a silent pass-through of full-precision coordinates.
- **District-scoped verification queue (safeguard 2, fail-open).** The `/api/landowner/verification-queue` filter narrows by `assigned_district` when set, but falls back to an unscoped (all-district) queue when the column is absent or null. This is intentional: under-scoping an audit queue is a workflow gap, not a confidentiality leak, so the fallback favors usability over restriction — the inverse of the coordinate-rounding fallback.

There is no global authentication middleware. `resolve_role()` in `privacy.py` only takes effect where a router explicitly accepts and passes a `token` parameter; a request that omits a token is treated as the least-privileged caller by default. This makes the rounding safeguard fail closed in practice without requiring every router to be individually audited for a missing check — but it does mean access control is opt-in per-endpoint rather than enforced globally, which is recorded as a known limitation in the top-level README.

### CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,              # from settings.cors_origins (comma-separated env var)
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Input Validation

All request/response bodies are Pydantic models (`models/user.py`, `models/land_plot.py`, `models/risk.py`), giving type and bounds validation at the FastAPI layer before any handler logic runs.

---

## Resilience Patterns

- **Remap-and-fallback (roles/statuses/columns).** New role names, status values, and Section 3.6 columns are tried first against the live database; on failure (e.g. the migration hasn't been applied yet), the code retries with the pre-rescope legacy values and logs a warning pointing at `migration_capstone_rescope.sql`. See `auth.py`'s `signup()` for the clearest example — it retries twice, first dropping `precise_location_consent`, then falling back to the legacy role string, before giving up.
- **GEE feature extraction fallback.** `gee_feature_extractor.py` falls back to `_mock_features()` when Earth Engine is unreachable, so a scan request degrades to illustrative output rather than hard-failing — useful for demos, but means a 200 response doesn't guarantee real satellite data was used; `sensors_used` flags in the stored `scan_results` row record which sensors actually contributed.
- **GEDI L4B baseline fallback.** `gee_biomass_baseline.py` falls back to a Rwanda elevation-based allometry estimate when the L4B lookup is unavailable.

---

## Deployment

```bash
# Backend (dev)
uvicorn main:app --reload --port 8002
# Backend (prod)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8002

# Frontend (dev)
npm run dev
# Frontend (prod)
npm run build && npm start
```

Environment variables are documented in the top-level `README.md`'s Getting Started section; see also `render.yaml` at the repository root for the configured Render deployment target.

---

## Known Architectural Limitations

See the top-level `README.md`'s "Known Limitations" section for the full list (model geography mismatch, no global auth middleware, unenforced retention period, schema-only `verifications` table, dead legacy API client functions). Two additional implementation details worth noting for anyone extending this codebase:

- **No automated tests exist** for the live routers or services as of this re-scope — `pytest tests/` referenced in earlier documentation does not correspond to a populated `tests/` directory in this repository.
- **The ML model is loaded once per process**, not per request — restarting the backend is currently the only way to pick up a newly retrained `biomass_model_v1.pkl` without a dedicated reload endpoint.
