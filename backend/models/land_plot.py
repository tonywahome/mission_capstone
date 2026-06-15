from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LandPlotCreate(BaseModel):
    name: str
    owner_id: str
    geometry: dict  # GeoJSON Polygon
    area_hectares: float
    region: Optional[str] = None
    land_use: str = "forest"


class LandPlotResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    geometry: dict
    area_hectares: float
    region: Optional[str] = None
    land_use: str
    created_at: Optional[str] = None
