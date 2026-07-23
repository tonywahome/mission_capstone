import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from models.risk import ScanRequest, ScanResponse
from services.biomass_estimator import predict_biomass_from_features, biomass_to_tco2e, calculate_integrity_score
from services.risk_scorer import calculate_risk_score, get_weather_data
from services.gee_feature_extractor import extract_sentinel_features
from services.carbon_calculator import calculate_credit_price
from services.location_service import get_location_from_geometry, get_centroid_from_geometry
from services.auth_deps import get_current_user, AuthedUser
from database import get_admin_client
import random

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scan", tags=["scan"])


def estimate_vegetation_cover_pct(ndvi: float, evi: float) -> float:
    vegetation_signal = (ndvi * 0.65) + (evi * 0.35)
    cover_pct = ((vegetation_signal - 0.15) / 0.7) * 100
    return round(max(0.0, min(100.0, cover_pct)), 1)


@router.post("", response_model=ScanResponse)
async def run_scan(request: ScanRequest, caller: AuthedUser = Depends(get_current_user)):
    if caller.role not in ("steward", "research_admin"):
        raise HTTPException(status_code=403, detail="Only stewards can run a scan")

    # A research_admin may scan on behalf of a steward by passing an
    # explicit owner_id; any other caller always scans as themselves,
    # regardless of what the request body says.
    owner_id = (
        request.owner_id
        if caller.role == "research_admin" and request.owner_id
        else caller.id
    )
    logger.info(f"Processing scan request for owner: {owner_id}")
    registration_request_id = request.registration_request_id

    # Extract location from geometry
    location = get_location_from_geometry(request.geometry)
    logger.info(f"Extracted location: {location}")
    
    # Try to get plot details from database if available, or create one
    plot = None
    plot_id = request.plot_id
    try:
        db = get_admin_client()
        if request.plot_id:
            result = db.table("land_plots").select("*").eq("id", request.plot_id).execute()
            if result.data:
                plot = result.data[0]
                logger.info(f"Found plot {request.plot_id} in database")
                # Update plot with location if not already set. The "Nyeri"
                # check this used to also match was a leftover default from
                # the pre-Rwanda-pivot codebase and no longer corresponds to
                # any default value this app actually writes — removed.
                if not plot.get("region"):
                    db.table("land_plots").update({"region": location}).eq("id", request.plot_id).execute()
                    logger.info(f"Updated plot {request.plot_id} with location: {location}")
        
        # No plot_id provided directly — if this scan originated from a
        # registration request, a plot was already created for it at
        # submission time (see backend/routers/registration.py) so the
        # steward's dashboard had something to show immediately. Find and
        # enrich that same row instead of inserting a duplicate plot.
        if not plot_id and registration_request_id:
            existing = (
                db.table("land_plots")
                .select("*")
                .eq("registration_request_id", registration_request_id)
                .execute()
            )
            if existing.data:
                plot = existing.data[0]
                plot_id = plot["id"]
                logger.info(f"Found pre-registered plot {plot_id} for registration request {registration_request_id}")

        # Default land_use to one of the proposal's two in-scope strata
        # (IN_SCOPE_LAND_USE in models/land_plot.py), not "forest" —
        # closed-canopy forest is explicitly out of scope for this
        # capstone (see README "Project Scope"). ScanRequest carries no
        # land_use field, so infer from the reverse-geocoded location
        # string when it names one of the two pilot districts; otherwise
        # fall back to "grassland" rather than an out-of-scope value.
        inferred_land_use = "grassland"
        if "rulindo" in location.lower():
            inferred_land_use = "agroforestry"
        elif "bugesera" in location.lower():
            inferred_land_use = "grassland"

        if plot_id and plot:
            # Enrich the pre-registered plot with the real geometry/location
            # derived from satellite imagery, and mark it scanned.
            update_fields = {
                "geometry": request.geometry,
                "region": location,
                "status": "scanned",
            }
            try:
                db.table("land_plots").update(update_fields).eq("id", plot_id).execute()
                plot = {**plot, **update_fields}
                logger.info(f"Updated pre-registered plot {plot_id} with scan geometry/location")
            except Exception as update_err:
                # 'status' column may not exist yet if
                # migration_plot_registration_link.sql hasn't been applied.
                logger.warning(f"Plot update failed with full schema, retrying without status: {update_err}")
                try:
                    db.table("land_plots").update({"geometry": request.geometry, "region": location}).eq("id", plot_id).execute()
                    plot = {**plot, "geometry": request.geometry, "region": location}
                except Exception as fallback_err:
                    logger.warning(f"Failed to update pre-registered plot {plot_id}: {fallback_err}")

        # Still no plot row (either no plot_id was ever supplied, or the
        # supplied plot_id/registration_request_id didn't match anything in
        # land_plots) — create one from scratch rather than silently
        # proceeding with a plot_id that has no backing row, which would
        # trip the scan_results/carbon_credits FK constraints downstream.
        if not plot:
            plot_id = None
            area_hectares = 10.0  # Default, can be calculated from geometry bounds

            new_plot_id = str(uuid.uuid4())
            new_plot = {
                "id": new_plot_id,
                "owner_id": owner_id,
                "name": f"Plot at {location}",
                "geometry": request.geometry,
                "area_hectares": area_hectares,
                "region": location,
                "land_use": inferred_land_use
            }
            try:
                result = db.table("land_plots").insert(new_plot).execute()
                if not result.data:
                    logger.error(f"land_plots insert for {new_plot_id} returned no data")
                    raise HTTPException(status_code=500, detail="Failed to create land plot record")
                plot = result.data[0]
                plot_id = plot["id"]
                logger.info(f"Created new plot {plot_id} at {location}")
            except HTTPException:
                raise
            except Exception as plot_insert_err:
                logger.error(f"Failed to insert plot to database: {plot_insert_err}")
                raise HTTPException(status_code=500, detail="Failed to create land plot record")

    except HTTPException:
        raise
    except Exception as e:
        # Database not configured, use defaults
        logger.warning(f"Database not available: {e}")

    # Same in-scope rationale as the new_plot default above.
    land_use = plot["land_use"] if plot else "grassland"
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
    vegetation_cover_pct = estimate_vegetation_cover_pct(ndvi, evi)
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
        db = get_admin_client()
        try:
            db.table("scan_results").insert(scan_record).execute()
            logger.info(f"Saved scan result {scan_id} to database")
        except Exception as insert_err:
            logger.warning(f"Failed to save scan to DB with all fields: {insert_err}")
            # Try fallback by removing fields not in the original schema
            fallback_record = {
                "id": scan_record["id"],
                "plot_id": scan_record["plot_id"],
                "mean_ndvi": scan_record["mean_ndvi"],
                "mean_evi": scan_record["mean_evi"],
                "estimated_biomass": scan_record["estimated_biomass"],
                "estimated_tco2e": scan_record["estimated_tco2e"],
                "carbon_density": scan_record["carbon_density"],
                "integrity_score": scan_record["integrity_score"],
                "model_version": scan_record["model_version"],
                "raw_bands": scan_record["raw_bands"],
            }
            try:
                db.table("scan_results").insert(fallback_record).execute()
                logger.info(f"Saved scan result {scan_id} using fallback schema")
            except Exception as fallback_insert_err:
                logger.error(f"Failed to save scan result {scan_id} even with fallback schema: {fallback_insert_err}")
                raise HTTPException(status_code=500, detail="Failed to save scan result")
        
        # Create an interim verification record from the scan result, status
        # 'pending_approval' (awaiting Verifier-Analyst review). This still
        # writes to the `carbon_credits` table for now — the proposal's
        # dedicated `Verification` entity (see
        # backend/data/migration_capstone_rescope.sql) supersedes this once
        # that additive migration is applied; no automated credit issuance
        # or marketplace listing happens here.
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
        try:
            db.table("carbon_credits").insert(credit_record).execute()
            logger.info(f"Created carbon credit {credit_id} with pending_approval status")
        except Exception as credit_err:
            logger.warning(f"Failed to create carbon credit with full schema, retrying with minimal fields: {credit_err}")
            # Retry with minimal fields, in case a newer column doesn't
            # exist yet on this project (e.g. migration not yet applied).
            try:
                fallback_credit = {
                    "id": credit_id,
                    "scan_id": scan_id,
                    "plot_id": plot_id,
                    "owner_id": owner_id,
                    "quantity_tco2e": tco2e,
                    "status": "pending_approval",
                }
                db.table("carbon_credits").insert(fallback_credit).execute()
                logger.info(f"Created fallback carbon credit {credit_id}")
            except Exception as fallback_err:
                logger.error(f"Failed to create fallback carbon credit {credit_id}: {fallback_err}")
                raise HTTPException(status_code=500, detail="Failed to create carbon credit record")
        
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

        # Create notification for the steward
        notification_data = {
            "user_id": owner_id,
            "type": "scan_complete",
            "title": "Scan Complete - Awaiting Verification",
            "message": f"Your scan has been completed: {tco2e:.2f} tCO2e estimated (90% PI uncertainty: {uncertainty_pct}%). It is now queued for Verifier-Analyst review.",
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
        try:
            admin_db.table("notifications").insert(notification_data).execute()
            logger.info(f"Created notification for landowner {owner_id}")
        except Exception as notif_err:
            logger.warning(f"Failed to create notification (non-fatal): {notif_err}")

        # Update registration request if provided
        if registration_request_id:
            try:
                admin_db.table("registration_requests").update({
                    "status": "approved",
                    "processed_at": datetime.now().isoformat(),
                }).eq("id", registration_request_id).execute()
                logger.info(f"Updated registration request {registration_request_id} to approved status")

                # Send email notification to admin about completed scan
                reg_request = admin_db.table("registration_requests").select("*").eq("id", registration_request_id).execute()
                if reg_request.data:
                    req_data = reg_request.data[0]
                    send_scan_completion_email(
                        owner_name=req_data.get("owner_name"),
                        owner_email=req_data.get("owner_email"),
                        land_location=req_data.get("land_location"),
                        land_size=req_data.get("land_size"),
                        biomass=biomass,
                        tco2e=tco2e,
                        integrity=integrity,
                        scan_id=scan_id
                    )
            except Exception as e:
                logger.warning(f"Failed to update registration request: {e}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to save scan to DB: {e}")

    return ScanResponse(
        scan_id=scan_id,
        plot_id=plot_id,
        mean_ndvi=ndvi,
        mean_evi=evi,
        vegetation_cover_pct=vegetation_cover_pct,
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


@router.post("/submit-review")
async def submit_scan_for_review(data: dict, caller: AuthedUser = Depends(get_current_user)):
    """Submit a completed scan for verifier review."""
    try:
        scan_id = data.get("scan_id")
        plot_id = data.get("plot_id")
        requested_owner_id = data.get("owner_id")
        owner_id = (
            requested_owner_id
            if caller.role == "research_admin" and requested_owner_id
            else caller.id
        )
        tco2e = data.get("tco2e")
        integrity_score = data.get("integrity_score")
        risk_score = data.get("risk_score")

        logger.info(f"submit-review received: scan_id={scan_id}, plot_id={plot_id}, owner_id={owner_id}")

        if not scan_id:
            logger.error("Missing scan_id in submit-review request")
            raise HTTPException(status_code=400, detail="scan_id required")

        if not plot_id:
            logger.warning(f"plot_id is None for scan {scan_id}, attempting to fetch from scan_results")
            db = get_admin_client()
            result = db.table("scan_results").select("plot_id").eq("id", scan_id).execute()
            if result.data:
                plot_id = result.data[0].get("plot_id")
                logger.info(f"Fetched plot_id from scan_results: {plot_id}")

            if not plot_id:
                plot_id = str(uuid.uuid4())
                logger.warning(f"Could not determine plot_id for scan {scan_id}, generating fallback ID: {plot_id}")

        admin_db = get_admin_client()

        logger.info(f"Scan {scan_id} submitted for review")

        # NOTE: the `verifications` table (migration_capstone_rescope.sql)
        # is a schema-only scaffold for the proposal's Section 3.4
        # Verification entity — its columns (credit_id, plot_id,
        # verifier_id, district, decision, notes, reviewed_at) don't match
        # what this endpoint would need to write at submit time (decision/
        # verifier_id aren't known yet; that only happens later at
        # approve-listing). The real verification-workflow status already
        # lives on carbon_credits.status (see routers/landowner.py's
        # approve-listing, and README's "Known Limitations"), so no insert
        # into `verifications` happens here — a generated id is returned
        # below purely for the response shape, not persisted anywhere.
        verification_id = str(uuid.uuid4())

        # NOTE: there is no real "notify all verifiers" fan-out mechanism in
        # this codebase — role lives in auth.users.app_metadata, which isn't
        # queryable from the `profiles` table alone, so there is no list of
        # analyst user ids to notify here. A prior version of this
        # code inserted a placeholder row with user_id="verifier-group" (not
        # a real UUID) and type="scan_pending_verification" (not in the
        # notifications.type CHECK constraint) — that insert could never
        # succeed and has been removed rather than patched, since there is no
        # correct target to notify yet. Verifiers currently discover pending
        # scans via the verification queue (GET /api/landowner/verification-queue).
        logger.info(f"Scan {scan_id} queued for verifier review (no per-verifier notification fan-out yet)")

        return {
            "message": "Scan submitted for review successfully",
            "scan_id": scan_id,
            "verification_id": verification_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit scan for review: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit scan for review: {str(e)}"
        )


def send_scan_completion_email(
    owner_name: str,
    owner_email: str,
    land_location: str,
    land_size: str,
    biomass: float,
    tco2e: float,
    integrity: float,
    scan_id: str
):
    """Send email notification to admin about completed scan."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        admin_email = "antonomics101@gmail.com"

        subject = f"Land Scan Complete: {owner_name}'s Property at {land_location}"

        body = f"""
Scan Completed Successfully

Landowner Details:
- Name: {owner_name}
- Email: {owner_email}

Land Details:
- Location: {land_location}
- Size: {land_size} hectares

Scan Results:
- Scan ID: {scan_id}
- Above-Ground Biomass: {biomass:.2f} t/ha
- Carbon Stock (tCO2e): {tco2e:.2f}
- Integrity Score: {integrity:.0f}/100

The scan results have been saved and are awaiting verifier review.

---
TerraFoma Carbon Credit Platform
        """

        logger.info(f"EMAIL TO ADMIN: {admin_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body}")

        # TODO: Configure SMTP to actually send emails
        # For production, configure with Gmail SMTP or SendGrid

    except Exception as e:
        logger.error(f"Failed to send scan completion email: {e}")


@router.get("/{scan_id}")
async def get_scan(scan_id: str, caller: AuthedUser = Depends(get_current_user)):
    db = get_admin_client()
    result = db.table("scan_results").select("*").eq("id", scan_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")
    scan = result.data[0]

    owner_id = None
    if scan.get("plot_id"):
        plot_res = db.table("land_plots").select("owner_id").eq("id", scan["plot_id"]).execute()
        if plot_res.data:
            owner_id = plot_res.data[0].get("owner_id")

    if caller.role not in ("analyst", "research_admin") and caller.id != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this scan")

    return scan
