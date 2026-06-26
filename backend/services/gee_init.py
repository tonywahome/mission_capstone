"""
Centralized Google Earth Engine initialization.

Credential resolution order:
  1. GEE_SERVICE_ACCOUNT_KEY env var — full service-account JSON as a string
     (the recommended approach for Railway / any container deployment)
  2. GOOGLE_APPLICATION_CREDENTIALS env var — path to a JSON key file
     (standard local-dev approach)
  3. Application default credentials — gcloud auth / Workload Identity
     (GCP-native environments)

Usage:
    from services.gee_init import initialize_gee, is_gee_available
    if initialize_gee():
        import ee
        ... use ee ...
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

_initialized: bool = False
_available:   bool = False


def initialize_gee() -> bool:
    """
    Initialize GEE once per process.  Returns True if GEE is ready to use.
    Subsequent calls are no-ops and return the cached result.
    """
    global _initialized, _available
    if _initialized:
        return _available

    try:
        import ee

        project = os.environ.get("EARTHENGINE_PROJECT_ID", "").strip() or None

        # ── Option 1: full JSON via env var (production / Railway) ──────────
        key_str = os.environ.get("GEE_SERVICE_ACCOUNT_KEY", "").strip()
        if key_str:
            key_data = json.loads(key_str)
            credentials = ee.ServiceAccountCredentials(
                email    = key_data["client_email"],
                key_data = json.dumps(key_data),
            )
            ee.Initialize(credentials, project=project)
            logger.info(
                f"GEE initialized via GEE_SERVICE_ACCOUNT_KEY "
                f"(project={project}, account={key_data['client_email']})"
            )
            _initialized = _available = True
            return True

        # ── Option 2: JSON file path via env var (local dev) ─────────────────
        key_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if key_file and os.path.exists(key_file):
            with open(key_file) as f:
                key_data = json.load(f)
            credentials = ee.ServiceAccountCredentials(
                email    = key_data["client_email"],
                key_data = json.dumps(key_data),
            )
            ee.Initialize(credentials, project=project)
            logger.info(
                f"GEE initialized via credentials file: {key_file} "
                f"(project={project})"
            )
            _initialized = _available = True
            return True

        # ── Option 3: application default credentials ─────────────────────────
        ee.Initialize(project=project)
        logger.info("GEE initialized via application default credentials")
        _initialized = _available = True
        return True

    except Exception as exc:
        logger.warning(
            f"GEE initialization failed — spectral features will use fallback data. "
            f"Error: {exc}"
        )
        _initialized = True
        _available   = False
        return False


def is_gee_available() -> bool:
    """Return cached GEE availability (call initialize_gee first)."""
    return _available
