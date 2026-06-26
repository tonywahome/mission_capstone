"""
Monitoring API — weekly biomass/NDVI health checks for all registered plots.

Endpoints:
  GET  /api/monitoring/plots/{plot_id}/latest   Latest monitoring report for a plot
  GET  /api/monitoring/plots/{plot_id}/history  All monitoring reports for a plot
  POST /api/monitoring/plots/{plot_id}/run      Manually trigger a monitoring check
  GET  /api/monitoring/summary                  Dashboard summary across all plots
  POST /api/monitoring/run-all                  Trigger full weekly run (admin only)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Query
from database import get_supabase_client, get_admin_client
from ml.monitor_biomass import (
    analyze_plot_monitoring_data,
    fetch_current_ndvi_from_gee,
    get_mock_current_ndvi,
    get_vegetation_tile_urls,
    get_change_detection_data,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ── Helper: run a single plot monitoring check ────────────────────────────────

async def _run_plot_check(plot_id: str, db) -> Optional[dict]:
    """
    Pull plot data, fetch current satellite observation, run analysis, save report.
    Returns the monitoring report dict or None on failure.
    """
    # Load plot
    plot_result = db.table("land_plots").select("*").eq("id", plot_id).execute()
    if not plot_result.data:
        logger.warning(f"Plot {plot_id} not found")
        return None
    plot = plot_result.data[0]

    area_ha   = float(plot.get("area_hectares") or 10.0)
    geometry  = plot.get("geometry")

    # Load scan history (most recent 20 scans for baseline)
    history_result = (
        db.table("scan_results")
        .select("mean_ndvi, estimated_tco2e, created_at")
        .eq("plot_id", plot_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    scan_history = history_result.data or []
    latest_tco2e = scan_history[0]["estimated_tco2e"] if scan_history else None

    # When no scan history exists, seed from the GEDI baseline scan so the
    # first monitoring check has a real reference NDVI instead of delta=0.
    if not scan_history and plot.get("baseline_ndvi"):
        scan_history = [{
            "mean_ndvi":      plot["baseline_ndvi"],
            "estimated_tco2e": None,
            "created_at":     plot.get("baseline_scan_date"),
        }]
        logger.info(f"Plot {plot_id[:8]}… no scan history — seeding baseline from GEDI ndvi={plot['baseline_ndvi']:.3f}")

    # Baseline NDVI for mock fallback
    baseline_ndvi = (
        sum(s["mean_ndvi"] for s in scan_history) / len(scan_history)
        if scan_history else plot.get("baseline_ndvi") or 0.55
    )

    # Fetch current satellite observation
    current_obs = None
    if geometry:
        current_obs = fetch_current_ndvi_from_gee(geometry)
    if not current_obs:
        current_obs = get_mock_current_ndvi(geometry or {}, baseline_ndvi)
        logger.info(f"Plot {plot_id[:8]}… using synthetic observation (GEE unavailable)")

    # Run analysis
    report = analyze_plot_monitoring_data(
        plot_id         = plot_id,
        scan_history    = scan_history,
        current_ndvi    = current_obs["ndvi"],
        current_evi     = current_obs.get("evi"),
        current_ndmi    = current_obs.get("ndmi"),
        current_nbr     = current_obs.get("nbr"),
        current_vv      = current_obs.get("vv"),
        current_vh      = current_obs.get("vh"),
        area_ha         = area_ha,
        estimated_tco2e = latest_tco2e,
        check_date      = datetime.now(timezone.utc),
    )

    # Persist report
    try:
        admin_db = get_admin_client()
        record = {
            "id":               report["id"],
            "plot_id":          plot_id,
            "check_date":       report["check_date"],
            "current_ndvi":     report["current_ndvi"],
            "baseline_ndvi":    report["baseline_ndvi"],
            "delta_ndvi":       report["delta_ndvi"],
            "z_score":          report["z_score"],
            "classification":   report["classification"],
            "alert_level":      report["alert_level"],
            "cause":            report["cause"],
            "explanation":      report["explanation"],
            "recommendation":   report["recommendation"],
            "spectral_context": report["spectral_context"],
            "data_quality":     report["data_quality"],
        }
        admin_db.table("monitoring_reports").insert(record).execute()
        logger.info(f"Saved monitoring report {report['id'][:8]}… for plot {plot_id[:8]}…")
    except Exception as e:
        logger.warning(f"Could not save monitoring report (table may not exist yet): {e}")

    # Send notification if actionable alert
    if report["alert_level"] in ("critical", "warning"):
        try:
            owner_id = plot.get("owner_id")
            if owner_id:
                level_label = "CRITICAL ALERT" if report["alert_level"] == "critical" else "Warning"
                notif = {
                    "user_id": owner_id,
                    "type":    "monitoring_alert",
                    "title":   f"{level_label}: {report['cause']}",
                    "message": f"{report['explanation'][:300]}… Action: {report['recommendation'][:200]}",
                    "data":    {
                        "plot_id":        plot_id,
                        "report_id":      report["id"],
                        "classification": report["classification"],
                        "delta_ndvi":     report["delta_ndvi"],
                        "alert_level":    report["alert_level"],
                    },
                }
                admin_db = get_admin_client()
                admin_db.table("notifications").insert(notif).execute()
                logger.info(f"Sent {level_label} notification to owner {owner_id[:8]}…")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    return report


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/plots/{plot_id}/latest")
async def get_latest_report(plot_id: str):
    """Return the most recent monitoring report for a plot."""
    db = get_admin_client()
    try:
        result = (
            db.table("monitoring_reports")
            .select("*")
            .eq("plot_id", plot_id)
            .order("check_date", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="No monitoring reports found for this plot")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plots/{plot_id}/history")
async def get_report_history(
    plot_id: str,
    limit: int = Query(default=52, le=200),  # 52 weeks = 1 year by default
):
    """Return all monitoring reports for a plot, newest first."""
    db = get_admin_client()
    try:
        result = (
            db.table("monitoring_reports")
            .select("*")
            .eq("plot_id", plot_id)
            .order("check_date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plots/{plot_id}/run")
async def run_monitoring_for_plot(plot_id: str):
    """Manually trigger a monitoring check for one plot."""
    db = get_admin_client()
    report = await _run_plot_check(plot_id, db)
    if not report:
        raise HTTPException(status_code=404, detail="Plot not found or monitoring failed")
    return report


@router.get("/summary")
async def monitoring_summary():
    """
    Dashboard summary: count of plots by alert level in the most recent weekly check.
    """
    db = get_admin_client()
    try:
        # Get the latest report per plot using a simple approach
        result = (
            db.table("monitoring_reports")
            .select("plot_id, alert_level, classification, check_date, cause, delta_ndvi")
            .order("check_date", desc=True)
            .limit(500)
            .execute()
        )

        rows = result.data or []
        # Keep only most recent report per plot
        seen: set = set()
        latest_per_plot = []
        for row in rows:
            if row["plot_id"] not in seen:
                seen.add(row["plot_id"])
                latest_per_plot.append(row)

        from collections import Counter
        alert_counts = Counter(r["alert_level"] for r in latest_per_plot)

        return {
            "total_plots_monitored": len(latest_per_plot),
            "alert_counts": {
                "critical": alert_counts.get("critical", 0),
                "warning":  alert_counts.get("warning",  0),
                "stable":   alert_counts.get("info",     0),
                "improving":alert_counts.get("positive", 0),
            },
            "plots_needing_attention": [
                r for r in latest_per_plot
                if r["alert_level"] in ("critical", "warning")
            ],
            "last_run": rows[0]["check_date"] if rows else None,
        }
    except Exception as e:
        logger.error(f"Summary failed: {e}")
        return {"total_plots_monitored": 0, "alert_counts": {}, "plots_needing_attention": []}


@router.get("/plots/{plot_id}/change-detection")
async def get_change_detection(
    plot_id: str,
    current_days:  int = Query(default=30,  ge=1,  le=90),
    baseline_days: int = Query(default=180, ge=30, le=365),
):
    """
    Pixel-level change detection: compare the last `current_days` to the prior
    `baseline_days` window.  Returns a delta-NDVI tile URL, zone polygons (GeoJSON),
    and per-zone area statistics.
    """
    db = get_admin_client()
    try:
        result = db.table("land_plots").select("geometry").eq("id", plot_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not result.data:
        raise HTTPException(status_code=404, detail="Plot not found")

    geometry = result.data[0].get("geometry")
    if not geometry:
        raise HTTPException(status_code=422, detail="Plot has no geometry stored")

    data = get_change_detection_data(
        geometry,
        current_days=current_days,
        baseline_days=baseline_days,
    )
    if data is None:
        return {"gee_available": False}
    return data


@router.post("/run-all")
async def run_all_plots():
    """
    Trigger the weekly monitoring run for all registered plots.
    Called automatically by the scheduler every Sunday; can also be invoked manually.
    """
    db = get_admin_client()
    try:
        plots_result = db.table("land_plots").select("id").execute()
        plot_ids = [p["id"] for p in (plots_result.data or [])]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch plots: {e}")

    if not plot_ids:
        return {"message": "No plots found", "processed": 0, "reports": []}

    reports = []
    errors  = []
    for pid in plot_ids:
        try:
            report = await _run_plot_check(pid, db)
            if report:
                reports.append({
                    "plot_id":        pid,
                    "classification": report["classification"],
                    "alert_level":    report["alert_level"],
                    "cause":          report["cause"],
                    "delta_ndvi":     report["delta_ndvi"],
                })
        except Exception as e:
            errors.append({"plot_id": pid, "error": str(e)})
            logger.error(f"Monitoring failed for plot {pid}: {e}")

    summary = {
        "processed":  len(reports),
        "errors":     len(errors),
        "run_at":     datetime.now(timezone.utc).isoformat(),
        "reports":    reports,
    }
    if errors:
        summary["error_details"] = errors

    logger.info(
        f"Weekly run complete: {len(reports)} plots processed, "
        f"{sum(1 for r in reports if r['alert_level']=='critical')} critical alerts"
    )
    return summary


@router.get("/plots/{plot_id}/vegetation-tiles")
async def get_vegetation_tiles(
    plot_id: str,
    days_back: int = Query(default=30, ge=1, le=365),
):
    """
    Return GEE raster tile URLs for spatial vegetation visualization.
    Tile URLs are Mapbox GL-compatible and cover NDVI, EVI, NBR, and False Color.
    """
    db = get_admin_client()
    try:
        result = db.table("land_plots").select("geometry").eq("id", plot_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not result.data:
        raise HTTPException(status_code=404, detail="Plot not found")

    geometry = result.data[0].get("geometry")
    if not geometry:
        raise HTTPException(status_code=422, detail="Plot has no geometry stored")

    tile_data = get_vegetation_tile_urls(geometry, days_back=days_back)
    if tile_data is None:
        return {"gee_available": False, "tiles": None, "date_range": None}

    return tile_data
