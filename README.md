# TerraFoma — Research Prototype

**A Locally-Calibrated Machine-Learning Architecture for Above-Ground Biomass Estimation and Auditable Monitoring in Rwanda**

TerraFoma is the software artifact for a BSc Software Engineering capstone at African Leadership University. It fuses Sentinel-1 radar, Sentinel-2 multispectral imagery, and NASA GEDI spaceborne LiDAR into a locally-calibrated machine-learning model for above-ground biomass (AGB) estimation, paired with an uncertainty-reporting module and a lightweight dashboard for project registration, field-data upload, and audit-trail visualization.

> **Author:** Wahome A. Wambugu | **Supervisor:** Emmanuel Adjei | **Institution:** African Leadership University, Kigali, Rwanda | **Repository:** [github.com/tonywahome/mission_capstone](https://github.com/tonywahome/mission_capstone)

---

## Project Scope

This repository was re-scoped in June 2026 to align with the revised capstone research proposal. The sections below define what this academic prototype does and does not cover — read this before the rest of the document, since several features described later (carbon-credit issuance, marketplace listing, payments) are explicitly **out of scope** and exist only as preserved legacy code for a separate commercial product, TerraFoma LTD.

### In Scope

- A locally-calibrated AGB estimation model fusing Sentinel-1, Sentinel-2, and GEDI LiDAR.
- Field-plot validation in **Bugesera** (savanna/grassland, Eastern Province) and **Rulindo** (agroforestry, Northern Province) districts of Rwanda.
- An uncertainty-reporting module (prediction intervals alongside point estimates).
- A web dashboard for project (plot) registration, field/scan data upload, and audit-trail visualization for a verification workflow.
- Three roles: **Land Steward** (registers plots, submits field/scan data), **Verifier/Analyst** (reviews submissions, confirms or flags them), and **Research-Administrator** (backend tier with exclusive full-precision data access).
- Ethical safeguards per proposal Section 3.6: coordinate rounding, role-/district-scoped access, separate precise-location consent, and a defined data-retention period.
- Structured experiment tracking (Section 3.7) for every model training run.

### Explicitly Out of Scope

Soil organic carbon estimation, biodiversity co-benefits, a secondary carbon-credit market, blockchain settlement, automated carbon-credit issuance, buyer matching/settlement, and full registry integration (Verra/Gold Standard) are **not** part of this capstone. The original codebase included working implementations of several of these features; rather than delete them, they have been moved intact into `backend/legacy/` and `frontend/legacy/` for the separate TerraFoma LTD commercial venture. See [Legacy Code / TerraFoma LTD](#legacy-code--terrafoma-ltd) below — that code is not imported by the live application and should not be conflated with this academic prototype.

---

## Research Context

Carbon markets have become a central instrument for combating climate change, yet fewer than 16% of issued credits have been estimated to represent real emission reductions (Probst et al., 2024). This integrity crisis is most acute in Sub-Saharan Africa, which retired only 22 million tonnes of CO₂e in 2021 against a feasible target of 300 million by 2030 (ACMI, 2022). A principal technical driver is measurement error: global biomass products carry up to 79.5% RMSE and a 36% negative bias over African savannas (Naidoo et al., 2024), while per-farmer monitoring costs of USD 150–200 exceed the USD 5–45 annual carbon revenue available to smallholders (CPI, 2024).

TerraFoma proposes that locally calibrated machine-learning models fusing Sentinel-1 radar, Sentinel-2 multispectral imagery, and spaceborne LiDAR can reduce biomass estimation error by at least **40% relative to global products**. The revised proposal validates this over a purposive field-plot sample in **Bugesera** (savanna/grassland) and **Rulindo** (agroforestry) districts, following a **Design Science Research (DSR)** methodology with five evaluation criteria: RMSE against GEDI per land-use stratum, mean bias, uncertainty/prediction-interval coverage, dashboard usability, and expert review of dMRV traceability.

### Research Objectives

1. **Understand & Review** — Review at least 25 indexed sources and conduct semi-structured interviews with a minimum of 15 stakeholders to collect requirements and field reference data.
2. **Develop** — Design and build a prototype fusing Sentinel-1, Sentinel-2, and GEDI LiDAR with locally calibrated ML for AGB estimation, an uncertainty-reporting module, and an auditable registration/upload/verification dashboard.
3. **Verify** — Validate the prototype against field measurements and incumbent global products (targeting ≥40% RMSE reduction), and assess the dashboard's usability and audit-trail traceability through expert review.

### Hypothesis

Local calibration of machine-learning biomass models against Rwandan field measurements will reduce RMSE by at least 40% relative to the global GEDI above-ground biomass product (baseline RMSE: 79.5%, negative bias: 36% — Naidoo et al., 2024).

---

## Roles

The application implements three roles per the proposal's Section 3.4 class diagram (`backend/models/user.py`, `VALID_ROLES`):

| Role               | Was (pre-rescope)    | Responsibilities                                                                                                          |
| ------------------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `steward`          | `landowner`          | Registers plots, draws boundaries, submits field/scan data for review.                                                    |
| `verifier_analyst` | `business` / `buyer` | Reviews submitted scans/field data via a district-scoped audit queue; confirms or flags records for the audit trail.      |
| `research_admin`   | `admin`              | Backend tier with exclusive access to full-precision (unrounded) coordinate data, per the Section 3.6 ethical safeguards. |

Legacy role strings (`landowner`, `buyer`, `admin`, `business`) are still accepted at the database layer — `backend/data/migration_capstone_rescope.sql` widens the `users.role` CHECK constraint additively rather than renaming values, and `backend/routers/auth.py` transparently remaps between old and new names in both directions. This keeps any pre-existing seed data or in-flight sessions valid through the re-scope.

---

## Validation Geography and Model Status

The revised proposal's active field-validation sample is **Bugesera** (savanna/grassland) and **Rulindo** (agroforestry) — not Kigali City, which was the second district in an earlier draft of the proposal.

**Important caveat on the shipped model artifact.** The trained model currently in this repository, `backend/ml/models/biomass_model_v1.pkl`, was trained and benchmarked on 1,990 samples drawn from **Bugesera and Kigali City** (see the benchmark table below) — i.e. the _pre-revision_ validation geography. It has not been retrained on Rulindo data. This artifact is retained and flagged as **v1 / legacy, pending retrain** rather than deleted or relabelled, for two reasons: its benchmark numbers are real, measured results worth preserving as a baseline, and no new Rulindo field/training data has been fabricated to replace it — collecting and labelling that data is itself part of the capstone's remaining fieldwork (see [Roadmap](#roadmap)). Demo/illustrative data added elsewhere in this repository for Bugesera and Rulindo (`backend/data/sample_plots.geojson`, `backend/data/sample_data.sql`) populates the dashboard's map and audit views only — it was not used to train or validate this or any model.

Everywhere the codebase needs a terrain/district prior for the two active districts (`backend/services/mock_data.py`'s `REGION_ELEVATION`) or needs to constrain which districts/land-uses count as "in scope" (`backend/models/land_plot.py`'s `IN_SCOPE_DISTRICTS = ("Bugesera", "Rulindo")` and `IN_SCOPE_LAND_USE = ("agroforestry", "grassland")`), it has been updated to reflect this. Forest, cropland, and wetland remain valid `land_use` values for backward compatibility but fall outside the active validation strata.

---

## Machine Learning Pipeline

`backend/ml/train_biomass_model.py` implements the architecture specified in proposal Section 3.3.3: a multi-model benchmark (Random Forest, XGBoost, SVR, and a CNN/MLP when PyTorch is available) selected by spatial-block cross-validation RMSE, a log1p target transform (AGB is log-normal), and SHAP/permutation feature importance for auditor explainability. XGBoost is optional at the dependency level — the script falls back to scikit-learn's `GradientBoostingRegressor` if `xgboost` isn't installed, since it is a standalone training script with its own dependency footprint, separate from the FastAPI backend's `requirements.txt` (which only needs `joblib` to load the pickled artifact at inference time, not the libraries used to produce it).

### Multi-Model Benchmark Results (5-Fold Spatial Block CV)

These are the measured results behind `biomass_model_v1.pkl`, trained on **1,990 samples** (Bugesera & Kigali City, 29.5–30.9°E, 1.05–2.85°S) — see the legacy-model caveat above. Spatial blocks: 0.5° grid with GroupKFold to prevent autocorrelation inflating the score. Target: log1p(AGBD t/ha); metrics reported in original units.

| Model                  | CV R²               | CV RMSE (t/ha) | CV MAE (t/ha) | Bias (t/ha)                              |
| ---------------------- | ------------------- | -------------- | ------------- | ---------------------------------------- |
| **XGBoost** (selected) | **0.8879 ± 0.0067** | **20.0 ± 0.5** | **16.0**      | **−1.0**                                 |
| Random Forest          | 0.8827 ± 0.0079     | 20.5 ± 0.6     | 16.3          | −1.4                                     |
| SVR (RBF)              | 0.8541 ± 0.0055     | 22.9 ± 0.7     | 17.9          | −3.6                                     |
| CNN (MLP)              | —                   | —              | —             | (PyTorch not installed at training time) |

Full-dataset train: R²=0.9917, RMSE=5.5 t/ha. Spatial CV (the honest, generalization-relevant figure): R²=0.8879, RMSE=20.0 t/ha. 90% prediction-interval coverage = 100% (mean PI width: 65.9 t/ha). Against the global GEDI product's 79.5% RMSE over African savannas (Naidoo et al., 2024), this is a **≥74% reduction** — exceeding the ≥40% hypothesis target, on the Bugesera/Kigali City sample. Whether this holds on Rulindo's agroforestry mosaic is an open question pending retraining.

### Top Feature Importances (Permutation)

| Rank | Feature                        | Importance | Sensor     |
| ---- | ------------------------------ | ---------- | ---------- |
| 1    | rh98 (canopy height, 98th pct) | 0.341      | GEDI LiDAR |
| 2    | cover (canopy cover fraction)  | 0.155      | GEDI LiDAR |
| 3    | ndvi                           | 0.142      | Sentinel-2 |
| 4    | savi                           | 0.054      | Sentinel-2 |
| 5    | vh (SAR backscatter)           | 0.041      | Sentinel-1 |

### Input Features (20 total)

Sentinel-2 spectral bands (6: blue, green, red, nir, swir1, swir2); vegetation indices (5: NDVI, EVI, SAVI, NDMI, NBR); Sentinel-1 SAR (3: VV, VH, VH–VV difference, C-band); GEDI LiDAR (4: rh50, rh75, rh98, cover fraction); terrain (2: elevation, slope).

### Supporting Modules

- `backend/services/gee_biomass_baseline.py` — GEDI L4B wall-to-wall AGBD baseline lookup (Verra/Gold Standard-accepted reference), with a Rwanda elevation-based fallback when Earth Engine is unreachable.
- `backend/services/experiment_tracker.py` — Section 3.7 experiment tracking: every training run is logged as a flat JSON/CSV record under `backend/ml/experiment_runs/` (dataset version, feature stack, hyperparameters, random seed, spatial-block split IDs, evaluation metrics, output artifact path). Filesystem-based by design, so the standalone training script doesn't need live database credentials.
- `backend/ml/collect_sentinel_data.py`, `collect_gedi_data.py`, `gee_export_rwanda.py` — data collection scripts; `gee_export_rwanda.py` already targets Rwanda as its area of interest, and is the natural starting point for collecting the Rulindo retraining sample.
- `backend/ml/monitor_biomass.py` — weekly NDVI/biomass health-check utilities backing the `/api/monitoring` endpoints below.

---

## Ethical Safeguards (Proposal Section 3.6)

Four safeguards are specified in the proposal; their implementation status:

1. **Coordinate rounding.** `backend/services/privacy.py` rounds stored coordinates to 3 decimal places (~111 m at the equator) for any role other than `research_admin`. This is a **fail-closed** design: on any error, it rounds rather than returning unrounded data.
2. **Role-/district-scoped access.** `users.assigned_district` scopes a `verifier_analyst`'s audit queue (`GET /api/landowner/verification-queue`) to one district. This is deliberately **fail-open/permissive** — if the column doesn't exist yet or is unset, the queue falls back to showing all districts rather than none, since under-scoping an audit queue is a usability gap, not a confidentiality leak (the opposite fallback direction from safeguard 1, and documented as such in both modules to avoid conflating the two).
3. **Separate precise-location consent.** `precise_location_consent` is a distinct, explicit boolean on `SignupRequest`/`users`, defaulting to `False`. Consenting to an account does not imply consenting to full-precision coordinate storage.
4. **Defined retention period.** `users.data_retention_until` exists as a column (added by `backend/data/migration_capstone_rescope.sql`) but is **not yet enforced** — no scheduled job purges or anonymizes data once this date passes. This is a known limitation, not a completed safeguard.

`backend/services/privacy.py` documents a further limitation directly in its docstring: there is no token/header-based auth middleware. `resolve_role` only restricts data when a router explicitly accepts a `token` parameter and calls it; omitting a token defaults to the least-privileged (rounded) behavior, so the fail-closed design holds even though enforcement is opt-in per router rather than global.

---

## Architecture

### Tech Stack

- **Backend:** FastAPI 0.115 (Python), Pydantic, Supabase (PostgreSQL + PostGIS)
- **Frontend:** Next.js 14.2, React 18, TypeScript 5.7, Tailwind CSS, Mapbox GL JS + Mapbox Draw
- **ML:** scikit-learn 1.6, XGBoost (optional, training-time only), joblib
- **Geospatial:** Google Earth Engine (Sentinel-1, Sentinel-2), NASA GEDI L4A/L4B
- **Auth:** Custom session-token system (SHA-256 password hashing, `sessions` table) — see [Known Limitations](#known-limitations)

### System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                       │
│   Public Landing │ Steward Dashboard │ Verifier Queue │ Admin │
│         └──────────────┬── API Client (lib/api.ts) ──┘        │
└────────────────────────┼───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                       Backend (FastAPI)                          │
│  Live routers: auth · registration · scan · landowner ·          │
│                notifications · plots · monitoring                │
│         │                                                         │
│  Services: biomass_estimator · gee_feature_extractor ·            │
│            gee_biomass_baseline · carbon_calculator ·             │
│            risk_scorer · location_service · privacy ·             │
│            experiment_tracker                                     │
│         │                                                         │
│  ML artifact: biomass_model_v1.pkl  (XGBoost, CV R²=0.8879 —      │
│               flagged legacy / pending Rulindo retrain)           │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  Supabase (PostgreSQL + PostGIS)  │  Google Earth Engine  │ Mapbox │
└────────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
mission_capstone/
├── backend/
│   ├── main.py                     # FastAPI entry — registers only the live routers below
│   ├── config.py / database.py
│   ├── routers/                    # LIVE
│   │   ├── auth.py                 # Signup/login/session (steward, verifier_analyst, research_admin)
│   │   ├── registration.py         # Plot registration requests
│   │   ├── scan.py                 # AI satellite scan trigger + lookup
│   │   ├── landowner.py            # Pending-scans, verification-queue, approve-listing, my-credits
│   │   ├── notifications.py        # Notification center
│   │   ├── plots.py                # Land plot CRUD + GeoJSON
│   │   └── monitoring.py           # Weekly biomass/NDVI health checks, change detection
│   ├── services/                   # LIVE
│   │   ├── biomass_estimator.py, carbon_calculator.py, risk_scorer.py
│   │   ├── gee_feature_extractor.py, gee_biomass_baseline.py, gee_init.py
│   │   ├── location_service.py, mock_data.py
│   │   ├── privacy.py              # Section 3.6 safeguards 1 & 2
│   │   └── experiment_tracker.py   # Section 3.7
│   ├── models/                     # user.py, land_plot.py, risk.py
│   ├── ml/                         # Training pipeline (see ML Pipeline section)
│   ├── data/                       # schema.sql + migrations + sample_data.sql/.geojson
│   ├── legacy/                     # NOT imported by main.py — see Legacy Code section
│   └── requirements.txt
│
├── frontend/
│   ├── src/app/                    # LIVE: landing page, login, signup, request-registration,
│   │   │                           #       scan, landowner/ (+ monitoring, pending-scans),
│   │   │                           #       admin/requests
│   │   ├── components/             # Navbar, ProtectedRoute, MapView, RiskGauge, StatsBar, CreditCard
│   │   ├── contexts/AuthContext.tsx
│   │   └── lib/api.ts, types.ts
│   └── legacy/                     # NOT routed from src/app — see Legacy Code section
│
├── docs/                            # ARCHITECTURE.md, SETUP.md, SUPABASE_SETUP.md, SUPABASE_QUICK_START.md
├── notebooks/integrity_score_training.ipynb
└── README.md                        # This file
```

---

## API Reference (Live Endpoints)

Only routers imported by `backend/main.py` are reachable; everything below is live. (Endpoints under `backend/legacy/routers/` — credits, transactions, certificates, dashboard, plots_enhanced — are **not** registered and will 404. See [Legacy Code](#legacy-code--terrafoma-ltd).)

```
Auth            POST /api/auth/signup | login | logout
                GET  /api/auth/me | user-by-email

Registration    POST /api/registration/request
                GET  /api/registration/requests

Scan            POST /api/scan
                GET  /api/scan/{scan_id}

Landowner /     GET  /api/landowner/pending-scans      (steward-scoped)
Verification    GET  /api/landowner/verification-queue  (verifier_analyst, district-scoped)
                POST /api/landowner/approve-listing
                GET  /api/landowner/my-credits

Notifications   GET  /api/notifications | /me | /unread-count
                PATCH /api/notifications/{id}/mark-read
                POST /api/notifications/mark-all-read

Plots           GET  /api/plots | /geojson | /owner/{owner_id} | /{plot_id}
                POST /api/plots
                DELETE /api/plots/{plot_id}

Monitoring      GET  /api/monitoring/plots/{plot_id}/latest | history | change-detection
                GET  /api/monitoring/summary
                POST /api/monitoring/plots/{plot_id}/run
                POST /api/monitoring/run-all
```

31 endpoints across 7 routers. Interactive OpenAPI docs are auto-generated at `/docs` when the backend is running.

---

## Getting Started

### Prerequisites

Python 3.11+, Node.js 18+, a Supabase project, a Google Earth Engine account, and a Mapbox API key.

### 1. Database

Run, in order: `backend/data/schema.sql`, `migration_add_auth.sql`, `migration_approval_workflow.sql`, `migration_capstone_rescope.sql` (additive-only; adds the re-scoped roles, districts, and Section 3.6 safeguard columns without touching legacy data), then `migration_canonical_entities.sql` (additive-only; adds four read-only views — `project`, `steward`, `biomass_model`, `verification` — mapping the Section 3.4 class diagram's exact entity names onto the tables above; see [Canonical Data Model](#canonical-data-model-section-34)). Optionally load `backend/data/sample_data.sql` and `sample_plots.geojson` afterward — these seed **illustrative, non-field-collected** Bugesera/Rulindo demo rows for the map and audit-trail views, not training data.

### 2. Backend

```bash
cd backend
python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # set SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
                          # EARTHENGINE_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS
earthengine authenticate
uvicorn main:app --reload --port 8002
```

Backend: `http://localhost:8002` · API docs: `http://localhost:8002/docs`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL, NEXT_PUBLIC_MAPBOX_TOKEN
npm run dev
```

Frontend: `http://localhost:3001`

### Test Accounts

`sample_data.sql` seeds one illustrative steward profile (`steward.pilot@terrafoma-capstone.local`) to populate dashboard views, but it has no usable password — `backend/routers/auth.py` only mints a `password_hash` through the `/api/auth/signup` flow, and the seed `INSERT` doesn't set one. To exercise the live workflow, sign up through the frontend's `/signup` page with role `steward`, `verifier_analyst`, or `research_admin`; legacy role strings (`landowner`, `business`, `admin`) are also accepted and remapped automatically.

---

## Development

```bash
# Backend
cd backend && uvicorn main:app --reload --port 8002          # dev
cd backend && gunicorn main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8002  # prod

# Frontend
cd frontend && npm run dev      # dev
cd frontend && npm run build && npm start   # prod
```

Linting: `black .` / `isort .` / `flake8 .` / `mypy .` (backend); `npm run lint` / `npm run type-check` (frontend).

---

## Legacy Code / TerraFoma LTD

This academic capstone is **distinct from TerraFoma LTD**, a separate commercial venture operating in Rwanda. The original codebase included a working carbon-credit marketplace (listing, pricing tiers, Polar.sh payments, certificate generation, buyer dashboards) that is out of scope for this capstone but represents real, reusable work for that commercial product. Rather than delete it, it was moved intact, unmodified, into:

- `backend/legacy/` — `routers/{credits,transactions,certificates,dashboard,plots_enhanced}.py`, `models/{credit,transaction}.py`, `services/{carbon_credit_engine,certificate_generator}.py`. See `backend/legacy/README.md` for the full router-by-router breakdown and re-integration notes.
- `frontend/legacy/` — `app/{marketplace,registry,certificate/[id],purchase-success,dashboard}/`, `app/api/{checkout,confirm-payment,webhooks/polar}/`, `app/admin/dashboard/`. See `frontend/legacy/README.md`.

None of this is imported by `backend/main.py` or routed from `frontend/src/app/`. The underlying Supabase tables (`carbon_credits`, `transactions`) remain in `schema.sql` unchanged — no destructive migration was run — and the live application still writes interim verification outcomes onto `carbon_credits.status` pending a dedicated `verifications` table (added as a schema-only scaffold by `migration_capstone_rescope.sql`, not yet wired up). Do not extend this legacy code as part of capstone work; do not present capstone evaluation results as validating TerraFoma LTD's commercial product, or vice versa.

---

## Canonical Data Model (Section 3.4)

The proposal's Section 3.4 class diagram defines exactly four domain entities: **Project**, **Steward**, **BiomassModel**, **Verification**. The physical schema (`schema.sql`) predates the re-scope and is organized around marketplace-era tables instead — `land_plots`, `users`, `scan_results`, `carbon_credits`/`verifications`. Renaming or collapsing those tables outright would violate this project's additive-only migration philosophy (see `migration_capstone_rescope.sql`'s header) and could break `backend/legacy/`/`frontend/legacy/` code still serving TerraFoma LTD.

Instead, `backend/data/migration_canonical_entities.sql` adds four read-only SQL views named exactly after the proposal's entities, each re-projecting and renaming columns from an existing table without altering anything underneath it:

| Canonical view  | Backing table                                            | Notable renames                                                                                                                                                                                                                 |
| --------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `project`       | `land_plots`                                             | `owner_id` → `steward_id`                                                                                                                                                                                                       |
| `steward`       | `users` (filtered to `role IN ('steward', 'landowner')`) | —                                                                                                                                                                                                                               |
| `biomass_model` | `scan_results`                                           | `plot_id` → `project_id`, `estimated_biomass` → `agb_estimate_t_ha`, `estimated_tco2e` → `carbon_stock_tco2e`, `created_at` → `run_at`; adds `uncertainty_pct` (currently `NULL` — see [Known Limitations](#known-limitations)) |
| `verification`  | `verifications`                                          | — (exact alias; matches the table added by `migration_capstone_rescope.sql`)                                                                                                                                                    |

These views are additive and read-only: `CREATE OR REPLACE VIEW` never touches base tables, no application code currently queries them, and they can be re-run safely. They exist so the database can be queried using the proposal's exact vocabulary (e.g. for the evaluation write-up or a future ORM layer) without a destructive rename of code that `backend/routers/*.py` already depends on.

---

## Known Limitations

- **Model geography mismatch.** `biomass_model_v1.pkl` is trained on Bugesera/Kigali City, not the current Bugesera/Rulindo validation sample. See [Validation Geography and Model Status](#validation-geography-and-model-status).
- **No auth middleware.** Role/data-access restrictions (`services/privacy.py`) only apply where a router explicitly checks a `token`; there is no global session-verification layer.
- **Retention period not enforced.** `users.data_retention_until` is a column with no scheduled purge job.
- **`verifications` table is schema-only.** Verification outcomes are still recorded on `carbon_credits`, not the dedicated entity from the Section 3.4 class diagram. The `verification` canonical view (see [Canonical Data Model](#canonical-data-model-section-34)) reads from `verifications`, so it will stay empty until that write-path migration happens.
- **`biomass_model.uncertainty_pct` is NULL for every row.** `scan_results` has no per-scan prediction-interval/confidence-bound column yet, so the canonical `biomass_model` view exposes an honest `NULL` rather than a fabricated uncertainty figure. Populate this once the retrained pipeline produces a real per-scan uncertainty estimate.
- **XGBoost is optional.** `backend/requirements.txt` does not pin `xgboost` — it's only needed to reproduce `train_biomass_model.py`'s training run, not to serve the already-trained artifact. Install it manually (`pip install xgboost`) if retraining.

---

## Roadmap

This is an academic capstone roadmap, not a commercial product roadmap — items like marketplace expansion, blockchain settlement, or registry integration are deliberately absent here; see [Legacy Code / TerraFoma LTD](#legacy-code--terrafoma-ltd) for that line of work.

- **Field data collection** — Gather GEDI-validated field plots in Rulindo (agroforestry) to complement the existing Bugesera-weighted sample.
- **Retrain on Bugesera + Rulindo** — Re-run `train_biomass_model.py` against the combined sample once Rulindo data is collected; supersede `biomass_model_v1.pkl`.
- **Per-stratum evaluation** — Report RMSE/bias separately for the grassland/savanna (Bugesera) and agroforestry (Rulindo) strata, per the proposal's evaluation criteria.
- **Retention enforcement** — Implement the scheduled purge/anonymization job for `data_retention_until`.
- **Verification entity write-path migration** — Move verification _writes_ from `carbon_credits.status` onto the dedicated `verifications` table (the `verification` canonical view already exposes it for reads; see [Canonical Data Model](#canonical-data-model-section-34)).
- **Real per-scan uncertainty** — Extend the retrained biomass pipeline to emit a prediction interval per scan, populating `biomass_model.uncertainty_pct` (currently an honest `NULL` placeholder).
- **Expert review** — dMRV traceability and dashboard usability review with domain experts, per the DSR evaluation plan.

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture detail
- [docs/SETUP.md](docs/SETUP.md), [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md), [docs/SUPABASE_QUICK_START.md](docs/SUPABASE_QUICK_START.md)
- [backend/legacy/README.md](backend/legacy/README.md), [frontend/legacy/README.md](frontend/legacy/README.md)
- [backend/ml/README.md](backend/ml/README.md) — data collection & training pipeline

---

## Acknowledgments and References

**Data & infrastructure:** Google Earth Engine, NASA GEDI, ESA Sentinel-1/Sentinel-2, Mapbox, Supabase.

**Scientific foundation:** IPCC carbon accounting guidelines; UNFCCC/Paris Agreement Article 6; Verra VCS; FAO Global Forest Resources; Africa Carbon Markets Initiative (ACMI); ICVCM Core Carbon Principles.

**Key references:** Probst et al. (2024) — carbon credit integrity synthesis; Naidoo et al. (2024) — GEDI biomass validation over Southern African savannas; West et al. (2023) — REDD+ effectiveness via synthetic-control methods; Duncanson et al. (2022) — GEDI L4A AGB algorithm; CPI (2024) — smallholder carbon finance cost structure.

---

## Author and Contact

**Wahome A. Wambugu** — BSc Software Engineering, African Leadership University, Kigali, Rwanda
GitHub: [@tonywahome](https://github.com/tonywahome) · Email: a.wambugu@alustudent.com

This project is an academic capstone submission. All rights reserved; for licensing inquiries relating to the separate TerraFoma LTD commercial product, contact the maintainer directly.
