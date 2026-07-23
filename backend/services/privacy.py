"""
Privacy & access-tier utilities — capstone proposal Section 3.6 (Ethical
Safeguards).

Implements two of the four safeguards described in the revised research
proposal:

  1. Coordinate rounding (safeguard 1): "precise GPS plot coordinates are
     retained at full precision only in the secure, access-controlled
     research database used for model training; any coordinates appearing
     in reports, the dashboard's visualisation layer, or this proposal's
     eventual write-up are rounded to a precision no finer than
     approximately 100m, sufficient for district- and stratum-level
     reporting but insufficient to identify an individual farmer's exact
     plot boundary." Full, unrounded precision stays in the underlying
     database and is only ever sent to a verified research_admin caller.

  2. Role-based access (safeguard 2): "...distinct access roles for land
     stewards (who can view and edit only their own registered plots),
     verifiers/analysts (who can view plot-level data within their
     assigned district for audit purposes), and a research-administrator
     role (the only role with access to the full, unrounded dataset)..."
     Steward-scoping is enforced in routers/plots.py and routers/landowner.py
     via owner_id filtering. District-scoping for verifiers/analysts is
     implemented in routers/landowner.py's /verification-queue endpoint
     using the caller's assigned_district (from their verified JWT
     app_metadata — see backend/services/auth_deps.py). Full-precision
     entitlement for the coordinate rounding below is determined the same
     way, via auth_deps.get_current_user_optional.

This module does NOT implement safeguards 3 (separate, explicitly-worded
consent for precise-location storage — see `precise_location_consent` on
models/user.py and models/land_plot.py, already wired into the signup and
registration flows) or 4 (defined retention period — see
`users.data_retention_until` / `services/retention.py`).

Role resolution for the coordinate-rounding decision now goes through
`backend/services/auth_deps.py`'s `get_current_user_optional`, which verifies
a real Supabase Auth JWT (see backend/data/migration_supabase_auth.sql) —
this module previously did its own `sessions` -> `users` token lookup
(`resolve_role`/`resolve_role_name`), which has been removed now that the
`sessions` table no longer exists.
"""
from typing import Optional
import copy
import logging

logger = logging.getLogger(__name__)

# Coordinates are rounded to this many decimal degrees. 3 decimal places is
# ~111m at the equator — satisfies the proposal's "no finer than
# approximately 100m" requirement with a small conservative margin.
COORD_ROUNDING_DECIMALS = 3

# The only role permitted to receive full, unrounded coordinate precision.
FULL_PRECISION_ROLE = "research_admin"


def round_coordinate(value: float, decimals: int = COORD_ROUNDING_DECIMALS) -> float:
    """Round a single longitude or latitude value to ~100m precision."""
    return round(value, decimals)


def _round_coords_recursive(node, decimals: int):
    """Recursively round a GeoJSON `coordinates` array. Point, LineString,
    Polygon, and MultiPolygon all nest plain [lon, lat] number pairs at the
    leaves, just at different array depths, so a generic recursive walk
    handles every geometry type without per-type branching."""
    if isinstance(node, (int, float)):
        return round_coordinate(node, decimals)
    if isinstance(node, list):
        return [_round_coords_recursive(n, decimals) for n in node]
    return node


def round_geojson_geometry(
    geometry: Optional[dict], decimals: int = COORD_ROUNDING_DECIMALS
) -> Optional[dict]:
    """Return a COPY of a GeoJSON geometry dict with all coordinates rounded
    to ~100m precision. Non-destructive — the caller's original dict (e.g.
    the full-precision row just read from the database) is left untouched."""
    if not geometry or "coordinates" not in geometry:
        return geometry
    rounded = copy.deepcopy(geometry)
    rounded["coordinates"] = _round_coords_recursive(rounded["coordinates"], decimals)
    return rounded


def apply_coordinate_rounding(
    plot: dict, role: Optional[str], decimals: int = COORD_ROUNDING_DECIMALS
) -> dict:
    """Apply Section 3.6 safeguard 1 to a single land_plots row before it
    leaves the backend. A confirmed research_admin session sees full
    precision; every other caller — including unauthenticated or
    unrecognised ones — gets rounded coordinates. Fails closed by design."""
    if role == FULL_PRECISION_ROLE:
        return plot
    if isinstance(plot, dict) and "geometry" in plot:
        plot = {**plot, "geometry": round_geojson_geometry(plot.get("geometry"), decimals)}
    return plot
