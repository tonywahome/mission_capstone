import random

BAND_PROFILES = {
    "forest": {"B2": 0.03, "B3": 0.05, "B4": 0.03, "B8": 0.40, "B11": 0.15, "B12": 0.08},
    "agroforestry": {"B2": 0.04, "B3": 0.06, "B4": 0.05, "B8": 0.35, "B11": 0.18, "B12": 0.10},
    "grassland": {"B2": 0.05, "B3": 0.08, "B4": 0.06, "B8": 0.28, "B11": 0.22, "B12": 0.15},
    "cropland": {"B2": 0.06, "B3": 0.09, "B4": 0.07, "B8": 0.25, "B11": 0.20, "B12": 0.14},
    "wetland": {"B2": 0.04, "B3": 0.06, "B4": 0.04, "B8": 0.32, "B11": 0.25, "B12": 0.18},
}

REGION_ELEVATION = {
    "Nyeri": {"elevation": 1800, "slope": 12, "precip": 1200},
    "Laikipia": {"elevation": 2200, "slope": 8, "precip": 700},
    "Murang'a": {"elevation": 1600, "slope": 15, "precip": 1500},
    "Nyandarua": {"elevation": 2500, "slope": 10, "precip": 1100},
}


def generate_mock_bands(land_use: str) -> dict:
    profile = BAND_PROFILES.get(land_use, BAND_PROFILES["grassland"])
    return {k: round(v + random.gauss(0, v * 0.1), 4) for k, v in profile.items()}


def calculate_ndvi(bands: dict) -> float:
    b4 = bands.get("B4", 0.05)
    b8 = bands.get("B8", 0.30)
    if (b8 + b4) == 0:
        return 0
    return round((b8 - b4) / (b8 + b4), 4)


def calculate_evi(bands: dict) -> float:
    b2 = bands.get("B2", 0.04)
    b4 = bands.get("B4", 0.05)
    b8 = bands.get("B8", 0.30)
    denominator = b8 + 6 * b4 - 7.5 * b2 + 1
    if denominator == 0:
        return 0
    return round(2.5 * (b8 - b4) / denominator, 4)


def get_terrain_data(region: str) -> dict:
    base = REGION_ELEVATION.get(region, {"elevation": 1800, "slope": 10, "precip": 1000})
    return {
        "elevation": base["elevation"] + random.uniform(-200, 200),
        "slope": base["slope"] + random.uniform(-3, 3),
        "precip": base["precip"] + random.uniform(-150, 150),
    }
