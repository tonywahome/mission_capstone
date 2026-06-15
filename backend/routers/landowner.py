from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from database import get_supabase_client, get_admin_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/landowner", tags=["landowner"])


class PendingScanResponse(BaseModel):
    credit_id: str
    scan_id: str
    plot_id: str
    plot_name: str
    scan_date: str
    quantity_tco2e: float
    price_per_tonne: float
    total_value: float
    integrity_score: float
    risk_score: float
    biomass: float
    ndvi: float
    evi: float
    carbon_density: float
    status: str


class ApprovalRequest(BaseModel):
    credit_id: str
    approved: bool
    rejection_reason: Optional[str] = None


@router.get("/pending-scans")
async def get_pending_scans(user_id: str, plot_id: Optional[str] = None):
    """
    Get scan results for a landowner.
    - Without plot_id: returns only pending_approval credits (dashboard mode).
    - With plot_id: returns all credits for that specific plot (all statuses).
    """
    try:
        db = get_admin_client()

        query = db.table("carbon_credits")\
            .select("*, scan_results(*), land_plots(name)")\
            .eq("owner_id", user_id)

        if plot_id:
            query = query.eq("plot_id", plot_id)
        else:
            query = query.eq("status", "pending_approval")

        credits_result = query.order("created_at", desc=True).execute()

        if not credits_result.data:
            return {"pending_scans": []}
        
        # Format response
        pending_scans = []
        for credit in credits_result.data:
            scan = credit.get("scan_results", {})
            plot = credit.get("land_plots", {})
            
            pending_scans.append({
                "credit_id": credit["id"],
                "scan_id": credit["scan_id"],
                "plot_id": credit["plot_id"],
                "plot_name": plot.get("name", "Unknown Plot") if plot else "Unknown Plot",
                "scan_date": scan.get("scan_date", credit["created_at"]) if scan else credit["created_at"],
                "quantity_tco2e": credit["quantity_tco2e"],
                "price_per_tonne": credit["price_per_tonne"],
                "total_value": credit["quantity_tco2e"] * credit["price_per_tonne"],
                "integrity_score": credit["integrity_score"],
                "risk_score": credit["risk_score"] * 100,  # Display as percentage
                "biomass": scan.get("estimated_biomass", 0) if scan else 0,
                "ndvi": scan.get("mean_ndvi", 0) if scan else 0,
                "evi": scan.get("mean_evi", 0) if scan else 0,
                "carbon_density": scan.get("carbon_density", 0) if scan else 0,
                "status": credit["status"],
            })
        
        return {"pending_scans": pending_scans}
    
    except Exception as e:
        logger.error(f"Error fetching pending scans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch pending scans")


@router.post("/approve-listing")
async def approve_or_reject_listing(data: ApprovalRequest, background_tasks: BackgroundTasks):
    """
    Approve or reject a carbon credit listing.
    
    - If approved: Credit status changes to 'listed' and appears on marketplace
    - If rejected: Credit status changes to 'rejected' and is hidden
    """
    try:
        db = get_supabase_client()
        
        # Verify credit exists and is pending
        credit_result = db.table("carbon_credits")\
            .select("*, land_plots(owner_id, name)")\
            .eq("id", data.credit_id)\
            .execute()
        
        if not credit_result.data:
            raise HTTPException(status_code=404, detail="Carbon credit not found")
        
        credit = credit_result.data[0]
        
        if credit["status"] != "pending_approval":
            raise HTTPException(
                status_code=400, 
                detail=f"Credit is not pending approval (current status: {credit['status']})"
            )
        
        # Update credit status
        new_status = "listed" if data.approved else "rejected"
        update_data = {
            "status": new_status,
            "updated_at": datetime.now().isoformat()
        }
        
        if new_status == "listed":
            update_data["listed_at"] = datetime.now().isoformat()
        
        db.table("carbon_credits")\
            .update(update_data)\
            .eq("id", data.credit_id)\
            .execute()

        logger.info(f"Credit {data.credit_id} {new_status} by landowner")

        # Mark the originating scan_complete notification as read so the
        # dashboard pending-review counter clears immediately.
        try:
            admin_db = get_admin_client()
            admin_db.table("notifications")\
                .update({"read": True})\
                .eq("user_id", credit.get("owner_id"))\
                .eq("type", "scan_complete")\
                .filter("data->>credit_id", "eq", data.credit_id)\
                .execute()
        except Exception as mark_err:
            logger.warning(f"Could not mark scan_complete notification read: {mark_err}")

        # Create confirmation notification
        # Use the owner_id directly from the credit, not from land_plots
        owner_id = credit.get("owner_id")
        
        if owner_id:
            notification_data = {
                "user_id": owner_id,
                "type": "credit_approved" if data.approved else "system",
                "title": "Listing Approved" if data.approved else "Listing Rejected",
                "message": (
                    f"Your carbon credit listing for {credit['quantity_tco2e']:.2f} tCO2e has been {'approved and listed on the marketplace' if data.approved else 'rejected'}."
                    if data.approved
                    else f"You rejected the carbon credit listing. Reason: {data.rejection_reason or 'Not specified'}"
                ),
                "data": {
                    "credit_id": data.credit_id,
                    "status": new_status,
                    "tco2e": credit["quantity_tco2e"],
                    "rejection_reason": data.rejection_reason,
                }
            }
            # Use admin client to bypass RLS for notification creation
            admin_db = get_admin_client()
            admin_db.table("notifications").insert(notification_data).execute()
        
        action_text = "approved and listed on marketplace" if data.approved else "rejected"
        
        return {
            "message": f"Carbon credit {action_text} successfully",
            "credit_id": data.credit_id,
            "new_status": new_status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process approval")


@router.get("/my-credits")
async def get_my_credits(user_id: str):
    """Get all carbon credits owned by the landowner (all statuses)."""
    try:
        db = get_supabase_client()
        
        result = db.table("carbon_credits")\
            .select("*, land_plots(name, area_hectares), scan_results(mean_ndvi, mean_evi)")\
            .eq("owner_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {"credits": result.data or []}
    
    except Exception as e:
        logger.error(f"Error fetching credits: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credits")
