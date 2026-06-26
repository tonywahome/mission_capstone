"""
Google Earth Engine feature extraction for real-time biomass estimation.

Per research proposal Section 3.3.1, extracts multi-sensor features:
  - Sentinel-2 multispectral: spectral bands + vegetation indices (NDVI, EVI, SAVI, NDMI, NBR)
  - Sentinel-1 SAR: VV and VH backscatter + VH-VV difference (C-band, Copernicus)
  - GEDI LiDAR: rh50, rh75, rh98 canopy height percentiles and cover fraction
  - Terrain: elevation and slope from SRTM

Falls back to synthetic mock data when the earthengine-api package is not
installed or GEE credentials are not configured.
"""

import logging
import random
from typing import Dict, Optional

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    _NP_AVAILABLE = False

logger = logging.getLogger(__name__)

from services.gee_init import initialize_gee
_GEE_AVAILABLE = initialize_gee()


def _mock_features(geometry: Dict) -> Dict:
    """
    Generate synthetic multi-sensor features when GEE is unavailable.
    Includes Sentinel-2, Sentinel-1 SAR, GEDI LiDAR, and terrain.
    """
    from services.mock_data import generate_mock_bands
    # Infer land use from geometry centroid latitude (Rwanda heuristic)
    land_use = "agroforestry"
    try:
        coords = geometry.get("coordinates", [[]])
        if geometry.get("type") == "Polygon":
            flat = [c for ring in coords for c in ring]
        else:
            flat = [coords]
        lat = sum(c[1] for c in flat) / len(flat) if flat else -1.9  # Kigali default
        land_use = "grassland" if lat > -1.5 else "agroforestry" if lat > -2.5 else "forest"
    except Exception:
        pass

    _rng = np.random if _NP_AVAILABLE else None
    def rng(lo, hi): return float(_rng.uniform(lo, hi) if _rng else random.uniform(lo, hi))

    bands = generate_mock_bands(land_use)
    ndvi = bands.get("NDVI", 0.65)
    evi  = bands.get("EVI", ndvi * 0.6)
    nir  = bands.get("B8", 0.35)
    swir1 = bands.get("B11", 0.18)
    swir2 = bands.get("B12", 0.10)

    # Sentinel-1 SAR mock values (dB scale; typical savanna/agroforestry values)
    vv = round(rng(-14.0, -8.0), 4)
    vh = round(rng(-22.0, -14.0), 4)

    # GEDI LiDAR mock values (typical agroforestry heights in metres)
    rh50 = round(rng(3.0, 12.0), 2)
    rh75 = round(rng(rh50, rh50 + 6.0), 2)
    rh98 = round(rng(rh75, rh75 + 8.0), 2)
    cover = round(rng(0.3, 0.85), 3)

    return {
        # Sentinel-2
        "blue":      bands.get("B2", 0.05),
        "green":     bands.get("B3", 0.08),
        "red":       bands.get("B4", 0.06),
        "nir":       nir,
        "swir1":     swir1,
        "swir2":     swir2,
        "ndvi":      ndvi,
        "evi":       evi,
        "savi":      round(ndvi * 0.85, 4),
        "ndmi":      round((nir - swir1) / (nir + swir1 + 1e-9), 4),
        "nbr":       round((nir - swir2) / (nir + swir2 + 1e-9), 4),
        # Sentinel-1 SAR
        "vv":        vv,
        "vh":        vh,
        "vh_vv_diff": round(vh - vv, 4),
        # GEDI LiDAR
        "rh50":      rh50,
        "rh75":      rh75,
        "rh98":      rh98,
        "cover":     cover,
        # Terrain
        "elevation": round(rng(1400, 2600), 1),  # Rwanda highland range
        "slope":     round(rng(2, 22), 2),
        "n_images":  0,
    }


def calculate_indices(image):
    """Calculate vegetation indices from Sentinel-2 bands (requires GEE)."""
    if not _GEE_AVAILABLE:
        return image
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi')
    evi = image.expression(
        '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
        {'NIR': image.select('B8'), 'RED': image.select('B4'), 'BLUE': image.select('B2')}
    ).rename('evi')
    savi = image.expression(
        '((NIR - RED) / (NIR + RED + 0.5)) * 1.5',
        {'NIR': image.select('B8'), 'RED': image.select('B4')}
    ).rename('savi')
    ndmi = image.normalizedDifference(['B8', 'B11']).rename('ndmi')
    nbr  = image.normalizedDifference(['B8', 'B12']).rename('nbr')
    return image.addBands([ndvi, evi, savi, ndmi, nbr])


def _extract_sar_features(ee_geometry, region, start_date: str, end_date: str) -> Dict:
    """
    Extract Sentinel-1 SAR backscatter features (VV, VH) via GEE.
    Returns empty dict if no imagery available.
    """
    try:
        s1 = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(ee_geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            .select(["VV", "VH"])
        )
        count = s1.size().getInfo()
        if count == 0:
            logger.warning("No Sentinel-1 images found for this geometry/date range")
            return {}
        composite = s1.median()
        vals = composite.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10,
            maxPixels=1e9,
        ).getInfo()
        vv = vals.get("VV")
        vh = vals.get("VH")
        if vv is None or vh is None:
            return {}
        return {"vv": vv, "vh": vh, "vh_vv_diff": vh - vv}
    except Exception as e:
        logger.warning(f"SAR extraction failed: {e}")
        return {}


def _extract_gedi_features(ee_geometry, region) -> Dict:
    """
    Extract GEDI L4A above-ground biomass density and canopy metrics via GEE.
    Returns empty dict if no data available over the region.
    """
    try:
        gedi = (
            ee.ImageCollection("LARSE/GEDI/GEDI04_A_002_MONTHLY")
            .filterBounds(ee_geometry)
            .select(["agbd", "elev_lowestmode"])
        )
        count = gedi.size().getInfo()
        if count == 0:
            logger.warning("No GEDI L4A data found for this geometry")
            return {}
        composite = gedi.mean()
        vals = composite.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=25,
            maxPixels=1e9,
        ).getInfo()

        # GEDI canopy height from L2A product
        gedi_l2a = (
            ee.ImageCollection("LARSE/GEDI/GEDI02_A_002_MONTHLY")
            .filterBounds(ee_geometry)
            .select(["rh50", "rh75", "rh98", "cover"])
        )
        height_composite = gedi_l2a.mean()
        height_vals = height_composite.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=25,
            maxPixels=1e9,
        ).getInfo()

        out = {}
        for k in ["rh50", "rh75", "rh98", "cover"]:
            if height_vals.get(k) is not None:
                out[k] = height_vals[k]
        return out
    except Exception as e:
        logger.warning(f"GEDI extraction failed: {e}")
        return {}


def extract_sentinel_features(
    geometry: Dict,
    start_date: str = "2023-01-01",
    end_date: str = "2024-12-31",
    scale: int = 10
) -> Optional[Dict]:
    """
    Extract multi-sensor features for a geometry (proposal Section 3.3.1):
      - Sentinel-2 optical bands + vegetation indices
      - Sentinel-1 SAR backscatter (VV, VH)
      - GEDI LiDAR canopy height + cover
      - SRTM terrain (elevation, slope)

    Falls back to synthetic mock features when GEE is unavailable.
    """
    if not _GEE_AVAILABLE:
        logger.info("GEE unavailable — returning synthetic mock features")
        return _mock_features(geometry)

    try:
        # Convert GeoJSON to EE geometry
        if geometry['type'] == 'Point':
            coords = geometry['coordinates']
            ee_geometry = ee.Geometry.Point(coords)
            region = ee_geometry.buffer(50)
        elif geometry['type'] == 'Polygon':
            coords = geometry['coordinates']
            ee_geometry = ee.Geometry.Polygon(coords)
            region = ee_geometry
        else:
            logger.error(f"Unsupported geometry type: {geometry['type']}")
            return None

        # ── Sentinel-2 ────────────────────────────────────────────────────────
        collection = (
            ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(ee_geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            .map(calculate_indices)
        )
        count = collection.size().getInfo()
        if count == 0:
            logger.warning("No Sentinel-2 images found for geometry")
            return None
        logger.info(f"Sentinel-2: {count} cloud-free images")
        composite = collection.median()
        s2_sample = composite.select([
            'B2', 'B3', 'B4', 'B8', 'B11', 'B12',
            'ndvi', 'evi', 'savi', 'ndmi', 'nbr'
        ]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=scale,
            maxPixels=1e9,
        ).getInfo()

        # ── Terrain (SRTM) ────────────────────────────────────────────────────
        dem = ee.Image('USGS/SRTMGL1_003')
        terrain_vals = ee.Image.cat([
            dem.select('elevation'),
            ee.Terrain.slope(dem),
        ]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=30,
            maxPixels=1e9,
        ).getInfo()

        features = {
            'blue':      s2_sample.get('B2'),
            'green':     s2_sample.get('B3'),
            'red':       s2_sample.get('B4'),
            'nir':       s2_sample.get('B8'),
            'swir1':     s2_sample.get('B11'),
            'swir2':     s2_sample.get('B12'),
            'ndvi':      s2_sample.get('ndvi'),
            'evi':       s2_sample.get('evi'),
            'savi':      s2_sample.get('savi'),
            'ndmi':      s2_sample.get('ndmi'),
            'nbr':       s2_sample.get('nbr'),
            'elevation': terrain_vals.get('elevation'),
            'slope':     terrain_vals.get('slope'),
            'n_images':  count,
        }

        if any(v is None for k, v in features.items() if k != 'n_images'):
            logger.error(f"Missing Sentinel-2/terrain values: {features}")
            return None

        # ── Sentinel-1 SAR ───────────────────────────────────────────────────
        sar = _extract_sar_features(ee_geometry, region, start_date, end_date)
        if sar:
            features.update(sar)
            logger.info(f"SAR: VV={sar['vv']:.2f} dB  VH={sar['vh']:.2f} dB")
        else:
            logger.warning("SAR features unavailable — omitting from feature vector")

        # ── GEDI LiDAR ────────────────────────────────────────────────────────
        gedi = _extract_gedi_features(ee_geometry, region)
        if gedi:
            features.update(gedi)
            logger.info(f"GEDI: rh98={gedi.get('rh98', 'N/A')}  cover={gedi.get('cover', 'N/A')}")
        else:
            logger.warning("GEDI features unavailable — omitting from feature vector")

        logger.info(
            f"Features extracted: NDVI={features['ndvi']:.3f}  "
            f"Elevation={features['elevation']:.1f}m  "
            f"Sensors: S2={'yes'}, SAR={'yes' if sar else 'no'}, GEDI={'yes' if gedi else 'no'}"
        )
        return features

    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        return None


def features_to_array(features: Dict):
    """
    Convert feature dictionary to numpy array in correct order for model.
    
    Args:
        features: Dictionary with feature names and values
        
    Returns:
        1D numpy array with 13 features in training order
    """
    feature_order = [
        'blue', 'green', 'red', 'nir', 'swir1', 'swir2',
        'ndvi', 'evi', 'savi', 'ndmi', 'nbr',
        'elevation', 'slope'
    ]
    
    if _NP_AVAILABLE:
        return np.array([features[name] for name in feature_order])
    return [features[name] for name in feature_order]
