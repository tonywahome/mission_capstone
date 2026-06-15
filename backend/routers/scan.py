import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from models.risk import ScanRequest, ScanResponse
from services.biomass_estimator import predict_biomass_from_features, biomass_to_tco2e, calculate_integrity_score
from services.risk_scorer import calculate_risk_score, get_weather_data
from services.gee_feature_extractor import extract_sentinel_features
from services.carbon_calculator import calculate_credit_price
from services.location_service import get_location_from_geometry, get_centroid_from_geometry
from database import get_supabase_client, get_admin_client
import random

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("", response_model=ScanResponse)
async def run_scan(request: ScanRequest):
    logger.info(f"Processing scan request for owner: {request.owner_id}")
    
    # Convert "demo-user" string to proper UUID
    DEMO_USER_UUID = "00000000-0000-0000-0000-000000000001"
    owner_id = DEMO_USER_UUID if request.owner_id == "demo-user" else request.owner_id
    
    # Extract location from geometry
    location = get_location_from_geometry(request.geometry)
    logger.info(f"Extracted location: {location}")
    
    # Try to get plot details from database if available, or create one
    plot = None
    plot_id = request.plot_id
    try:
        db = get_supabase_client()
        if request.plot_id:
            result = db.table("land_plots").select("*").eq("id", request.plot_id).execute()
            if result.data:
                plot = result.data[0]
                logger.info(f"Found plot {request.plot_id} in database")
                # Update plot with location if not already set
                if not plot.get("region") or plot.get("region") == "Nyeri":
                    db.table("land_plots").update({"region": location}).eq("id", request.plot_id).execute()
                    logger.info(f"Updated plot {request.plot_id} with location: {location}")
        
        # If no plot_id provided, create a new plot
        if not plot_id:
            # Calculate area from geometry (rough estimate)
            coords = get_centroid_from_geometry(request.geometry)
            area_hectares = 10.0  # Default, can be calculated from geometry bounds
            
            new_plot = {
                "id": str(uuid.uuid4()),
                "owner_id": owner_id,
                "name": f"Plot at {location}",
                "geometry": request.geometry,
                "area_hectares": area_hectares,
                "region": location,
                "land_use": "forest"
            }
            result = db.table("land_plots").insert(new_plot).execute()
            plot = result.data[0]
            plot_id = plot["id"]
            logger.info(f"Created new plot {plot_id} at {location}")
            
    except Exception as e:
        # Database not configured, use defaults
        logger.warning(f"Database not available: {e}")

    land_use = plot["land_use"] if plot else "forest"
    region = location  # Use extracted location
    area = plot["area_hectares"] if plot else 10.0
    
    # Extract real Sentinel-2 features from Google Earth Engine
    if not request.geometry:
        raise HTTPException(status_code=400, detail="Geometry is required for scan")
    
    logger.info(f"Extracting Sentinel-2 features for geometry type: {request.geometry['type']}")
    features = extract_sentinel_features(
        geometry=request.geometry,
        start_date="2023-01-01",
        end_date="2024-12-31"
    )
    
    if features is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to extract satellite features. Check geometry and try again."
        )
    
    # Predict biomass using trained multi-sensor model (with uncertainty)
    biomass_result = predict_biomass_from_features(features)
    biomass = biomass_result["biomass_mean"]
    biomass_lower = biomass_result["biomass_lower_90"]
    biomass_upper = biomass_result["biomass_upper_90"]
    uncertainty_pct = biomass_result["uncertainty_pct"]
    logger.info(
        f"Biomass: {biomass} t/ha  "
        f"[90% PI: {biomass_lower}–{biomass_upper}]  "
        f"model={biomass_result['model_type']}  R²={biomass_result['model_r2']}"
    )

    
    # Calculate tCO2e
    tco2e = biomass_to_tco2e(biomass, area)
    carbon_density = round(tco2e / area, 2) if area > 0 else 0

    # Risk assessment
    weather = get_weather_data(region)
    risk = calculate_risk_score(weather, land_use)

    # Integrity score
    ndvi = features['ndvi']
    evi = features['evi']
    integrity = calculate_integrity_score(
        ndvi_mean=ndvi,
        ndvi_std=random.uniform(0.02, 0.15),
        temporal_ndvi_change=random.uniform(-0.05, 0.1),
        cloud_cover_pct=random.uniform(5, 30),
        scan_resolution_m=10.0,
        biomass_model_r2=biomass_result.get("model_r2") or 0.53,
        drought_risk=risk["drought_risk"],
        wildfire_risk=risk["wildfire_risk"],
        deforestation_proximity_km=random.uniform(5, 40),
        years_under_conservation=random.uniform(0, 15),
        land_use=land_use,
        additionality_score=random.uniform(0.4, 0.9),
    )

    # Price
    price = calculate_credit_price(integrity, risk["composite_risk"])

    # Save scan result to DB
    scan_id = str(uuid.uuid4())
    
    # Build raw bands dict from features
    raw_bands = {
        'B2': features['blue'],
        'B3': features['green'],
        'B4': features['red'],
        'B8': features['nir'],
        'B11': features['swir1'],
        'B12': features['swir2'],
        'NDVI': features['ndvi'],
        'EVI': features['evi'],
        'elevation': features['elevation'],
        'slope': features['slope'],
        'n_images': features['n_images']
    }
    
    scan_record = {
        "id": scan_id,
        "plot_id": plot_id,
        "mean_ndvi": ndvi,
        "mean_evi": evi,
        "estimated_biomass": biomass,
        "biomass_lower_90": biomass_lower,
        "biomass_upper_90": biomass_upper,
        "biomass_uncertainty_pct": uncertainty_pct,
        "estimated_tco2e": tco2e,
        "carbon_density": carbon_density,
        "integrity_score": integrity,
        "model_version": "biomass_model_v1",
        "model_type": biomass_result.get("model_type"),
        "model_r2": biomass_result.get("model_r2"),
        "sensors_used": {
            "sentinel2": True,
            "sentinel1_sar": "vv" in features,
            "gedi_lidar": "rh98" in features,
        },
        "raw_bands": raw_bands,
    }
    try:
        db = get_supabase_client()
        db.table("scan_results").insert(scan_record).execute()
        logger.info(f"Saved scan result {scan_id} to database")
        
        # Automatically create carbon credit from scan result with 'pending_approval' status
        credit_id = str(uuid.uuid4())
        credit_record = {
            "id": credit_id,
            "scan_id": scan_id,
            "plot_id": plot_id,
            "owner_id": owner_id,  # Use converted UUID
            "vintage_year": datetime.now().year,
            "quantity_tco2e": tco2e,
            "price_per_tonne": price,
            "status": "pending_approval",  # Wait for landowner approval before listing
            "integrity_score": integrity,
            "risk_score": risk["composite_risk"],  # Keep as 0-1 decimal, not percentage
        }
        db.table("carbon_credits").insert(credit_record).execute()
        logger.info(f"Created carbon credit {credit_id} with pending_approval status")
        
        # Audit trail — required for dMRV transparency (proposal Section 3.3)
        try:
            audit_entry = {
                "action": "scan_completed",
                "entity_type": "scan_result",
                "entity_id": scan_id,
                "performed_by": owner_id,
                "details": {
                    "plot_id": plot_id,
                    "credit_id": credit_id,
                    "biomass_mean_t_ha": biomass,
                    "biomass_lower_90": biomass_lower,
                    "biomass_upper_90": biomass_upper,
                    "uncertainty_pct": uncertainty_pct,
                    "tco2e": tco2e,
                    "integrity_score": integrity,
                    "model_type": biomass_result.get("model_type"),
                    "model_r2": biomass_result.get("model_r2"),
                    "sensors_used": scan_record["sensors_used"],
                },
            }
            db.table("audit_log").insert(audit_entry).execute()
            logger.info(f"Audit trail entry written for scan {scan_id}")
        except Exception as audit_err:
            logger.warning(f"Audit log write failed (non-fatal): {audit_err}")

        # Create notification for landowner
        notification_data = {
            "user_id": owner_id,
            "type": "scan_complete",
            "title": "Land Scan Complete - Review Results",
            "message": f"Your land scan has been completed. Review the findings: {tco2e:.2f} tCO2e valued at ${price:.2f}/tonne (Total: ${tco2e * price:.2f}). Please review and approve to list on marketplace.",
            "data": {
                "scan_id": scan_id,
                "credit_id": credit_id,
                "plot_id": plot_id,
                "tco2e": tco2e,
                "price_per_tonne": price,
                "total_value": tco2e * price,
                "integrity_score": integrity,
                "risk_score": risk["composite_risk"] * 100,  # Display as percentage
                "biomass": biomass,
                "ndvi": ndvi,
                "evi": evi,
            }
        }
        # Use admin client to bypass RLS for notification creation
        admin_db = get_admin_client()
        admin_db.table("notifications").insert(notification_data).execute()
        logger.info(f"Created notification for landowner {owner_id}")
        
    except Exception as e:
        logger.warning(f"Failed to save scan to DB: {e}")

    return ScanResponse(
        scan_id=scan_id,
        plot_id=plot_id,
        mean_ndvi=ndvi,
        mean_evi=evi,
        estimated_biomass=biomass,
        biomass_lower_90=biomass_lower,
        biomass_upper_90=biomass_upper,
        biomass_uncertainty_pct=uncertainty_pct,
        estimated_tco2e=tco2e,
        carbon_density=carbon_density,
        integrity_score=integrity,
        buy_price_per_tonne=price,
        risk_adjustment=risk["composite_risk"],
        raw_bands=raw_bands,
        sensors_used=scan_record["sensors_used"],
    )


@router.get("/{scan_id}")
async def get_scan(scan_id: str):
    db = get_supabase_client()
    result = db.table("scan_results").select("*").eq("id", scan_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")
    return result.data[0]
