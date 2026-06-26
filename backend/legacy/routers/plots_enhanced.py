"""
Updated plots router with integrated carbon credit engine.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.carbon_credit_engine import CarbonCreditEngine
import logging

router = APIRouter(prefix="/api/plots", tags=["plots"])
logger = logging.getLogger(__name__)

# Initialize the engine (will use trained model when available)
credit_engine = CarbonCreditEngine(
    biomass_model_path="backend/ml/models/biomass_model_v1.pkl"
)


class PlotAnalysisRequest(BaseModel):
    lat: float
    lon: float
    buffer_m: float = 1000
    project_name: str = "Unnamed Project"


class PlotAnalysisResponse(BaseModel):
    project_name: str
    location: dict
    forest_segmentation: dict
    biomass_estimation: dict
    carbon_stock: dict
    risk_assessment: dict
    final_credits: dict
    integrity_score: float


@router.post("/analyze", response_model=PlotAnalysisResponse)
async def analyze_plot(request: PlotAnalysisRequest):
    """
    Complete carbon credit analysis for a plot.
    
    This endpoint:
    1. Segments forest cover from satellite imagery
    2. Estimates biomass using trained ML model
    3. Calculates carbon stock (tCO₂e)
    4. Assesses risk factors
    5. Issues adjusted carbon credits
    """
    try:
        logger.info(f"Analyzing plot: {request.project_name}")
        
        result = credit_engine.process_plot(
            lat=request.lat,
            lon=request.lon,
            buffer_m=request.buffer_m,
            project_name=request.project_name
        )
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return result
        
    except Exception as e:
        logger.error(f"Plot analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sample-analysis")
async def get_sample_analysis():
    """
    Get a sample analysis (for demo purposes).
    """
    # Use a Congo Basin location
    result = credit_engine.process_plot(
        lat=-18.213,
        lon=12.770,
        buffer_m=5000,
        project_name="Congo Basin Sample"
    )
    
    return result


@router.post("/quick-estimate")
async def quick_carbon_estimate(
    mean_biomass: float,
    forest_area_ha: float
):
    """
    Quick carbon stock calculation from known biomass.
    
    Args:
        mean_biomass: Average biomass density (tonnes/ha)
        forest_area_ha: Forest area (hectares)
    """
    carbon_data = credit_engine.calculate_carbon_stock(
        mean_biomass_tonnes_per_ha=mean_biomass,
        forest_area_ha=forest_area_ha
    )
    
    return {
        **carbon_data,
        'estimated_credits_range': {
            'conservative': round(carbon_data['carbon_stock_tco2e'] * 0.7, 2),
            'moderate': round(carbon_data['carbon_stock_tco2e'] * 0.85, 2),
            'optimistic': round(carbon_data['carbon_stock_tco2e'] * 0.95, 2)
        }
    }
