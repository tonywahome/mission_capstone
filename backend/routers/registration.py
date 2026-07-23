from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import logging
import json
import uuid
from datetime import datetime
from database import get_admin_client
from services.auth_deps import get_current_user, require_role, AuthedUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/registration", tags=["registration"])

class Coordinates(BaseModel):
    lat: float
    lon: float

class RegistrationRequest(BaseModel):
    owner_name: str
    owner_email: EmailStr
    land_location: str
    land_size: str
    land_type: str
    coordinates: Optional[Coordinates] = None  # Center point of land
    boundaries: Optional[List[List[float]]] = None  # Array of [lat, lon] points forming polygon
    geometry: Optional[Dict[str, Any]] = None  # GeoJSON geometry from Mapbox
    additional_info: Optional[str] = None

@router.post("/request")
async def submit_registration_request(
    data: RegistrationRequest,
    background_tasks: BackgroundTasks,
    caller: AuthedUser = Depends(get_current_user),
):
    """Submit a land registration request. Admin will be notified via email."""
    if caller.role != "steward":
        raise HTTPException(status_code=403, detail="Only stewards can submit registration requests")

    try:
        # Extract fields from request
        owner_id = caller.id  # server-derived, never trust a client-sent value
        owner_name = data.owner_name
        owner_email = data.owner_email
        land_location = data.land_location
        land_size = data.land_size
        land_type = data.land_type
        additional_info = data.additional_info
        geometry = data.geometry

        db = get_admin_client()
        
        # Store request in database
        request_data = {
            "owner_name": owner_name,
            "owner_email": owner_email,
            "land_location": land_location,
            "land_size": land_size,
            "land_type": land_type,
            "geometry": geometry,
            "additional_info": additional_info,
            "status": "pending",
        }
        
        logger.info(f"Inserting registration request: {request_data}")
        result = db.table("registration_requests").insert(request_data).execute()
        logger.info(f"Insert result: {result}")

        if not result.data:
            logger.error(f"No data returned from insert: {result}")
            raise HTTPException(
                status_code=500,
                detail="Failed to submit registration request"
            )

        request_id = result.data[0]["id"]

        # Immediately create a plot so it shows up on the steward's dashboard
        # ("Registered plots" tally reads land_plots, not registration_requests
        # — see frontend/src/app/landowner/page.tsx). The admin scan flow
        # (backend/routers/scan.py) later enriches this same row with the
        # real area/land_use derived from satellite imagery rather than
        # creating a second plot; it looks the row up by registration_request_id.
        if owner_id:
            try:
                parsed_size = float(land_size)
            except (TypeError, ValueError):
                parsed_size = 0.0

            # land_plots.land_use has a narrower CHECK constraint than
            # registration_requests.land_type (schema.sql omits 'bareland',
            # which migration_add_admin.sql allows on the request form) —
            # fall back to 'grassland' rather than violate the constraint.
            plot_land_use = land_type if land_type in (
                "forest", "grassland", "cropland", "wetland", "agroforestry"
            ) else "grassland"

            plot_data = {
                "id": str(uuid.uuid4()),
                "owner_id": owner_id,
                "name": f"Plot at {land_location}",
                "geometry": geometry or {},
                "area_hectares": parsed_size,
                "region": land_location,
                "land_use": plot_land_use,
                "registration_request_id": request_id,
                "status": "pending_scan",
            }
            try:
                plot_result = db.table("land_plots").insert(plot_data).execute()
                logger.info(f"Created plot for registration request {request_id}: {plot_result.data}")
            except Exception as plot_err:
                # Older schemas may not have registration_request_id/status yet
                # (see backend/data/migration_plot_registration_link.sql) —
                # retry without those columns so the plot still appears on the
                # dashboard even if that migration hasn't been applied.
                logger.warning(f"Plot insert failed with full schema, retrying without new columns: {plot_err}")
                try:
                    fallback_plot = {k: v for k, v in plot_data.items() if k not in ("registration_request_id", "status")}
                    db.table("land_plots").insert(fallback_plot).execute()
                    logger.info(f"Created plot for registration request {request_id} using fallback schema")
                except Exception as fallback_err:
                    logger.error(f"Failed to create plot for registration request {request_id}: {fallback_err}")
                    raise HTTPException(status_code=500, detail="Failed to create land plot for this registration request")
        else:
            logger.warning(f"No owner_id provided with registration request {request_id}; skipping plot creation")

        # Send email notification to admin (in background)
        background_tasks.add_task(
            send_admin_notification,
            owner_name,
            owner_email,
            land_location,
            land_size,
            land_type,
            additional_info
        )
        
        logger.info(f"Registration request submitted by {owner_name} ({owner_email})")
        
        return {
            "message": "Registration request submitted successfully",
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration request error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit registration request: {str(e)}"
        )

def send_admin_notification(
    owner_name: str,
    owner_email: str,
    land_location: str,
    land_size: str,
    land_type: str,
    additional_info: Optional[str]
):
    """Send email notification to admin about new registration request."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        admin_email = "antonomics101@gmail.com"
        
        # Create email message
        subject = f"New Land Registration Request from {owner_name}"
        
        body = f"""
New Land Registration Request Received

Owner Details:
- Name: {owner_name}
- Email: {owner_email}

Land Details:
- Location: {land_location}
- Size: {land_size} hectares
- Type: {land_type}

Additional Information:
{additional_info or "None provided"}

Please log in to the admin portal to scan this land and issue a certificate.

---
TerraFoma Carbon Credit Platform
        """
        
        # For now, just log the email (you can configure SMTP later)
        logger.info(f"EMAIL TO ADMIN: {admin_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body}")
        
        # TODO: Configure SMTP to actually send emails
        # For production, configure with Gmail SMTP or SendGrid
        
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
        # Don't raise exception - notification failure shouldn't block request

@router.get("/requests")
async def get_registration_requests(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    caller: AuthedUser = Depends(require_role("analyst", "research_admin")),
):
    """Get registration requests (analyst/research_admin only), paginated."""
    try:
        db = get_admin_client()

        query = db.table("registration_requests").select("*")

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        return result.data

    except Exception as e:
        logger.error(f"Failed to fetch registration requests: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch registration requests"
        )


@router.get("/requests/{request_id}/plot")
async def get_plot_for_registration_request(
    request_id: str,
    caller: AuthedUser = Depends(require_role("research_admin")),
):
    """Return the land_plots row created for this registration request, so
    the admin 'Auto Scan on behalf of a steward' flow can obtain the real
    owner_id without needing an unauthenticated email-resolution lookup."""
    db = get_admin_client()
    try:
        result = (
            db.table("land_plots")
            .select("*")
            .eq("registration_request_id", request_id)
            .execute()
        )
    except Exception as e:
        logger.error(f"Failed to fetch plot for registration request {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch plot for this registration request")
    if not result.data:
        raise HTTPException(status_code=404, detail="No plot found for this registration request")
    return result.data[0]


class ReviewRequest(BaseModel):
    rejection_reason: Optional[str] = None


@router.post("/requests/{request_id}/approve")
async def approve_registration_request(
    request_id: str,
    body: ReviewRequest,
    caller: AuthedUser = Depends(require_role("research_admin")),
):
    """
    Admin greenlights a pending registration request for scanning.

    This does NOT run the satellite scan itself — the plot created at
    submission time (see submit_registration_request above) already exists
    on the steward's dashboard with status 'pending_scan'. Approving here
    just marks the request reviewed/accepted so it moves out of the
    "pending" filter; a research_admin still runs "Auto Scan" afterward to
    populate real biomass/NDVI data (backend/routers/scan.py sets the plot
    to 'scanned' and the request to 'approved' again at that point — both
    writes are idempotent, so doing it here first is safe).
    """
    db = get_admin_client()

    existing = db.table("registration_requests").select("*").eq("id", request_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Registration request not found")

    current = existing.data[0]
    if current["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending (current status: {current['status']})"
        )

    update_data = {
        "status": "approved",
        "processed_at": datetime.now().isoformat(),
        "processed_by": caller.id,
    }

    try:
        db.table("registration_requests").update(update_data).eq("id", request_id).execute()
    except Exception as e:
        logger.error(f"Failed to approve registration request {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve registration request")

    _notify_steward_of_review(db, current, approved=True)

    logger.info(f"Registration request {request_id} approved")
    return {"message": "Registration request approved", "request_id": request_id, "status": "approved"}


@router.post("/requests/{request_id}/reject")
async def reject_registration_request(
    request_id: str,
    body: ReviewRequest,
    caller: AuthedUser = Depends(require_role("research_admin")),
):
    """Admin declines a pending registration request. The plot created at
    submission time is removed so it no longer shows on the steward's
    dashboard (it never had a real scan/credit attached, since only pending
    requests can be rejected — see the status check below)."""
    db = get_admin_client()

    existing = db.table("registration_requests").select("*").eq("id", request_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Registration request not found")

    current = existing.data[0]
    if current["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Request is not pending (current status: {current['status']})"
        )

    update_data = {
        "status": "rejected",
        "processed_at": datetime.now().isoformat(),
        "rejection_reason": body.rejection_reason,
        "processed_by": caller.id,
    }

    try:
        db.table("registration_requests").update(update_data).eq("id", request_id).execute()
    except Exception as e:
        logger.error(f"Failed to reject registration request {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject registration request")

    # Remove the plot created at submission time — it was never scanned
    # (status is still 'pending' at this point, guaranteed by the check
    # above), so nothing else references it yet.
    try:
        db.table("land_plots").delete().eq("registration_request_id", request_id).execute()
    except Exception as e:
        logger.warning(f"Failed to remove plot for rejected request {request_id} (non-fatal): {e}")

    _notify_steward_of_review(db, current, approved=False, rejection_reason=body.rejection_reason)

    logger.info(f"Registration request {request_id} rejected")
    return {"message": "Registration request rejected", "request_id": request_id, "status": "rejected"}


def _notify_steward_of_review(db, request_row: dict, approved: bool, rejection_reason: Optional[str] = None):
    """Best-effort notification to the steward who submitted the request.
    Looked up by owner_email since registration_requests doesn't store the
    steward's user id directly (see submit_registration_request docstring
    context — owner_id is only used for the land_plots row, not persisted
    on the request itself)."""
    try:
        owner_email = request_row.get("owner_email")
        if not owner_email:
            return
        user_res = db.table("profiles").select("id").eq("email", owner_email).execute()
        if not user_res.data:
            return
        user_id = user_res.data[0]["id"]

        notification_data = {
            "user_id": user_id,
            "type": "system",
            "title": "Registration Approved" if approved else "Registration Rejected",
            "message": (
                f"Your land registration request for {request_row.get('land_location')} was approved. "
                "It's now queued for satellite scanning."
                if approved
                else f"Your land registration request for {request_row.get('land_location')} was rejected."
                + (f" Reason: {rejection_reason}" if rejection_reason else "")
            ),
            "data": {"request_id": request_row.get("id")},
        }
        db.table("notifications").insert(notification_data).execute()
    except Exception as e:
        logger.warning(f"Failed to send review notification (non-fatal): {e}")
