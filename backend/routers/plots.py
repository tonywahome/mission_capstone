from fastapi import APIRouter, HTTPException
from models.land_plot import LandPlotCreate, LandPlotResponse
from database import get_supabase_client, get_admin_client
import uuid

router = APIRouter(prefix="/api/plots", tags=["plots"])


@router.get("")
async def list_plots():
    db = get_supabase_client()
    result = db.table("land_plots").select("*").execute()
    return result.data


@router.get("/geojson")
async def get_plots_geojson():
    db = get_supabase_client()
    result = db.table("land_plots").select("*").execute()
    features = []
    for plot in result.data:
        feature = {
            "type": "Feature",
            "properties": {
                "id": plot["id"],
                "name": plot["name"],
                "area_hectares": plot["area_hectares"],
                "region": plot.get("region"),
                "land_use": plot.get("land_use"),
                "owner_id": plot.get("owner_id"),
            },
            "geometry": plot.get("geometry", {}),
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


@router.get("/owner/{owner_id}")
async def get_plots_by_owner(owner_id: str):
    """Get all plots owned by a user, enriched with latest scan and monitoring data."""
    db = get_admin_client()

    plots_result = db.table("land_plots").select("*").eq("owner_id", owner_id).execute()
    plots = plots_result.data or []

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

        enriched.append(plot)

    return enriched


@router.get("/{plot_id}")
async def get_plot(plot_id: str):
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
    return plot


@router.post("", response_model=LandPlotResponse)
async def create_plot(plot: LandPlotCreate):
    db = get_supabase_client()
    plot_data = {
        "id": str(uuid.uuid4()),
        **plot.model_dump(),
    }
    result = db.table("land_plots").insert(plot_data).execute()
    return result.data[0]


@router.delete("/{plot_id}")
async def delete_plot(plot_id: str, owner_id: str):
    """Delete a plot. Blocked if the plot has listed or sold credits."""
    db = get_admin_client()

    plot_res = db.table("land_plots").select("id, owner_id").eq("id", plot_id).execute()
    if not plot_res.data:
        raise HTTPException(status_code=404, detail="Plot not found")
    if plot_res.data[0]["owner_id"] != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this plot")

    active_credits = (
        db.table("carbon_credits")
        .select("id", count="exact")
        .eq("plot_id", plot_id)
        .in_("status", ["listed", "sold"])
        .execute()
    )
    if active_credits.count and active_credits.count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a plot with active (listed or sold) carbon credits",
        )

    db.table("monitoring_reports").delete().eq("plot_id", plot_id).execute()
    db.table("carbon_credits").delete().eq("plot_id", plot_id).execute()
    db.table("scan_results").delete().eq("plot_id", plot_id).execute()
    db.table("land_plots").delete().eq("id", plot_id).execute()

    return {"message": "Plot deleted successfully", "plot_id": plot_id}
