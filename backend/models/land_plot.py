from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Proposal scope (Section 1.5 / 3.3.1): two validation strata only —
# "agroforestry" (Rulindo district) and "grassland" (savanna/grassland,
# Bugesera district). "forest", "cropland", "wetland" are retained as
# allowed values for backward compatibility with existing sample data and
# the Section 3.3.2 model's training feature space, but are not part of
# the capstone's active field-validation sample.
IN_SCOPE_LAND_USE = ("agroforestry", "grassland")
ALL_LAND_USE = ("forest", "agroforestry", "grassland", "cropland", "wetland")

# Districts covered by the revised proposal's purposive field sample.
IN_SCOPE_DISTRICTS = ("Bugesera", "Rulindo")


class LandPlotCreate(BaseModel):
    name: str
    owner_id: str
    geometry: dict  # GeoJSON Polygon
    area_hectares: float
    region: Optional[str] = None
    district: Optional[str] = None  # e.g. "Bugesera" or "Rulindo"
    land_use: str = "grassland"


class LandPlotResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    geometry: dict
    area_hectares: float
    region: Optional[str] = None
    district: Optional[str] = None
    land_use: str
    created_at: Optional[str] = None
