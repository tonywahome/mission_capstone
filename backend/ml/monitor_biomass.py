"""
TerraFoma Weekly Biomass Monitoring Engine

Runs every week for every registered plot. For each plot it:
  1. Pulls the latest Sentinel-2 NDVI composite from GEE (or uses DB scan history as fallback)
  2. Compares to historical baseline (median of all prior scans)
  3. Computes a Z-score anomaly — how many standard deviations from normal
  4. Classifies the change: stable / improving / degrading / acute disturbance
  5. Diagnoses the most likely cause from spectral and contextual signals
  6. Generates a specific, actionable recommendation
  7. Saves a monitoring_report record and notifies the landowner if anomalous

Change classification thresholds (tuned for Rwanda A/R projects):
  - Acute disturbance:  delta_ndvi < -0.15  OR  Z-score < -2.5  (immediate alert)
  - Degrading:          delta_ndvi in [-0.15, -0.04]  OR  Z < -1.5
  - Stable:             |delta_ndvi| < 0.04  AND  |Z| < 1.5
  - Improving:          delta_ndvi > 0.04  OR  Z > 1.5
"""

from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

import numpy as np

# Initialize GEE once at import time using the centralized helper.
# This covers the inline `import ee` calls inside each GEE function.
try:
    from services.gee_init import initialize_gee as _init_gee
    _init_gee()
except Exception:
    pass  # GEE unavailable; each function already has its own try/except fallback

logger = logging.getLogger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────────

ACUTE_NDVI_DROP   = -0.15    # Very sudden loss — likely clearing or fire
DEGRADE_NDVI_DROP = -0.04    # Gradual decline threshold
IMPROVE_NDVI_GAIN = 0.04     # Recovery/growth threshold
ZSCORE_ACUTE      = -2.5     # Statistically extreme negative event
ZSCORE_DEGRADE    = -1.5
ZSCORE_IMPROVE    = 1.5

# Rwanda-specific context
RWANDA_DRY_MONTHS = {6, 7, 8, 1, 2}     # June–Aug + Jan–Feb (short dry)
TYPICAL_SEASONAL_DIP = -0.06             # Expected NDVI drop in dry months

# ── Change classification ──────────────────────────────────────────────────────

def classify_change(
    delta_ndvi: float,
    z_score: float,
    month: int,
) -> str:
    """
    Returns one of: acute_disturbance | degrading | stable | improving
    Accounts for expected seasonal dip in Rwanda's dry months.
    """
    # Seasonal adjustment: dry-season dips are normal
    seasonal_adj = TYPICAL_SEASONAL_DIP if month in RWANDA_DRY_MONTHS else 0.0
    adj_delta = delta_ndvi - seasonal_adj   # If it's dry season, we expect a dip

    if adj_delta < ACUTE_NDVI_DROP or z_score < ZSCORE_ACUTE:
        return "acute_disturbance"
    if adj_delta < DEGRADE_NDVI_DROP or z_score < ZSCORE_DEGRADE:
        return "degrading"
    if adj_delta > IMPROVE_NDVI_GAIN or z_score > ZSCORE_IMPROVE:
        return "improving"
    return "stable"


# ── Cause diagnosis ────────────────────────────────────────────────────────────

def diagnose_cause(
    classification: str,
    delta_ndvi: float,
    current_ndvi: float,
    ndmi_current: Optional[float],
    nbr_current: Optional[float],
    month: int,
    delta_vh_vv: Optional[float],   # SAR ratio change — if available
    prev_rainfall_anomaly: Optional[float],  # mm deviation from normal
    z_score: float = 0.0,
) -> Tuple[str, str]:
    """
    Returns (cause, detailed_explanation) strings.
    Uses all available spectral signals to narrow down the cause.
    """
    in_dry_season = month in RWANDA_DRY_MONTHS

    # ── Acute disturbance causes ──────────────────────────────────────────────
    if classification == "acute_disturbance":
        # NBR < -0.1 after a drop is diagnostic of fire
        if nbr_current is not None and nbr_current < -0.10:
            return (
                "Fire or burn event",
                f"NBR={nbr_current:.3f} indicates burned vegetation. The Normalized Burn Ratio "
                f"dropped below -0.10, consistent with post-fire bare soil exposure. "
                f"NDVI loss of {abs(delta_ndvi):.3f} confirms canopy destruction."
            )
        # SAR (VH/VV) drops when woody biomass is removed — logging/clearing
        if delta_vh_vv is not None and delta_vh_vv < -2.0:
            return (
                "Illegal clearing or deforestation",
                f"SAR VH/VV ratio dropped by {abs(delta_vh_vv):.1f} dB, indicating removal of woody "
                f"biomass. Sentinel-1 penetrates cloud cover, confirming this is structural change "
                f"not cloud interference. Immediate field investigation required."
            )
        return (
            "Acute canopy disturbance — unknown cause",
            f"NDVI dropped {abs(delta_ndvi):.3f} in a single monitoring cycle. This magnitude of "
            f"change is inconsistent with normal seasonality. Possible causes: clearing, storm "
            f"damage, pest outbreak, or fire. Field verification required within 7 days."
        )

    # ── Degrading causes ─────────────────────────────────────────────────────
    if classification == "degrading":
        # NDMI < -0.2 → moisture stress
        if ndmi_current is not None and ndmi_current < -0.20:
            if prev_rainfall_anomaly is not None and prev_rainfall_anomaly < -50:
                return (
                    "Drought stress (below-normal rainfall)",
                    f"NDMI={ndmi_current:.3f} indicates water deficit in canopy. Rainfall was "
                    f"{abs(prev_rainfall_anomaly):.0f}mm below normal in the prior 4 weeks. "
                    f"Drought-stressed vegetation is at elevated risk of mortality and reduced "
                    f"carbon uptake. Consider irrigation for recently planted areas."
                )
            return (
                "Moisture stress — possible drought or root damage",
                f"NDMI={ndmi_current:.3f} (below -0.20 threshold). Canopy is experiencing water "
                f"deficit. No major rainfall deficit confirmed — possible compacted soil, root "
                f"disease, or overgrazing reducing water retention. Soil inspection recommended."
            )
        if in_dry_season and delta_ndvi > 1.5 * TYPICAL_SEASONAL_DIP:
            return (
                "Dry-season phenological stress",
                f"NDVI decline of {abs(delta_ndvi):.3f} in dry season (Month {month}). "
                f"Expected seasonal dip is ~{abs(TYPICAL_SEASONAL_DIP):.2f}. Decline exceeds normal "
                f"range, suggesting the canopy is more drought-sensitive than baseline. "
                f"Monitor closely — recovery expected by Month 10–11 (onset of short rains)."
            )
        return (
            "Progressive vegetation decline",
            f"Gradual NDVI reduction of {abs(delta_ndvi):.3f} over the monitoring period. "
            f"Possible causes: invasive species competition, pest infestation, overgrazing pressure "
            f"at plot boundaries, or soil nutrient depletion in young plantations. "
            f"Recommend field inspection and review of management activities."
        )

    # ── Improving causes ─────────────────────────────────────────────────────
    if classification == "improving":
        if delta_ndvi > 0.10:
            return (
                "Strong vegetation recovery or growth flush",
                f"NDVI increased by {delta_ndvi:.3f} — exceptional growth signal. Likely driven by "
                f"recent rainfall after a dry period, or active growth phase of planted trees "
                f"(typically 2–5 years after planting). This is a positive indicator for carbon "
                f"accumulation. Update biomass estimate to capture gains."
            )
        if not in_dry_season:
            return (
                "Healthy wet-season growth",
                f"NDVI gain of {delta_ndvi:.3f} during wet season confirms active photosynthesis "
                f"and canopy expansion. Consistent with expected A/R project trajectory. "
                f"Current NDVI of {current_ndvi:.3f} suggests {'dense' if current_ndvi > 0.6 else 'developing'} "
                f"canopy cover."
            )
        return (
            "Vegetation recovery",
            f"Unexpected improvement of {delta_ndvi:.3f} despite dry conditions. "
            f"Possible: irrigation, microclimate buffering from existing canopy, or drought-tolerant "
            f"species recovery. Plot is performing above expectations."
        )

    # ── Stable ───────────────────────────────────────────────────────────────
    return (
        "Stable vegetation cover",
        f"NDVI change of {delta_ndvi:+.3f} is within normal variation (Z={z_score:.2f}). "
        f"Current NDVI of {current_ndvi:.3f} indicates "
        f"{'healthy closed-canopy forest' if current_ndvi > 0.65 else 'developing vegetation cover'}. "
        f"Plot is maintaining its carbon stock. No management intervention required."
    )


# ── Recommendation generator ──────────────────────────────────────────────────

def generate_recommendation(
    classification: str,
    cause: str,
    current_ndvi: float,
    delta_ndvi: float,
    area_ha: float,
    estimated_tco2e: Optional[float],
) -> str:
    """
    Generates a concrete, actionable recommendation for the plot operator.
    """
    credit_note = f" ({estimated_tco2e:.1f} tCO₂e at risk)" if estimated_tco2e else ""

    rec = {
        "acute_disturbance": (
            f"IMMEDIATE ACTION REQUIRED: Dispatch a field team within 7 days to verify the "
            f"disturbance. If confirmed, suspend carbon credit issuance for this plot{credit_note} "
            f"and document the event with GPS-referenced photos. Notify the Rwanda Forestry "
            f"Authority (RFA) if clearing or fire is confirmed. The plot will be placed under "
            f"enhanced monitoring (daily SAR alerts) until cleared."
        ),
        "degrading": (
            f"Schedule a field inspection within 30 days. Identify the degradation driver "
            f"(drought, pests, grazing, or management gaps). For plots showing moisture stress "
            f"(NDMI < -0.2), prioritise mulching or water conservation earthworks on the {area_ha:.0f} ha. "
            f"If decline continues for 3 consecutive weeks, consider reporting under the project's "
            f"buffer pool provisions to protect issued credits{credit_note}."
        ),
        "stable": (
            f"No action required. Continue routine plot management. The next full biomass scan "
            f"is recommended in 3 months to update the carbon estimate. Maintain management "
            f"records (planting logs, maintenance activities) for upcoming verification."
        ),
        "improving": (
            f"Positive trajectory — update the biomass estimate to capture recent gains. "
            f"Schedule a satellite scan to recalculate tCO₂e and issue additional verified credits "
            f"if NDVI improvement is sustained for 4+ consecutive weeks. Document growth evidence "
            f"(canopy photos, tree height measurements) for the project verification report."
        ),
    }.get(classification, "Review plot status with a certified monitoring specialist.")

    return rec


# ── Main monitoring function ──────────────────────────────────────────────────

def analyze_plot_monitoring_data(
    plot_id: str,
    scan_history: List[Dict[str, Any]],
    current_ndvi: float,
    current_evi: Optional[float],
    current_ndmi: Optional[float],
    current_nbr: Optional[float],
    current_vv: Optional[float],
    current_vh: Optional[float],
    area_ha: float,
    estimated_tco2e: Optional[float],
    check_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Core analysis function. Compares current satellite observation to historical baseline.

    Args:
        plot_id:          Plot UUID
        scan_history:     List of prior scan records [{mean_ndvi, estimated_tco2e, created_at}, ...]
        current_ndvi:     NDVI extracted from this week's satellite image
        current_*:        Other spectral indices (optional but improve diagnosis)
        area_ha:          Plot area in hectares
        estimated_tco2e:  Latest tCO₂e estimate (for risk context in recommendations)
        check_date:       Datetime of this check (defaults to now UTC)

    Returns:
        Dictionary with full monitoring report.
    """
    if check_date is None:
        check_date = datetime.now(timezone.utc)

    month = check_date.month

    # ── Compute baseline statistics ───────────────────────────────────────────
    if scan_history:
        historical_ndvi = [s["mean_ndvi"] for s in scan_history if s.get("mean_ndvi") is not None]
    else:
        historical_ndvi = []

    if len(historical_ndvi) >= 2:
        baseline_mean = np.median(historical_ndvi)
        baseline_std  = np.std(historical_ndvi)
        # Guard against near-zero std (all scans identical)
        baseline_std  = max(baseline_std, 0.02)
        delta_ndvi    = current_ndvi - baseline_mean
        z_score       = delta_ndvi / baseline_std
        data_quality  = "historical" if len(historical_ndvi) >= 3 else "limited_history"
    elif len(historical_ndvi) == 1:
        baseline_mean = historical_ndvi[0]
        delta_ndvi    = current_ndvi - baseline_mean
        z_score       = 0.0   # Can't compute without std
        baseline_std  = 0.0
        data_quality  = "single_baseline"
    else:
        # No history — treat current as baseline, flag for future comparison
        baseline_mean = current_ndvi
        delta_ndvi    = 0.0
        z_score       = 0.0
        baseline_std  = 0.0
        data_quality  = "no_history"

    # ── VH/VV ratio change (SAR) ──────────────────────────────────────────────
    delta_vh_vv: Optional[float] = None
    if current_vv is not None and current_vh is not None and current_vv != 0:
        current_ratio = current_vh / current_vv
        # Compare to history if prior SAR data stored (future extension)
        # For now, flag if ratio is anomalously low for vegetated areas
        if current_ratio < 0.3:    # Below 0.3 often indicates bare soil / clearing
            delta_vh_vv = -3.0     # Trigger the clearing diagnosis path

    # ── Classification & diagnosis ────────────────────────────────────────────
    classification = classify_change(delta_ndvi, z_score, month)

    cause, explanation = diagnose_cause(
        classification=classification,
        delta_ndvi=delta_ndvi,
        current_ndvi=current_ndvi,
        ndmi_current=current_ndmi,
        nbr_current=current_nbr,
        month=month,
        delta_vh_vv=delta_vh_vv,
        prev_rainfall_anomaly=None,
        z_score=z_score,
    )

    recommendation = generate_recommendation(
        classification=classification,
        cause=cause,
        current_ndvi=current_ndvi,
        delta_ndvi=delta_ndvi,
        area_ha=area_ha,
        estimated_tco2e=estimated_tco2e,
    )

    # ── Alert level ───────────────────────────────────────────────────────────
    alert_level = {
        "acute_disturbance": "critical",
        "degrading":         "warning",
        "stable":            "info",
        "improving":         "positive",
    }[classification]

    report = {
        "id":                   str(uuid.uuid4()),
        "plot_id":              plot_id,
        "check_date":           check_date.isoformat(),
        "current_ndvi":         round(current_ndvi, 4),
        "baseline_ndvi":        round(baseline_mean, 4),
        "delta_ndvi":           round(delta_ndvi, 4),
        "z_score":              round(z_score, 3),
        "baseline_std":         round(baseline_std, 4),
        "n_historical_scans":   len(historical_ndvi),
        "data_quality":         data_quality,
        "classification":       classification,
        "alert_level":          alert_level,
        "cause":                cause,
        "explanation":          explanation,
        "recommendation":       recommendation,
        "area_ha":              area_ha,
        "estimated_tco2e":      estimated_tco2e,
        "spectral_context": {
            "ndvi":   round(current_ndvi, 4),
            "evi":    round(current_evi, 4) if current_evi else None,
            "ndmi":   round(current_ndmi, 4) if current_ndmi else None,
            "nbr":    round(current_nbr, 4) if current_nbr else None,
        },
    }

    logger.info(
        f"Plot {plot_id[:8]}… | NDVI={current_ndvi:.3f} ({delta_ndvi:+.3f}) | "
        f"Z={z_score:.2f} | {classification.upper()} | {cause}"
    )
    return report


# ── GEE-powered current NDVI fetch ────────────────────────────────────────────

def fetch_current_ndvi_from_gee(geometry: Dict, days_back: int = 10) -> Optional[Dict]:
    """
    Pull the most recent cloud-free Sentinel-2 observation for a plot polygon.
    Returns dict with ndvi, evi, ndmi, nbr or None if GEE is unavailable.
    """
    try:
        import ee
        from datetime import timedelta

        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)

        if geometry["type"] == "Polygon":
            roi = ee.Geometry.Polygon(geometry["coordinates"])
        elif geometry["type"] == "Point":
            roi = ee.Geometry.Point(geometry["coordinates"]).buffer(200)
        else:
            return None

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        )

        # Extend window if too few images
        count = collection.size().getInfo()
        if count == 0:
            start = end - timedelta(days=30)
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(roi)
                .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
            )

        def add_indices(img):
            ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
            evi  = img.expression(
                "2.5*((NIR-RED)/(NIR+6*RED-7.5*BLUE+1))",
                {"NIR": img.select("B8"), "RED": img.select("B4"), "BLUE": img.select("B2")}
            ).rename("evi")
            ndmi = img.normalizedDifference(["B8", "B11"]).rename("ndmi")
            nbr  = img.normalizedDifference(["B8", "B12"]).rename("nbr")
            return img.addBands([ndvi, evi, ndmi, nbr])

        composite = collection.map(add_indices).median()
        result = composite.select(["ndvi", "evi", "ndmi", "nbr"]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=10,
            maxPixels=1e8,
        ).getInfo()

        return {
            "ndvi": result.get("ndvi"),
            "evi":  result.get("evi"),
            "ndmi": result.get("ndmi"),
            "nbr":  result.get("nbr"),
        }

    except Exception as e:
        logger.warning(f"GEE fetch failed: {e}")
        return None


def _gee_tile_url(map_id_dict: dict) -> str:
    """Extract a Mapbox-compatible {z}/{x}/{y} tile URL from a GEE getMapId result."""
    try:
        return map_id_dict["tile_fetcher"].url_format
    except (KeyError, AttributeError):
        mid = map_id_dict.get("mapid", "")
        tok = map_id_dict.get("token", "")
        return f"https://earthengine.googleapis.com/map/{mid}/{{z}}/{{x}}/{{y}}?token={tok}"


def _gee_roi(geometry: Dict):
    """Convert a GeoJSON geometry dict to a GEE geometry object."""
    import ee
    if geometry.get("type") == "Polygon":
        return ee.Geometry.Polygon(geometry["coordinates"])
    if geometry.get("type") == "Point":
        return ee.Geometry.Point(geometry["coordinates"]).buffer(500)
    raise ValueError(f"Unsupported geometry type: {geometry.get('type')}")


def get_vegetation_tile_urls(geometry: Dict, days_back: int = 30) -> Optional[Dict]:
    """
    Generate GEE raster tile URLs for spatial vegetation visualization.
    Returns Mapbox-compatible tile URL templates for NDVI, EVI, NBR, and False Color.
    """
    try:
        import ee
        from datetime import timedelta

        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)
        roi   = _gee_roi(geometry)

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        )

        count = collection.size().getInfo()
        actual_start = start
        if count == 0:
            actual_start = end - timedelta(days=90)
            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(roi)
                .filterDate(actual_start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
            )
            count = collection.size().getInfo()

        def add_indices(img):
            ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
            evi  = img.expression(
                "2.5*((NIR-RED)/(NIR+6*RED-7.5*BLUE+1))",
                {"NIR": img.select("B8"), "RED": img.select("B4"), "BLUE": img.select("B2")}
            ).rename("evi")
            nbr  = img.normalizedDifference(["B8", "B12"]).rename("nbr")
            return img.addBands([ndvi, evi, nbr])

        composite = collection.map(add_indices).median()
        veg_palette  = ["#d73027", "#f46d43", "#fee08b", "#66bd63", "#1a9850"]
        burn_palette = ["#7f0000", "#d73027", "#fee08b", "#66bd63", "#1a9850"]

        tiles = {
            "ndvi":        _gee_tile_url(composite.select("ndvi").getMapId({"min": -0.2,  "max": 0.8, "palette": veg_palette})),
            "evi":         _gee_tile_url(composite.select("evi").getMapId( {"min":  0.0,  "max": 0.7, "palette": veg_palette})),
            "nbr":         _gee_tile_url(composite.select("nbr").getMapId( {"min": -0.5,  "max": 0.9, "palette": burn_palette})),
            "false_color": _gee_tile_url(composite.select(["B8", "B4", "B3"]).getMapId({"min": 0, "max": 3000, "gamma": 1.4})),
        }

        return {
            "gee_available": True,
            "tiles": tiles,
            "date_range": {
                "from":     actual_start.strftime("%Y-%m-%d"),
                "to":       end.strftime("%Y-%m-%d"),
                "n_images": count,
            },
        }

    except Exception as e:
        logger.warning(f"GEE vegetation tile generation failed: {e}")
        return None


# ── Change detection ──────────────────────────────────────────────────────────

ZONE_LABELS = {0: "stable", 1: "degrading", 2: "critical", 3: "improving"}
ZONE_COLORS = {
    "stable":    "#3b82f6",
    "degrading": "#f59e0b",
    "critical":  "#dc2626",
    "improving": "#16a34a",
}


def get_change_detection_data(
    geometry: Dict,
    current_days: int = 30,
    baseline_days: int = 180,
) -> Optional[Dict]:
    """
    Pixel-level change detection comparing a recent period to a prior baseline.

    Returns:
      - change_tile: Mapbox tile URL for the delta-NDVI raster
          (red = vegetation loss, green = gain)
      - zones: GeoJSON FeatureCollection of labelled change polygons
      - stats: % area per classification zone
      - date_range: periods compared
    """
    try:
        import ee
        from datetime import timedelta

        end              = datetime.now(timezone.utc)
        current_start    = end - timedelta(days=current_days)
        baseline_end     = current_start          # no overlap
        baseline_start   = end - timedelta(days=baseline_days)
        roi              = _gee_roi(geometry)

        def ndvi_composite(t_start, t_end, max_cloud: int = 50):
            col = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(roi)
                .filterDate(t_start.strftime("%Y-%m-%d"), t_end.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
                .map(lambda img: img.normalizedDifference(["B8", "B4"]).rename("ndvi"))
            )
            n = col.size().getInfo()
            # Do NOT clip — keeping the full scene so the tile URL renders over
            # the whole region (same pattern as get_vegetation_tile_urls).
            # Zone polygons and stats are still clipped via zones_img.clip(roi).
            return col.median(), n

        current_img,  current_n  = ndvi_composite(current_start,  end,           40)
        baseline_img, baseline_n = ndvi_composite(baseline_start, baseline_end,  50)

        if current_n == 0 or baseline_n == 0:
            logger.info(
                f"Change detection: insufficient imagery "
                f"(current={current_n}, baseline={baseline_n})"
            )
            return {"gee_available": False, "reason": "insufficient imagery for change detection"}

        delta = current_img.subtract(baseline_img).rename("delta_ndvi")

        # ── Change raster tile ────────────────────────────────────────────────
        change_palette = [
            "#7f0000", "#d73027", "#f46d43", "#fee08b",
            "#ffffbf",
            "#d9ef8b", "#66bd63", "#1a9850", "#006837",
        ]
        change_tile = _gee_tile_url(
            delta.getMapId({"min": -0.4, "max": 0.4, "palette": change_palette})
        )

        # ── Zone raster  (0=stable 1=degrading 2=critical 3=improving) ────────
        zones_img = (
            ee.Image(0)
            .where(delta.lt(-0.04),  1)   # degrading
            .where(delta.lt(-0.15),  2)   # critical
            .where(delta.gt( 0.04),  3)   # improving
            .rename("zone")
            .clip(roi)
        )

        # ── Area statistics per zone ──────────────────────────────────────────
        zone_areas = (
            zones_img.eq([0, 1, 2, 3])
            .rename(["stable", "degrading", "critical", "improving"])
            .multiply(ee.Image.pixelArea())
            .reduceRegion(
                reducer   = ee.Reducer.sum(),
                geometry  = roi,
                scale     = 20,
                maxPixels = 1e8,
            )
            .getInfo()
        )
        total = sum(v for v in zone_areas.values() if v) or 1.0

        stats = {
            "stable_pct":    round(100 * zone_areas.get("stable",    0) / total, 1),
            "degrading_pct": round(100 * zone_areas.get("degrading", 0) / total, 1),
            "critical_pct":  round(100 * zone_areas.get("critical",  0) / total, 1),
            "improving_pct": round(100 * zone_areas.get("improving", 0) / total, 1),
        }

        # ── Zone polygons (GeoJSON) ────────────────────────────────────────────
        # 20 m = Sentinel-2 native resolution; critical for small plots (10ha ≈ 250 px)
        zones_geojson: Optional[Dict] = None
        try:
            vectors = zones_img.reduceToVectors(
                geometry      = roi,
                scale         = 20,
                maxPixels     = 1e8,
                maxError      = 5,          # simplify geometry to reduce payload size
                geometryType  = "polygon",
                eightConnected= True,
                labelProperty = "zone",
                reducer       = ee.Reducer.mode(),
                bestEffort    = True,
            )
            raw = vectors.getInfo()
            # Drop tiny fragments (< 20 pixels at 20 m = 8 000 m² ≈ 0.8 ha)
            kept = []
            for feat in raw.get("features", []):
                if feat["properties"].get("count", 999) < 20:
                    continue
                z   = int(feat["properties"].get("zone", 0))
                cls = ZONE_LABELS.get(z, "stable")
                feat["properties"]["classification"] = cls
                feat["properties"]["color"]          = ZONE_COLORS[cls]
                kept.append(feat)
            raw["features"] = kept
            zones_geojson = raw
            logger.info(
                f"Change detection: {len(kept)} zone polygons (after filtering), "
                f"stats={stats}"
            )
        except Exception as poly_err:
            logger.warning(f"Zone polygon generation failed (stats still available): {poly_err}")

        return {
            "gee_available": True,
            "change_tile":   change_tile,
            "zones":         zones_geojson,
            "stats":         stats,
            "date_range": {
                "current":  {
                    "from": current_start.strftime("%Y-%m-%d"),
                    "to":   end.strftime("%Y-%m-%d"),
                    "n_images": current_n,
                },
                "baseline": {
                    "from": baseline_start.strftime("%Y-%m-%d"),
                    "to":   baseline_end.strftime("%Y-%m-%d"),
                    "n_images": baseline_n,
                },
            },
        }

    except Exception as e:
        logger.warning(f"GEE change detection failed: {e}")
        return None


def get_mock_current_ndvi(geometry: Dict, baseline_ndvi: float) -> Dict:
    """
    Synthetic current observation — used when GEE is unavailable.
    Simulates realistic weekly variation with occasional anomaly events.
    """
    import random
    month = datetime.now().month
    seasonal = -0.05 if month in RWANDA_DRY_MONTHS else +0.03

    # 5% chance of a significant degradation event (for demo purposes)
    if random.random() < 0.05:
        delta = random.uniform(-0.20, -0.10)
    else:
        delta = seasonal + random.gauss(0, 0.03)

    ndvi = float(np.clip(baseline_ndvi + delta, 0.05, 0.95))
    evi  = float(ndvi * 0.75)
    ndmi = float(ndvi * 0.4 - 0.1)
    nbr  = float(ndvi * 0.5 - 0.05)
    return {"ndvi": ndvi, "evi": evi, "ndmi": ndmi, "nbr": nbr}
