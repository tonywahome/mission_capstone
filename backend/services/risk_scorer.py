import random

WEATHER_PROFILES = {
    "Nyeri": {
        "avg_temp": 18,
        "precip_mm": 1200,
        "drought_index": 0.2,
        "fire_events_5yr": 1,
    },
    "Laikipia": {
        "avg_temp": 22,
        "precip_mm": 700,
        "drought_index": 0.6,
        "fire_events_5yr": 4,
    },
    "Murang'a": {
        "avg_temp": 19,
        "precip_mm": 1500,
        "drought_index": 0.15,
        "fire_events_5yr": 0,
    },
    "Nyandarua": {
        "avg_temp": 14,
        "precip_mm": 1100,
        "drought_index": 0.25,
        "fire_events_5yr": 2,
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
    profile = WEATHER_PROFILES.get(region)
    if profile is None:
        # Generate random profile for unknown regions
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
