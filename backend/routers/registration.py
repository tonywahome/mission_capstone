from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
from database import get_admin_client

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
async def submit_registration_request(data: RegistrationRequest, background_tasks: BackgroundTasks):
    """Submit a land registration request. Admin will be notified via email."""
    try:
        db = get_admin_client()
        
        # Prepare coordinates and boundaries for storage
        coords_json = None
        if data.coordinates:
            coords_json = {"lat": data.coordinates.lat, "lon": data.coordinates.lon}
        
        boundaries_json = None
        if data.boundaries:
            boundaries_json = data.boundaries
        
        geometry_json = None
        if data.geometry:
            geometry_json = data.geometry
        
        # Store request in database
        request_data = {
            "owner_name": data.owner_name,
            "owner_email": data.owner_email,
            "land_location": data.land_location,
            "land_size": data.land_size,
            "land_type": data.land_type,
            "coordinates": coords_json,
            "boundaries": boundaries_json,
            "geometry": geometry_json,
            "additional_info": data.additional_info,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        
        result = db.table("registration_requests").insert(request_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to submit registration request"
            )
        
        # Send email notification to admin (in background)
        background_tasks.add_task(
            send_admin_notification,
            data.owner_name,
            data.owner_email,
            data.land_location,
            data.land_size,
            data.land_type,
            data.additional_info
        )
        
        logger.info(f"Registration request submitted by {data.owner_name} ({data.owner_email}) with coordinates")
        
        return {
            "message": "Registration request submitted successfully",
            "request_id": result.data[0]["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration request error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit registration request"
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
        
        admin_email = "mangamhizha@gmail.com"
        
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
async def get_registration_requests(status: Optional[str] = None):
    """Get all registration requests (admin only)."""
    try:
        db = get_admin_client()
        
        query = db.table("registration_requests").select("*")
        
        if status:
            query = query.eq("status", status)
        
        result = query.order("created_at", desc=True).execute()
        
        return result.data
        
    except Exception as e:
        logger.error(f"Failed to fetch registration requests: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch registration requests"
        )
