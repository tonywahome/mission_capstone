from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import scan, plots, auth, registration, notifications, landowner, monitoring

# NOTE — re-scope (capstone proposal, June 2026): the marketplace / credit-
# issuance / payments routers (credits, transactions, certificates,
# dashboard) have been relocated to `backend/legacy/` and are intentionally
# NOT imported here. They remain on disk, unmodified, for the separate
# TerraFoma LTD commercial product — see `backend/legacy/README.md`.

app = FastAPI(
    title="TerraFoma Research Prototype API",
    description=(
        "Locally-calibrated above-ground biomass (AGB) estimation, "
        "project registration, and audit-trail monitoring for the ALU BSc "
        "Software Engineering capstone (Bugesera & Rulindo, Rwanda)."
    ),
    version="2.0.0",
)

# CORS — set CORS_ORIGINS env var to a comma-separated list of allowed origins.
# All *.vercel.app subdomains are also allowed via regex for Vercel preview deployments.
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (capstone-scope only — see NOTE above for legacy routers)
app.include_router(auth.router)
app.include_router(registration.router)
app.include_router(notifications.router)
app.include_router(landowner.router)
app.include_router(scan.router)
app.include_router(plots.router)
app.include_router(monitoring.router)


@app.get("/")
async def root():
    return {
        "name": "TerraFoma Research Prototype API",
        "version": "2.0.0",
        "description": (
            "Multi-sensor biomass estimation and audit-trail monitoring "
            "prototype — Bugesera & Rulindo, Rwanda"
        ),
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
