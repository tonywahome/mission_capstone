from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from models.land_plot import LandPlotCreate, LandPlotResponse
from database import get_admin_client
from services.privacy import apply_coordinate_rounding
from services.auth_deps import get_current_user, get_current_user_optional, AuthedUser
import uuid

router = APIRouter(prefix="/api/plots", tags=["plots"])

# Section 3.6 safeguard 1 (coordinate rounding): every endpoint below that
# returns plot geometry rounds coordinates to ~100m precision unless the
# verified caller is a research_admin. An unauthenticated/unrecognised
# caller is treated as least-privilege (rounded), never full precision.

# Roles allowed to see plots beyond their own (verifier/audit + admin tiers).
CROSS_OWNER_ROLES = ("analyst", "research_admin")


def _forbid_unless_owner_or_privileged(caller: Optional[AuthedUser], owner_id: str):
    if caller is None or (caller.id != owner_id and caller.role not in CROSS_OWNER_ROLES):
        raise HTTPException(status_code=403, detail="Not authorized to view this plot")


@router.get("")
async def list_plots(
    limit: int = 100,
    offset: int = 0,
    caller: Optional[AuthedUser] = Depends(get_current_user_optional),
):
    db = get_admin_client()
    query = db.table("land_plots").select("*")
    if caller and caller.role == "steward":
        query = query.eq("owner_id", caller.id)
    elif not caller or caller.role not in CROSS_OWNER_ROLES:
        # Unauthenticated or any other non-privileged caller: no owner to
        # scope to, so return nothing rather than everyone's plots.
        return []
    result = query.range(offset, offset + limit - 1).execute()
    role = caller.role if caller else None
    return [apply_coordinate_rounding(p, role) for p in result.data]


@router.get("/geojson")
async def get_plots_geojson(caller: Optional[AuthedUser] = Depends(get_current_user_optional)):
    db = get_admin_client()
    query = db.table("land_plots").select("*")
    if caller and caller.role == "steward":
        query = query.eq("owner_id", caller.id)
    elif not caller or caller.role not in CROSS_OWNER_ROLES:
        return {"type": "FeatureCollection", "features": []}
    result = query.execute()
    role = caller.role if caller else None

    features = []
    for plot in result.data:
        plot = apply_coordinate_rounding(plot, role)
        feature = {
            "type": "Feature",
            "properties": {
                "id": plot["id"],
                "name": plot["name"],
                "area_hectares": plot["area_hectares"],
                "region": plot.get("region"),
                "district": plot.get("district"),
                "land_use": plot.get("land_use"),
                "owner_id": plot.get("owner_id"),
            },
            "geometry": plot.get("geometry", {}),
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


@router.get("/owner/{owner_id}")
async def get_plots_by_owner(
    owner_id: str,
    limit: int = 100,
    offset: int = 0,
    caller: Optional[AuthedUser] = Depends(get_current_user_optional),
):
    """Get all plots owned by a user, enriched with latest scan and monitoring data."""
    _forbid_unless_owner_or_privileged(caller, owner_id)

    db = get_admin_client()

    plots_result = (
        db.table("land_plots")
        .select("*")
        .eq("owner_id", owner_id)
        .range(offset, offset + limit - 1)
        .execute()
    )
    plots = plots_result.data or []
    role = caller.role if caller else None
    plot_ids = [p["id"] for p in plots]

    # Batch-fetch the latest scan/monitoring row per plot in 2 queries total
    # instead of 2 queries per plot (previously 1 + 2N round trips for N
    # plots). Since there's no native "latest per group" query, fetch all
    # matching rows sorted newest-first and keep the first hit per plot_id.
    latest_scan_by_plot: dict = {}
    latest_monitoring_by_plot: dict = {}
    if plot_ids:
        all_scans = (
            db.table("scan_results")
            .select("plot_id, mean_ndvi, mean_evi, estimated_tco2e, estimated_biomass, created_at")
            .in_("plot_id", plot_ids)
            .order("created_at", desc=True)
            .execute()
        ).data or []
        for s in all_scans:
            latest_scan_by_plot.setdefault(s["plot_id"], s)

        all_monitoring = (
            db.table("monitoring_reports")
            .select("*")
            .in_("plot_id", plot_ids)
            .order("check_date", desc=True)
            .execute()
        ).data or []
        for m in all_monitoring:
            latest_monitoring_by_plot.setdefault(m["plot_id"], m)

    enriched = []
    for plot in plots:
        pid = plot["id"]
        plot["latest_scan"] = latest_scan_by_plot.get(pid)
        plot["latest_monitoring"] = latest_monitoring_by_plot.get(pid)
        enriched.append(apply_coordinate_rounding(plot, role))

    return enriched


@router.get("/{plot_id}")
async def get_plot(plot_id: str, caller: Optional[AuthedUser] = Depends(get_current_user_optional)):
    db = get_admin_client()
    result = db.table("land_plots").select("*").eq("id", plot_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Plot not found")

    plot = result.data[0]
    _forbid_unless_owner_or_privileged(caller, plot.get("owner_id"))

    scan_result = (
        db.table("scan_results")
        .select("*")
        .eq("plot_id", plot_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    plot["latest_scan"] = scan_result.data[0] if scan_result.data else None
    role = caller.role if caller else None
    return apply_coordinate_rounding(plot, role)


@router.post("", response_model=LandPlotResponse)
async def create_plot(plot: LandPlotCreate, caller: AuthedUser = Depends(get_current_user)):
    if caller.role not in ("steward", "research_admin"):
        raise HTTPException(status_code=403, detail="Only stewards can register plots")

    db = get_admin_client()
    # exclude_none avoids sending columns (e.g. `district`) that won't exist
    # until backend/data/migration_capstone_rescope.sql has been applied.
    plot_data = {
        "id": str(uuid.uuid4()),
        **plot.model_dump(exclude_none=True),
        "owner_id": caller.id,  # server-derived, never trust the client-sent value
    }
    result = db.table("land_plots").insert(plot_data).execute()
    return result.data[0]


@router.delete("/{plot_id}")
async def delete_plot(plot_id: str, caller: AuthedUser = Depends(get_current_user)):
    """Delete a plot. Blocked if the plot has a credit awaiting or past verification."""
    db = get_admin_client()

    plot_res = db.table("land_plots").select("id, owner_id").eq("id", plot_id).execute()
    if not plot_res.data:
        raise HTTPException(status_code=404, detail="Plot not found")
    if plot_res.data[0]["owner_id"] != caller.id and caller.role != "research_admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this plot")

    # Status vocabulary post-rescope is 'pending_approval'/'verified'/'flagged'
    # (see routers/scan.py, data/sample_data.sql) — 'listed'/'sold' removed,
    # no code path in this app writes those statuses anymore.
    active_credits = (
        db.table("carbon_credits")
        .select("id", count="exact")
        .eq("plot_id", plot_id)
        .in_("status", ["pending_approval", "verified"])
        .execute()
    )
    if active_credits.count and active_credits.count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a plot with a carbon credit that is pending verification or verified",
        )

    db.table("monitoring_reports").delete().eq("plot_id", plot_id).execute()
    db.table("carbon_credits").delete().eq("plot_id", plot_id).execute()
    db.table("scan_results").delete().eq("plot_id", plot_id).execute()
    db.table("land_plots").delete().eq("id", plot_id).execute()

    return {"message": "Plot deleted successfully", "plot_id": plot_id}
