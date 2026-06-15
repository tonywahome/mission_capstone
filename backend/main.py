from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import scan, plots, credits, transactions, dashboard, certificates, auth, registration, notifications, landowner, monitoring

app = FastAPI(
    title="TerraFoma API",
    description="AI-powered Carbon Credit Verification & Exchange Platform",
    version="1.0.0",
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

# Register routers
app.include_router(auth.router)
app.include_router(registration.router)
app.include_router(notifications.router)
app.include_router(landowner.router)
app.include_router(scan.router)
app.include_router(plots.router)
app.include_router(credits.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)
app.include_router(certificates.router)
app.include_router(monitoring.router)


@app.get("/")
async def root():
    return {
        "name": "TerraFoma API",
        "version": "1.0.0",
        "description": "AI-powered Carbon Credit Verification & Exchange Platform",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
