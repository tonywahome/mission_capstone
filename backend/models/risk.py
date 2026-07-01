from pydantic import BaseModel
from typing import Optional


class RiskAssessment(BaseModel):
    plot_id: str
    drought_risk: float
    wildfire_risk: float
    deforestation_risk: float
    political_risk: float
    composite_risk: float
    weather_data: Optional[dict] = None


class RiskAssessmentResponse(RiskAssessment):
    id: str
    assessment_date: Optional[str] = None


class ScanRequest(BaseModel):
    plot_id: Optional[str] = None
    geometry: Optional[dict] = None  # GeoJSON Polygon
    owner_id: str


class ScanResponse(BaseModel):
    scan_id: str
    plot_id: Optional[str] = None
    mean_ndvi: float
    mean_evi: float
    vegetation_cover_pct: float
    estimated_biomass: float
    # Uncertainty quantification — per research proposal Section 3.3.2
    biomass_lower_90: Optional[float] = None
    biomass_upper_90: Optional[float] = None
    biomass_uncertainty_pct: Optional[float] = None
    estimated_tco2e: float
    carbon_density: float
    integrity_score: float
    buy_price_per_tonne: float
    risk_adjustment: float
    raw_bands: Optional[dict] = None
    sensors_used: Optional[dict] = None  # which sensor sources contributed


class FootprintRequest(BaseModel):
    # Scope 2 — Purchased electricity
    energy_kwh_monthly: float = 0
    # Scope 1 — Direct fuel combustion
    fuel_litres_monthly: float = 0
    fuel_type: str = "diesel"                  # diesel | petrol | natural_gas | lpg
    # Scope 1 — Natural gas for heating
    natural_gas_m3_monthly: float = 0
    # Scope 1 — Refrigerant leakage (R-410A, GWP 2088)
    refrigerant_leaked_kg_annual: float = 0
    # Scope 3 — Business air travel
    flights_short_km_annual: float = 0         # < 1500 km
    flights_long_km_annual: float = 0          # > 1500 km
    # Scope 3 — Waste
    waste_landfill_kg_monthly: float = 0
    waste_recycled_kg_monthly: float = 0
    # Scope 3 — Water
    water_m3_monthly: float = 0
    # Scope 3 — Freight
    freight_tonne_km_monthly: float = 0        # Road/truck
    freight_sea_tonne_km_monthly: float = 0    # Sea/container shipping
    # Scope 3 — Supply chain spend-based
    supply_chain_spend_usd_monthly: float = 0
    industry_sector: Optional[str] = None


class FootprintResponse(BaseModel):
    annual_tco2e: float
    monthly_tco2e: float
    # GHG Protocol scope totals
    scope1_tco2e: float
    scope2_tco2e: float
    scope3_tco2e: float
    # Individual source breakdowns
    electricity_tco2e: float
    fuel_tco2e: float
    natural_gas_tco2e: float
    refrigerant_tco2e: float
    flights_tco2e: float
    waste_tco2e: float
    water_tco2e: float
    freight_tco2e: float
    freight_sea_tco2e: float
    supply_chain_tco2e: float
    breakdown: dict
