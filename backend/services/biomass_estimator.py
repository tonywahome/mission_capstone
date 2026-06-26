import os
import logging

try:
    import joblib
    import numpy as np
    _ML_AVAILABLE = True
except ImportError:
    _ML_AVAILABLE = False

logger = logging.getLogger(__name__)

_biomass_model_data = None
_integrity_model = None

LAND_USE_ENCODING = {
    "forest": 0,
    "agroforestry": 1,
    "grassland": 2,
    "cropland": 3,
    "wetland": 4,
}


def _load_biomass_model():
    """Load the trained biomass model with scaler."""
    global _biomass_model_data
    if not _ML_AVAILABLE:
        return None
    if _biomass_model_data is None:
        model_path = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "biomass_model_v1.pkl")
        abs_model_path = os.path.abspath(model_path)
        
        logger.info(f"🔍 Attempting to load biomass model...")
        logger.info(f"   Relative path: {model_path}")
        logger.info(f"   Absolute path: {abs_model_path}")
        logger.info(f"   File exists: {os.path.exists(model_path)}")
        
        if os.path.exists(model_path):
            try:
                _biomass_model_data = joblib.load(model_path)
                logger.info(f"✅ Successfully loaded biomass model v1")
                logger.info(f"   Test R²: {_biomass_model_data.get('test_r2', 'N/A')}")
                logger.info(f"   Test RMSE: {_biomass_model_data.get('test_rmse', 'N/A')}")
                logger.info(f"   Features: {len(_biomass_model_data.get('feature_cols', []))}")
                logger.info(f"   Model type: {type(_biomass_model_data.get('model', None)).__name__}")
            except Exception as e:
                logger.error(f"❌ Error loading model file: {type(e).__name__}: {str(e)}")
                logger.error(f"   Full traceback:", exc_info=True)
                _biomass_model_data = None
        else:
            logger.warning(f"❌ Biomass model file not found at {abs_model_path}")
            logger.warning(f"   Current working directory: {os.getcwd()}")
            logger.warning(f"   Directory of this file: {os.path.dirname(__file__)}")
            
            # List what's actually in the models directory
            models_dir = os.path.join(os.path.dirname(__file__), "..", "ml", "models")
            if os.path.exists(models_dir):
                logger.info(f"   Contents of models directory:")
                for item in os.listdir(models_dir):
                    logger.info(f"      - {item}")
            else:
                logger.warning(f"   Models directory does not exist: {models_dir}")
    return _biomass_model_data


def _load_integrity_model():
    global _integrity_model
    if not _ML_AVAILABLE:
        return None
    if _integrity_model is None:
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "ml", "integrity_model.pkl"
        )
        if os.path.exists(model_path):
            _integrity_model = joblib.load(model_path)
    return _integrity_model


def biomass_to_tco2e(biomass_tonnes_per_ha: float, area_hectares: float) -> float:
    carbon_fraction = 0.47  # IPCC default
    co2_ratio = 3.667  # 44/12
    tco2e_per_ha = biomass_tonnes_per_ha * carbon_fraction * co2_ratio
    return round(tco2e_per_ha * area_hectares, 2)


def predict_biomass_from_features(feature_dict: dict) -> dict:
    """
    Predict above-ground biomass using the trained model (proposal Section 3.3.2–3.3.3).

    Supports multi-sensor feature dictionaries with Sentinel-2, Sentinel-1 SAR,
    GEDI LiDAR, and terrain features.  Features absent from the trained model's
    feature list are silently ignored; features required by the model but missing
    from the input raise ValueError.

    Returns a dict with:
        biomass_mean      — point estimate in tonnes/ha
        biomass_lower_90  — lower 90% prediction interval bound
        biomass_upper_90  — upper 90% prediction interval bound
        uncertainty_pct   — (upper-lower) / mean * 100
        model_type        — algorithm used
        model_r2          — spatial CV R² from training
        used_features     — list of feature names used
    """
    logger.info("=" * 60)
    logger.info("BIOMASS PREDICTION")
    logger.info("=" * 60)

    model_data = _load_biomass_model()

    if model_data is None:
        logger.error("❌ FALLBACK MODE: model not loaded — using NDVI heuristic")
        ndvi = feature_dict.get('ndvi', 0.5)
        evi  = feature_dict.get('evi', 0.3)
        rh98 = feature_dict.get('rh98', 0.0)
        biomass = max(5.0, min(400.0, ndvi * 300 + evi * 50 + rh98 * 1.5))
        logger.warning(f"   Fallback: {biomass:.2f} t/ha")
        return {
            "biomass_mean": round(biomass, 2),
            "biomass_lower_90": round(biomass * 0.7, 2),
            "biomass_upper_90": round(biomass * 1.3, 2),
            "uncertainty_pct": 30.0,
            "model_type": "heuristic",
            "model_r2": None,
            "used_features": [],
        }

    logger.info(f"✅ Model: {model_data.get('model_type')}  CV R²={model_data.get('test_r2', 'N/A')}")

    try:
        feature_cols = model_data['feature_cols']
        missing = [c for c in feature_cols if c not in feature_dict]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        X = np.array([[feature_dict[col] for col in feature_cols]])
        X_scaled = model_data['scaler'].transform(X)

        use_log1p = model_data.get('target_transform') == 'log1p'
        model = model_data['model']

        # Point estimate
        raw_pred = model.predict(X_scaled)[0]
        biomass_mean = float(np.expm1(raw_pred) if use_log1p else raw_pred)
        biomass_mean = max(1.0, min(500.0, biomass_mean))

        # Uncertainty quantification via prediction intervals
        # RF: spread of individual tree predictions; others: use model CV RMSE
        trees = model_data.get('uncertainty_trees')
        if trees is not None:
            # RF — use individual tree preds to compute percentile interval
            tree_preds = np.array([t.predict(X_scaled)[0] for t in trees])
            if use_log1p:
                tree_preds = np.expm1(tree_preds)
            lower = float(np.percentile(tree_preds, 5))
            upper = float(np.percentile(tree_preds, 95))
        else:
            # Non-RF: fall back to ±1.645σ using CV RMSE as proxy for std
            cv_rmse = model_data.get('test_rmse', biomass_mean * 0.25)
            lower = max(0.0, biomass_mean - 1.645 * cv_rmse)
            upper = biomass_mean + 1.645 * cv_rmse

        lower = max(0.0, lower)
        uncertainty_pct = round((upper - lower) / max(biomass_mean, 1.0) * 100, 1)

        logger.info(
            f"✅ {biomass_mean:.2f} t/ha  "
            f"[90% PI: {lower:.1f}–{upper:.1f}]  "
            f"uncertainty={uncertainty_pct}%  "
            f"NDVI={feature_dict.get('ndvi', 'N/A')}"
        )
        logger.info("=" * 60)

        return {
            "biomass_mean": round(biomass_mean, 2),
            "biomass_lower_90": round(lower, 2),
            "biomass_upper_90": round(upper, 2),
            "uncertainty_pct": uncertainty_pct,
            "model_type": model_data.get('model_type', 'unknown'),
            "model_r2": model_data.get('test_r2'),
            "used_features": feature_cols,
        }

    except Exception as e:
        logger.error(f"❌ Prediction error: {e}", exc_info=True)
        ndvi = feature_dict.get('ndvi', 0.5)
        biomass = round(float(max(5.0, min(400.0, ndvi * 300))), 2)
        logger.warning(f"   Fallback: {biomass:.2f} t/ha")
        logger.info("=" * 60)
        return {
            "biomass_mean": biomass,
            "biomass_lower_90": round(biomass * 0.7, 2),
            "biomass_upper_90": round(biomass * 1.3, 2),
            "uncertainty_pct": 30.0,
            "model_type": "heuristic",
            "model_r2": None,
            "used_features": [],
        }


def estimate_biomass(
    ndvi: float,
    evi: float,
    elevation: float,
    slope: float,
    precip: float,
    land_use: str,
) -> float:
    """Legacy function for backward compatibility. Use predict_biomass_from_features for real predictions."""
    model_data = _load_biomass_model()
    land_type = LAND_USE_ENCODING.get(land_use, 2)

    # Fallback formula if model not trained yet
    biomass = ndvi * 300 + evi * 50 + (precip - 800) / 1200 * 40 - slope * 0.5
    return round(float(max(5.0, min(350.0, biomass))), 2)


def calculate_integrity_score(
    ndvi_mean: float,
    ndvi_std: float,
    temporal_ndvi_change: float,
    cloud_cover_pct: float,
    scan_resolution_m: float,
    biomass_model_r2: float,
    drought_risk: float,
    wildfire_risk: float,
    deforestation_proximity_km: float,
    years_under_conservation: float,
    land_use: str,
    additionality_score: float,
) -> float:
    model = _load_integrity_model()
    land_type = LAND_USE_ENCODING.get(land_use, 2)

    if model is not None and _ML_AVAILABLE:
        features = np.array(
            [
                [
                    ndvi_mean,
                    ndvi_std,
                    temporal_ndvi_change,
                    cloud_cover_pct,
                    scan_resolution_m,
                    biomass_model_r2,
                    drought_risk,
                    wildfire_risk,
                    deforestation_proximity_km,
                    years_under_conservation,
                    land_type,
                    additionality_score,
                ]
            ]
        )
        score = model.predict(features)[0]
        return round(float(max(0.0, min(100.0, score))), 1)

    # Fallback rule-based calculation
    data_quality = (
        min(ndvi_mean / 0.8, 1.0) * 15
        + max(0, 1 - ndvi_std / 0.2) * 5
        + max(0, 1 - cloud_cover_pct / 100) * 5
        + max(0, 1 - scan_resolution_m / 60) * 5
    )
    model_conf = biomass_model_r2 * 20
    temporal = (
        max(0, 1 - abs(temporal_ndvi_change) / 0.3) * 10
        + min(years_under_conservation / 10, 1.0) * 10
    )
    risk_adj = (
        (1 - drought_risk) * 5
        + (1 - wildfire_risk) * 5
        + min(deforestation_proximity_km / 30, 1.0) * 5
    )
    additionality = additionality_score * 15
    score = data_quality + model_conf + temporal + risk_adj + additionality
    return round(float(max(0.0, min(100.0, score))), 1)
