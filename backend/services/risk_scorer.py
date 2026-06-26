import random

# Illustrative weather profiles for the capstone's two pilot districts.
# These are NOT sourced from a real meteorological dataset (e.g. CHIRPS or
# the Rwanda Meteorology Agency) — they are directionally-reasonable
# placeholders (Bugesera: lower-altitude Eastern Province savanna/grassland,
# drier and more drought-prone; Rulindo: higher-altitude Northern Province
# agroforestry, wetter and less fire-prone) standing in until a real climate
# data source is integrated. This mirrors the same "illustrative, not
# fabricated training data" labeling used in sample_plots.geojson's `_meta`
# block — see backend/ml/README.md "Next Steps" for the equivalent gap on
# the biomass side.
WEATHER_PROFILES = {
    "Bugesera": {
        "avg_temp": 21,
        "precip_mm": 900,
        "drought_index": 0.45,
        "fire_events_5yr": 2,
    },
    "Rulindo": {
        "avg_temp": 18,
        "precip_mm": 1300,
        "drought_index": 0.15,
        "fire_events_5yr": 0,
    },
}

DEFORESTATION_RISK_BY_LAND_USE = {
    "forest": 0.3,
    "agroforestry": 0.15,
    "grassland": 0.05,
    "cropland": 0.02,
    "wetland": 0.1,
}


def get_weather_data(region: str) -> dict:
    """Look up an illustrative weather profile for a region string.

    `region` is typically a free-text reverse-geocoded location (e.g.
    "Nyamata, Bugesera, Rwanda"), not an exact district name, so this
    matches by case-insensitive substring against the two in-scope
    districts (IN_SCOPE_DISTRICTS in models/land_plot.py) rather than an
    exact dict-key lookup. Anything that doesn't mention Bugesera or
    Rulindo — including legacy/out-of-scope region strings — falls back to
    a randomly generated profile, same as before.
    """
    region_lower = (region or "").lower()
    profile = None
    if "bugesera" in region_lower:
        profile = WEATHER_PROFILES["Bugesera"]
    elif "rulindo" in region_lower:
        profile = WEATHER_PROFILES["Rulindo"]

    if profile is None:
        # Generate random profile for unmatched regions
        profile = {
            "avg_temp": random.uniform(14, 25),
            "precip_mm": random.uniform(600, 1800),
            "drought_index": random.uniform(0.1, 0.7),
            "fire_events_5yr": random.randint(0, 5),
        }
    return profile


def calculate_risk_score(weather_data: dict, land_use: str) -> dict:
    drought_risk = weather_data.get("drought_index", 0.3)
    wildfire_risk = min(weather_data.get("fire_events_5yr", 2) / 10, 1.0)
    deforestation_risk = DEFORESTATION_RISK_BY_LAND_USE.get(land_use, 0.1)
    political_risk = 0.1  # constant for demo

    composite = (
        drought_risk * 0.3
        + wildfire_risk * 0.3
        + deforestation_risk * 0.25
        + political_risk * 0.15
    )

    return {
        "drought_risk": round(drought_risk, 3),
        "wildfire_risk": round(wildfire_risk, 3),
        "deforestation_risk": round(deforestation_risk, 3),
        "political_risk": round(political_risk, 3),
        "composite_risk": round(composite, 3),
    }
