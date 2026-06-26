from fastapi import APIRouter, HTTPException
from typing import Optional
from models.land_plot import LandPlotCreate, LandPlotResponse
from database import get_supabase_client, get_admin_client
from services.privacy import apply_coordinate_rounding, resolve_role_name
import uuid

router = APIRouter(prefix="/api/plots", tags=["plots"])

# Section 3.6 safeguard 1 (coordinate rounding): every endpoint below that
# returns plot geometry accepts an optional `token` query param and rounds
# coordinates to ~100m precision unless that token resolves to a
# research_admin session. See services/privacy.py for the full rationale
# and its documented limitation (no auth middleware exists in this codebase
# yet, so this is an opt-in check a caller can omit, not an enforced one —
# omitting it simply means the caller is treated as least-privilege).


@router.get("")
async def list_plots(token: Optional[str] = None):
    db = get_supabase_client()
    result = db.table("land_plots").select("*").execute()
    role = resolve_role_name(token, get_admin_client())
    return [apply_coordinate_rounding(p, role) for p in result.data]


@router.get("/geojson")
async def get_plots_geojson(token: Optional[str] = None):
    db = get_supabase_client()
    result = db.table("land_plots").select("*").execute()
    role = resolve_role_name(token, get_admin_client())
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
async def get_plots_by_owner(owner_id: str, token: Optional[str] = None):
    """Get all plots owned by a user, enriched with latest scan and monitoring data."""
    db = get_admin_client()

    plots_result = db.table("land_plots").select("*").eq("owner_id", owner_id).execute()
    plots = plots_result.data or []
    role = resolve_role_name(token, db)

    enriched = []
    for plot in plots:
        pid = plot["id"]

        scan_res = (
            db.table("scan_results")
            .select("mean_ndvi, mean_evi, estimated_tco2e, estimated_biomass, created_at")
            .eq("plot_id", pid)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        plot["latest_scan"] = scan_res.data[0] if scan_res.data else None

        mon_res = (
            db.table("monitoring_reports")
            .select("*")
            .eq("plot_id", pid)
            .order("check_date", desc=True)
            .limit(1)
            .execute()
        )
        plot["latest_monitoring"] = mon_res.data[0] if mon_res.data else None

        enriched.append(apply_coordinate_rounding(plot, role))

    return enriched


@router.get("/{plot_id}")
async def get_plot(plot_id: str, token: Optional[str] = None):
    db = get_admin_client()
    result = db.table("land_plots").select("*").eq("id", plot_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Plot not found")

    plot = result.data[0]

    scan_result = (
        db.table("scan_results")
        .select("*")
        .eq("plot_id", plot_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    plot["latest_scan"] = scan_result.data[0] if scan_result.data else None
    role = resolve_role_name(token, db)
    return apply_coordinate_rounding(plot, role)


@router.post("", response_model=LandPlotResponse)
async def create_plot(plot: LandPlotCreate):
    db = get_supabase_client()
    # exclude_none avoids sending columns (e.g. `district`) that won't exist
    # until backend/data/migration_capstone_rescope.sql has been applied.
    plot_data = {
        "id": str(uuid.uuid4()),
        **plot.model_dump(exclude_none=True),
    }
    result = db.table("land_plots").insert(plot_data).execute()
    return result.data[0]


@router.delete("/{plot_id}")
async def delete_plot(plot_id: str, owner_id: str):
    """Delete a plot. Blocked if the plot has a credit awaiting or past verification."""
    db = get_admin_client()

    plot_res = db.table("land_plots").select("id, owner_id").eq("id", plot_id).execute()
    if not plot_res.data:
        raise HTTPException(status_code=404, detail="Plot not found")
    if plot_res.data[0]["owner_id"] != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this plot")

    # Status vocabulary post-rescope is 'pending_approval'/'verified'/'flagged'
    # (see routers/scan.py, data/sample_data.sql). 'listed'/'sold' are kept
    # alongside them for backward compatibility with any pre-rescope rows —
    # without 'pending_approval'/'verified' here, this guard was a no-op
    # against every credit the live app actually writes, since nothing in
    # the current flow sets status to 'listed' or 'sold' anymore.
    active_credits = (
        db.table("carbon_credits")
        .select("id", count="exact")
        .eq("plot_id", plot_id)
        .in_("status", ["pending_approval", "verified", "listed", "sold"])
        .execute()
    )
    if active_credits.count and active_credits.count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a plot with a carbon credit that is pending verification, verified, listed, or sold",
        )

    db.table("monitoring_reports").delete().eq("plot_id", plot_id).execute()
    db.table("carbon_credits").delete().eq("plot_id", plot_id).execute()
    db.table("scan_results").delete().eq("plot_id", plot_id).execute()
    db.table("land_plots").delete().eq("id", plot_id).execute()

    return {"message": "Plot deleted successfully", "plot_id": plot_id}
