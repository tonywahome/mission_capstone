# TerraFoma — Research Prototype

**A Locally-Calibrated Machine-Learning Architecture for Above-Ground Biomass Estimation and Auditable Monitoring in Rwanda**

TerraFoma is the software artifact for a BSc Software Engineering capstone at African Leadership University. It fuses Sentinel-1 radar, Sentinel-2 multispectral imagery, and NASA GEDI spaceborne LiDAR into a locally-calibrated machine-learning model for above-ground biomass (AGB) estimation, paired with an uncertainty-reporting module and a lightweight dashboard for project registration, field-data upload, and audit-trail visualization.

> **Author:** Wahome A. Wambugu | **Supervisor:** Emmanuel Adjei | **Institution:** African Leadership University, Kigali, Rwanda | **Video Demo:** [Final Version Video Demo](https://drive.google.com/file/d/1-XVYOEI7cy3BKUBAbhRiM0s8h4sGGYag/view?usp=sharing)

---

## Project Scope

This repository was re-scoped in June 2026 to align with the revised capstone research proposal. The sections below define what this academic prototype does and does not cover — read this before the rest of the document, since several features (carbon-credit issuance, marketplace listing, payments, blockchain settlement, buyer matching) are explicitly **out of scope** and have been removed from this codebase.

### In Scope

- A locally-calibrated AGB estimation model fusing Sentinel-1, Sentinel-2, and GEDI LiDAR.
- Field-plot validation in **Bugesera** (savanna/grassland, Eastern Province) and **Rulindo** (agroforestry, Northern Province) districts of Rwanda.
- An uncertainty-reporting module (prediction intervals alongside point estimates).
- A web dashboard for project (plot) registration, field/scan data upload, and audit-trail visualization for a verification workflow.
- Three roles: **Land Steward** (registers plots, submits field/scan data), **Verifier/Analyst** (reviews submissions, confirms or flags them), and **Research-Administrator** (backend tier with exclusive full-precision data access).
- Ethical safeguards per proposal Section 3.6: coordinate rounding, role-/district-scoped access, separate precise-location consent, and a defined data-retention period.
- Structured experiment tracking (Section 3.7) for every model training run.

### Explicitly Out of Scope

Soil organic carbon estimation, biodiversity co-benefits, a secondary carbon-credit market, blockchain settlement, automated carbon-credit issuance, buyer matching/settlement, and full registry integration (Verra/Gold Standard) are **not** part of this capstone. The original codebase included working implementations of several of these features (a carbon-credit marketplace, pricing tiers, Polar.sh payments, certificate generation, buyer dashboards); these have been **removed** from this repository as part of the re-scope. Only the locally-calibrated AGB estimation model, the uncertainty-reporting module, and the registration/upload/verification dashboard remain.

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

| Role             | Was (pre-rescope)                       | Responsibilities                                                                                                          |
| ---------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `steward`        | `landowner`                             | Registers plots, draws boundaries, submits field/scan data for review.                                                    |
| `analyst`        | `verifier_analyst` / `business`/`buyer` | Reviews submitted scans/field data via a district-scoped audit queue; confirms or flags records for the audit trail.      |
| `research_admin` | `admin`                                 | Backend tier with exclusive access to full-precision (unrounded) coordinate data, per the Section 3.6 ethical safeguards. |

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
2. **Role-/district-scoped access.** `users.assigned_district` scopes an `analyst`'s audit queue (`GET /api/landowner/verification-queue`) to one district. This is deliberately **fail-open/permissive** — if the column doesn't exist yet or is unset, the queue falls back to showing all districts rather than none, since under-scoping an audit queue is a usability gap, not a confidentiality leak (the opposite fallback direction from safeguard 1, and documented as such in both modules to avoid conflating the two).
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
│   │   ├── auth.py                 # Signup/login/session (steward, analyst, research_admin)
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
│   └── requirements.txt
│
├── frontend/
│   ├── src/app/                    # LIVE: landing page, login, signup, request-registration,
│   │   │                           #       scan, landowner/ (+ monitoring, pending-scans),
│   │   │                           #       admin/requests
│   │   ├── components/             # Navbar, ProtectedRoute, MapView, RiskGauge, StatsBar, CreditCard
│   │   ├── contexts/AuthContext.tsx
│   │   └── lib/api.ts, types.ts
│
├── docs/                            # ARCHITECTURE.md, SETUP.md, SUPABASE_SETUP.md, SUPABASE_QUICK_START.md
├── notebooks/integrity_score_training.ipynb
└── README.md                        # This file
```

---

## API Reference (Live Endpoints)

Only routers imported by `backend/main.py` are reachable; everything below is live. The marketplace-era endpoints (credits, transactions, certificates, dashboard, plots_enhanced) were removed in the re-scope and no longer exist.

```
Auth            POST /api/auth/signup | login | logout
                GET  /api/auth/me | user-by-email

Registration    POST /api/registration/request
                GET  /api/registration/requests

Scan            POST /api/scan
                GET  /api/scan/{scan_id}

Landowner /     GET  /api/landowner/pending-scans      (steward-scoped)
Verification    GET  /api/landowner/verification-queue  (analyst, district-scoped)
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

### Recent Improvements (July 2026)

**Registration API (`/api/registration/request`)**
- Refactored request payload parsing to accept raw JSON instead of Pydantic model validation, improving flexibility for frontend-driven schema evolution.
- Added comprehensive request validation with explicit error messages for missing required fields (`owner_name`, `owner_email`, `land_location`, `land_size`, `land_type`).
- Enhanced logging with `exc_info=True` for improved debugging and error trace collection.
- Simplified coordinate/boundary handling: now captures `geometry` directly from request without intermediate field mapping.
- Improved error messaging to include the underlying exception detail, aiding frontend error handling.

**Scan API (`/api/scan`)**
- Added fault-tolerant carbon-credit creation with graceful fallback: if the full credit record fails to insert (e.g., missing optional fields), the system attempts a minimal-fields fallback rather than crashing the entire scan response.
- Enhanced error handling on notification creation: marked as non-fatal (logs warning, not error) so a notification failure does not block the scan workflow.
- Structured exception handling with specific error logging at each critical step (carbon-credit insert, fallback credit, notification).
- Improved observability: detailed logging at each stage of the scan-to-credit flow for post-incident debugging.

These changes improve API resilience in production by tolerating partial failures in downstream services (notifications, optional database fields) while still delivering core scan results to the frontend.

---

## Installation & Setup Guide

### System Requirements

**Required:**
- **Python 3.11+** — Backend runtime ([download](https://www.python.org/downloads/))
- **Node.js 18+** and **npm 9+** — Frontend build and runtime ([download](https://nodejs.org/))
- **Git** — Version control ([download](https://git-scm.com/))
- **PostgreSQL client** (optional but recommended) — For direct database inspection

**External Accounts & Credentials (Required for Full Functionality):**
- **Supabase account** — PostgreSQL hosting + Auth ([create at supabase.com](https://supabase.com))
- **Google Cloud project** with Earth Engine API enabled — For satellite imagery ([setup guide](https://cloud.google.com/docs/authentication/getting-started))
- **Mapbox account** — Map rendering and geospatial UI ([create at mapbox.com](https://mapbox.com))

---

### Step-by-Step Installation

#### Step 1: Clone the Repository

```bash
git clone https://github.com/tonywahome/mission_capstone.git
cd mission_capstone
```

Verify the directory structure:
```bash
ls -la
# Expected: backend/, frontend/, docs/, README.md, .env, etc.
```

---

#### Step 2: Set Up External Services

Before running the application locally, you'll need to configure three external services: Supabase (database), Google Earth Engine (satellite data), and Mapbox (maps).

**A) Supabase Setup**

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project:
   - Choose a project name (e.g., `terrafoma-capstone`)
   - Select your preferred region (e.g., `us-east-1`)
   - Create a strong database password
3. Once created, go to **Settings → API** and copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` → `SUPABASE_ANON_KEY`
   - `service_role secret` → `SUPABASE_SERVICE_ROLE_KEY`
4. Open the SQL Editor and run the database initialization scripts (in order):
   ```sql
   -- Run each file in sequence:
   -- 1. backend/data/schema.sql
   -- 2. backend/data/migration_add_auth.sql
   -- 3. backend/data/migration_approval_workflow.sql
   -- 4. backend/data/migration_capstone_rescope.sql
   -- 5. backend/data/migration_canonical_entities.sql
   -- 6. (Optional) backend/data/sample_data.sql  (for demo data)
   ```
   For detailed Supabase setup, see [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md)

**B) Google Earth Engine Setup**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Earth Engine API**:
   - Search for "Earth Engine API" in the search bar
   - Click **Enable**
4. Create a Service Account:
   - Go to **Service Accounts** (under IAM & Admin)
   - Click **Create Service Account**
   - Fill in name and description
   - Grant the role: **Editor** (or `roles/earthengine.admin`)
   - Create a JSON key and download it
5. Save the JSON file to your project:
   ```bash
   # Save to a secure location, e.g.:
   mkdir -p ~/.gee-credentials
   # Copy your downloaded JSON file there
   ```

**C) Mapbox Setup**

1. Go to [mapbox.com](https://account.mapbox.com)
2. Sign up or log in
3. Go to **Tokens** and copy your default public token
4. If the token doesn't exist, create one with these scopes:
   - `maps:read`
   - `styles:read`
   - `datasets:read`

---

#### Step 3: Configure Environment Variables

**Backend Configuration:**

```bash
cd backend
cp ../.env.production.example .env
```

Edit `backend/.env` with your credentials:
```bash
# Supabase (from Step 2.A)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_from_supabase
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_from_supabase

# Google Earth Engine (from Step 2.B)
EARTHENGINE_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json

# CORS (adjust as needed for your frontend)
CORS_ORIGINS=["http://localhost:3001"]

# Optional
API_HOST=0.0.0.0
API_PORT=8002
```

**Frontend Configuration:**

```bash
cd frontend
cp .env.example .env.local
```

Edit `frontend/.env.local` with your credentials:
```bash
# API Backend URL (local development)
NEXT_PUBLIC_API_URL=http://localhost:8002

# Mapbox (from Step 2.C)
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_public_token

# Supabase (optional, for client-side operations)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key_from_supabase
```

---

#### Step 4: Set Up Python Virtual Environment

```bash
# Navigate to project root
cd mission_capstone

# Create virtual environment
python3 -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Windows Command Prompt:
.\.venv\Scripts\activate.bat
```

Verify activation (you should see `(.venv)` prefix in your terminal):
```bash
python --version  # Should be 3.11+
```

---

#### Step 5: Install Backend Dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

Verify installation:
```bash
python -c "import fastapi, supabase; print('✓ Dependencies OK')"
```

---

#### Step 6: Authenticate with Google Earth Engine

```bash
# Set GOOGLE_APPLICATION_CREDENTIALS to your service account JSON
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json

# Initialize Earth Engine (one-time setup)
earthengine authenticate

# Verify connection
python -c "import ee; ee.Initialize(); print('✓ Earth Engine OK')"
```

---

#### Step 7: Start the Backend Server

```bash
cd backend
uvicorn main:app --reload --port 8002
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8002
INFO:     Application startup complete
```

**Access:**
- API: `http://localhost:8002`
- Interactive API Docs: `http://localhost:8002/docs`
- ReDoc (alternative docs): `http://localhost:8002/redoc`

---

#### Step 8: Install Frontend Dependencies

In a **new terminal**:

```bash
cd frontend
npm install
```

Verify installation:
```bash
npm list react  # Should show React 18.3+
```

---

#### Step 9: Start the Frontend Server

```bash
cd frontend
npm run dev
```

**Expected output:**
```
  ▲ Next.js 14.2.35
  - Local:        http://localhost:3001
```

**Access:**
- Frontend: `http://localhost:3001`

---

### Verification Checklist

Run this checklist to ensure everything is working:

- [ ] **Backend API**: `curl http://localhost:8002/docs` returns OpenAPI docs
- [ ] **Frontend**: `http://localhost:3001` loads the landing page
- [ ] **Database**: Backend can query Supabase (check console for no errors)
- [ ] **Earth Engine**: Backend can initialize EE API (check for `Earth Engine OK` message)
- [ ] **Maps**: Frontend map component loads without errors (F12 → Console)

---

### Creating Test Accounts

1. Open `http://localhost:3001/signup` in your browser
2. Fill in the form:
   - **Email**: any email (doesn't need to be real for local testing)
   - **Password**: any secure password
   - **Role**: Choose `steward`, `analyst`, or `research_admin`
   - **District**: `Bugesera` or `Rulindo`
3. Click **Sign Up**
4. You're now logged in! Explore the dashboard:
   - **Steward**: Register plots and upload scans
   - **Verifier/Analyst**: Review submissions in the verification queue
   - **Research Admin**: Access full-precision data and system settings

**Pre-seeded Demo Data:**

If you loaded `backend/data/sample_data.sql` in Supabase, a demo steward profile exists:
- **Email**: `steward.pilot@terrafoma-capstone.local`
- **Password**: Set your own via `/signup` (seed data has no password)
- **Role**: `steward`
- **Sample plots**: Pre-drawn plots in Bugesera and Rulindo appear on the map

---

### Project Directory Structure

**Key files and directories:**

```
mission_capstone/
│
├── .env                              # Root environment variables (shared config)
├── .env.example                      # Template (do not edit)
├── README.md                         # This file
│
├── backend/                          # FastAPI backend
│   ├── main.py                       # Entry point; registers all routers
│   ├── config.py                     # Configuration and settings
│   ├── database.py                   # Supabase client initialization
│   ├── requirements.txt              # Python dependencies
│   ├── .env                          # Backend environment variables (override root .env)
│   ├── .env.production.example       # Template for production
│   │
│   ├── routers/                      # API endpoint handlers
│   │   ├── auth.py                   # User signup, login, session management
│   │   ├── registration.py           # Land plot registration requests
│   │   ├── scan.py                   # AI satellite scan trigger & lookup
│   │   ├── landowner.py              # User dashboard (pending scans, credits)
│   │   ├── notifications.py          # Notification system
│   │   ├── plots.py                  # Plot CRUD operations
│   │   └── monitoring.py             # Health checks and monitoring
│   │
│   ├── services/                     # Business logic and external integrations
│   │   ├── biomass_estimator.py      # ML model inference
│   │   ├── carbon_calculator.py      # Carbon credit calculation
│   │   ├── gee_feature_extractor.py  # Sentinel-1/2, GEDI data extraction
│   │   ├── gee_biomass_baseline.py   # GEDI L4B baseline reference
│   │   ├── risk_scorer.py            # Risk assessment for scans
│   │   ├── location_service.py       # Geospatial utilities
│   │   ├── privacy.py                # Section 3.6 ethical safeguards
│   │   ├── mock_data.py              # Demo data generation
│   │   └── experiment_tracker.py     # ML experiment logging
│   │
│   ├── models/                       # Data models (Pydantic schemas)
│   │   ├── user.py                   # User, role definitions
│   │   ├── land_plot.py              # Land plot schema
│   │   └── risk.py                   # Risk model schema
│   │
│   ├── ml/                           # Machine learning pipeline
│   │   ├── train_biomass_model.py    # Model training script
│   │   ├── models/
│   │   │   └── biomass_model_v1.pkl  # Trained XGBoost model (artifact)
│   │   ├── collect_sentinel_data.py  # Data collection from Sentinel
│   │   ├── collect_gedi_data.py      # GEDI LiDAR data collection
│   │   └── gee_export_rwanda.py      # Earth Engine Rwanda export
│   │
│   ├── data/                         # Database schemas and migrations
│   │   ├── schema.sql                # Main database schema
│   │   ├── migration_*.sql           # Incremental migrations
│   │   ├── sample_data.sql           # Demo user/plot data
│   │   └── sample_plots.geojson      # GeoJSON sample plots
│   │
│   └── templates/                    # Email templates, etc.
│
├── frontend/                         # Next.js frontend
│   ├── package.json                  # Node.js dependencies
│   ├── next.config.js                # Next.js configuration
│   ├── tsconfig.json                 # TypeScript configuration
│   ├── .env.local                    # Frontend environment variables (local)
│   ├── .env.example                  # Template for .env.local
│   ├── Dockerfile                    # Container image definition
│   ├── railway.json                  # Railway.app deployment config
│   │
│   ├── src/
│   │   ├── app/                      # Next.js 14 App Router
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── login/                # Login page
│   │   │   ├── signup/               # User signup
│   │   │   ├── request-registration/ # Plot registration request form
│   │   │   ├── scan/                 # Satellite scan trigger
│   │   │   ├── landowner/            # User dashboard
│   │   │   │   ├── page.tsx          # Landowner home
│   │   │   │   ├── pending-scans/    # Pending scans list
│   │   │   │   └── monitoring/       # Monitoring dashboard
│   │   │   ├── admin/                # Admin pages
│   │   │   └── layout.tsx            # Root layout
│   │   │
│   │   ├── components/               # Reusable React components
│   │   │   ├── Navbar.tsx            # Navigation bar
│   │   │   ├── MapView.tsx           # Mapbox GL map
│   │   │   ├── ProtectedRoute.tsx    # Auth-protected route wrapper
│   │   │   ├── RiskGauge.tsx         # Risk visualization
│   │   │   ├── StatsBar.tsx          # Statistics display
│   │   │   └── CreditCard.tsx        # Carbon credit card
│   │   │
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx       # Global auth state
│   │   │
│   │   └── lib/
│   │       ├── api.ts                # Backend API client
│   │       ├── types.ts              # TypeScript type definitions
│   │       └── utils.ts              # Utility functions
│   │
│   └── public/                       # Static assets (images, icons)
│
├── docs/                             # Project documentation
│   ├── SETUP.md                      # Detailed setup instructions
│   ├── ARCHITECTURE.md               # System architecture
│   ├── SUPABASE_SETUP.md             # Database-specific setup
│   └── SUPABASE_QUICK_START.md       # Quick Supabase guide
│
├── notebooks/                        # Jupyter notebooks (analysis, training)
│   └── integrity_score_training.ipynb
│
├── datasets/                         # Sample datasets and GeoJSON files
│
├── scripts/                          # Utility scripts
│
└── render.yaml                       # Render.com deployment config
```

---

### Common Tasks

**Run Backend in Production Mode:**
```bash
cd backend
gunicorn main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8002
```

**Build Frontend for Production:**
```bash
cd frontend
npm run build
npm start
```

**Run Backend Tests (if available):**
```bash
cd backend
pytest tests/
```

**Format Code:**
```bash
# Backend
cd backend
black .
isort .

# Frontend
cd frontend
npm run lint
```

**View Database Directly:**
```bash
# Using psql (requires PostgreSQL client)
psql postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

**Check API Health:**
```bash
curl -s http://localhost:8002/docs | grep -q "FastAPI" && echo "✓ Backend OK" || echo "✗ Backend Down"
```

---

### Troubleshooting

**Issue: "ModuleNotFoundError: No module named 'fastapi'"**
- Solution: Ensure virtual environment is activated and `pip install -r requirements.txt` completed

**Issue: "SUPABASE_URL is not set"**
- Solution: Check `.env` file exists in backend directory with correct credentials

**Issue: "Earth Engine authentication failed"**
- Solution: Re-run `earthengine authenticate` and verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct

**Issue: Frontend can't reach backend API**
- Solution: Verify `NEXT_PUBLIC_API_URL=http://localhost:8002` in `frontend/.env.local` and backend is running

**Issue: "Mapbox token invalid"**
- Solution: Regenerate token from [mapbox.com/tokens](https://account.mapbox.com/access-tokens/) and update `NEXT_PUBLIC_MAPBOX_TOKEN`

**Issue: "Connection refused" on Supabase**
- Solution: Verify internet connection and that Supabase project is active (check at supabase.com/projects)

For more help, check [docs/SETUP.md](docs/SETUP.md) or [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md)

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

## Removed Scope (Marketplace / Carbon-Credit Features)

The original codebase included a working carbon-credit marketplace (listing, pricing tiers, Polar.sh payments, certificate generation, buyer dashboards, registry views). These features are out of scope for this academic capstone and have been **removed** from the repository — the corresponding backend routers/models/services (`credits`, `transactions`, `certificates`, `dashboard`, `plots_enhanced`, `carbon_credit_engine`, `certificate_generator`) and frontend routes (`marketplace`, `registry`, `certificate`, `purchase-success`, `dashboard`, `checkout`/`confirm-payment`/`webhooks` payment APIs) no longer exist.

The underlying Supabase tables (`carbon_credits`, `transactions`) remain in `schema.sql` for backward compatibility — no destructive migration was run — and the live application still writes interim verification outcomes onto `carbon_credits.status` pending a dedicated `verifications` table (added as a schema-only scaffold by `migration_capstone_rescope.sql`, not yet wired up). Do not present capstone evaluation results as validating any commercial carbon-market product.

---

## Canonical Data Model (Section 3.4)

The proposal's Section 3.4 class diagram defines exactly four domain entities: **Project**, **Steward**, **BiomassModel**, **Verification**. The physical schema (`schema.sql`) predates the re-scope and is organized around marketplace-era tables instead — `land_plots`, `users`, `scan_results`, `carbon_credits`/`verifications`. Renaming or collapsing those tables outright would violate this project's additive-only migration philosophy (see `migration_capstone_rescope.sql`'s header).

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

This is an academic capstone roadmap, not a commercial product roadmap — items like marketplace expansion, blockchain settlement, or registry integration are deliberately out of scope (see [Removed Scope](#removed-scope-marketplace--carbon-credit-features)).

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

This project is an academic capstone submission. All rights reserved; for licensing inquiries, contact the maintainer directly.
