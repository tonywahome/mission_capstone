"""
GEDI L4B baseline biomass lookup.

First scan for a plot: query GEDI L4B (LARSE/GEDI/GEDI04_B_002) to get a
certified wall-to-wall biomass estimate at the plot location. This value is
stored as land_plots.baseline_agbd and used as the reference for all future
delta-based estimates.

GEDI L4B is a global 1 km continuous AGBD map derived from all GEDI waveform
shots (2019-2023). It is scientifically validated and accepted by Verra / Gold
Standard as a biomass reference layer — no custom ML needed.

Falls back to an elevation-based Rwanda forest estimate when GEE is unavailable.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

from services.gee_init import initialize_gee
_GEE_AVAILABLE = initialize_gee()


# ── Rwanda elevation → biomass lookup (fallback when GEE is offline) ──────────
# Based on published allometric studies for East African montane forests.
# Nyungwe / Volcanoes NP at 1800-2800 m elevation: 120-300 t/ha
# Lower highland forests at 1400-1800 m: 50-120 t/ha
_ELEVATION_AGBD = [
    (2500, 280.0),
    (2200, 220.0),
    (1900, 160.0),
    (1600, 100.0),
    (1300,  60.0),
    (   0,  30.0),
]


def _elevation_fallback(elevation_m: Optional[float]) -> float:
    """Return a coarse Rwanda-calibrated AGBD estimate from elevation."""
    elev = elevation_m or 1600.0
    for threshold, agbd in _ELEVATION_AGBD:
        if elev >= threshold:
            return agbd
    return 30.0


def _geojson_to_ee_geometry(geometry: Dict):
    """Convert a GeoJSON geometry dict to an EE geometry with a 500 m buffer for points."""
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    if geom_type == "Point":
        return ee.Geometry.Point(coords).buffer(500)
    if geom_type == "Polygon":
        return ee.Geometry.Polygon(coords)
    if geom_type == "MultiPolygon":
        return ee.Geometry.MultiPolygon(coords)
    raise ValueError(f"Unsupported geometry type: {geom_type}")


def fetch_gedi_baseline(
    geometry: Dict,
    elevation_m: Optional[float] = None,
) -> Dict:
    """
    Fetch the GEDI L4B mean AGBD for a plot geometry.

    Returns a dict:
        {
            "agbd":   float,   # above-ground biomass density (t/ha)
            "source": str,     # "gedi_l4b" | "elevation_fallback"
            "note":   str,     # human-readable provenance string
        }

    Never raises — always returns a usable estimate.
    """
    if _GEE_AVAILABLE:
        try:
            ee_geom = _geojson_to_ee_geometry(geometry)

            gedi_l4b = ee.Image("LARSE/GEDI/GEDI04_B_002")

            # Quality-filtered mean: mask quality_flag == 0 pixels before averaging
            qf    = gedi_l4b.select("QF")
            agbd  = gedi_l4b.select("MU").updateMask(qf.gt(0))

            result = agbd.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geom,
                scale=1000,
                maxPixels=1_000_000,
            ).getInfo()

            value = result.get("MU")
            if value is not None and value > 0:
                logger.info(f"GEDI L4B baseline: {value:.1f} t/ha")
                return {
                    "agbd":   round(float(value), 2),
                    "source": "gedi_l4b",
                    "note":   "GEDI L4B 2019-2023 composite (LARSE/GEDI/GEDI04_B_002)",
                }

            logger.warning("GEDI L4B returned no valid pixels for this geometry — using elevation fallback")

        except Exception as exc:
            logger.warning(f"GEDI L4B query failed: {exc} — using elevation fallback")

    # GEE unavailable or no valid pixels
    agbd = _elevation_fallback(elevation_m)
    logger.info(f"Elevation-based baseline: {agbd:.1f} t/ha  (elevation={elevation_m} m)")
    return {
        "agbd":   agbd,
        "source": "elevation_fallback",
        "note":   f"Rwanda elevation lookup (elev={elevation_m or 'unknown'} m) — update when GEE is available",
    }
