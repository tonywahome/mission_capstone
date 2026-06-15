from fastapi import APIRouter
from models.risk import FootprintRequest, FootprintResponse
from services.carbon_calculator import calculate_footprint

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.post("/footprint", response_model=FootprintResponse)
async def calculate_carbon_footprint(request: FootprintRequest):
    result = calculate_footprint(
        energy_kwh_monthly=request.energy_kwh_monthly,
        fuel_litres_monthly=request.fuel_litres_monthly,
        fuel_type=request.fuel_type,
        natural_gas_m3_monthly=request.natural_gas_m3_monthly,
        refrigerant_leaked_kg_annual=request.refrigerant_leaked_kg_annual,
        flights_short_km_annual=request.flights_short_km_annual,
        flights_long_km_annual=request.flights_long_km_annual,
        waste_landfill_kg_monthly=request.waste_landfill_kg_monthly,
        waste_recycled_kg_monthly=request.waste_recycled_kg_monthly,
        water_m3_monthly=request.water_m3_monthly,
        freight_tonne_km_monthly=request.freight_tonne_km_monthly,
        freight_sea_tonne_km_monthly=request.freight_sea_tonne_km_monthly,
        supply_chain_spend_usd_monthly=request.supply_chain_spend_usd_monthly,
    )
    return FootprintResponse(**result)
