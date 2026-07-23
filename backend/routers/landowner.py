from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from database import get_admin_client
from services.auth_deps import get_current_user, require_role, AuthedUser

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


class UnsubmitRequest(BaseModel):
    credit_id: str


@router.get("/pending-scans")
async def get_pending_scans(
    plot_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    caller: AuthedUser = Depends(get_current_user),
):
    """
    Get scan results for the authenticated steward.
    - Without plot_id: returns only pending_approval credits (dashboard mode).
    - With plot_id: returns all credits for that specific plot (all statuses).
    """
    if caller.role not in ("steward", "research_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        db = get_admin_client()

        query = db.table("carbon_credits")\
            .select("*, scan_results(*), land_plots(name)")\
            .eq("owner_id", caller.id)

        if plot_id:
            query = query.eq("plot_id", plot_id)
        else:
            query = query.eq("status", "pending_approval")

        credits_result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

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


@router.get("/verification-queue")
async def get_verification_queue(
    limit: int = 50,
    offset: int = 0,
    caller: AuthedUser = Depends(require_role("analyst", "research_admin")),
):
    """
    District-scoped audit queue for an analyst (Section 3.4/3.6).

    Unlike /pending-scans above (which is owner_id-scoped — i.e. it only
    ever returns records a STEWARD owns), this endpoint returns pending
    records across ALL stewards, narrowed to the caller's
    `assigned_district` (read from their verified JWT app_metadata — see
    backend/services/auth_deps.py) when one is set.

    Falls back to an unscoped queue (all districts) when:
      - the caller has no `assigned_district` set, or
      - the `land_plots.district` column doesn't exist yet (pre-migration) —
        see backend/data/migration_capstone_rescope.sql.

    This fallback is intentionally permissive (shows MORE records, not
    fewer) — under-scoping an audit queue is a workflow/usability gap, not
    a privacy leak. This is the opposite fallback direction from
    services/privacy.py's coordinate rounding, which fails closed toward
    LESS data because it protects identifying location information; there
    is no equivalent confidentiality risk in which districts' pending
    records a verifier can see.
    """
    try:
        db = get_admin_client()
        assigned_district = caller.assigned_district

        credits_result = None
        if assigned_district:
            try:
                credits_result = (
                    db.table("carbon_credits")
                    .select("*, scan_results(*), land_plots(name, district, owner_id)")
                    .in_("status", ["pending_approval", "pending_review"])
                    .eq("land_plots.district", assigned_district)
                    .order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )
            except Exception as filter_err:
                logger.warning(
                    f"verification-queue: district filter failed ({filter_err}); "
                    "falling back to unscoped queue. Apply "
                    "backend/data/migration_capstone_rescope.sql to add "
                    "land_plots.district."
                )
                credits_result = None

        if credits_result is None:
            credits_result = (
                db.table("carbon_credits")
                .select("*, scan_results(*), land_plots(name, district, owner_id)")
                .in_("status", ["pending_approval", "pending_review"])
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

        if not credits_result.data:
            return {"pending_scans": [], "scoped_to_district": assigned_district}

        pending_scans = []
        for credit in credits_result.data:
            scan = credit.get("scan_results", {})
            plot = credit.get("land_plots", {})

            pending_scans.append({
                "credit_id": credit["id"],
                "scan_id": credit["scan_id"],
                "plot_id": credit["plot_id"],
                "plot_name": plot.get("name", "Unknown Plot") if plot else "Unknown Plot",
                "district": plot.get("district") if plot else None,
                "owner_id": plot.get("owner_id") if plot else credit.get("owner_id"),
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

        return {"pending_scans": pending_scans, "scoped_to_district": assigned_district}

    except Exception as e:
        logger.error(f"Error fetching verification queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch verification queue")


@router.post("/approve-listing")
async def verify_scan_record(
    data: ApprovalRequest,
    background_tasks: BackgroundTasks,
    caller: AuthedUser = Depends(require_role("analyst", "research_admin")),
):
    """
    Analyst review of a submitted scan/field-data record.

    Repurposed from the original marketplace "list for sale" approval flow:
    this capstone has no secondary market, so the same underlying record
    (still persisted in `carbon_credits` pending the formal `Verification`
    entity/table — see backend/data/migration_capstone_rescope.sql) now
    represents an audit-trail verification outcome rather than a listing.

    - If approved: status -> 'verified' (confirmed, appears in audit trail)
    - If rejected:  status -> 'flagged' (queried/excluded from audit trail)

    Route path kept as `/approve-listing` for backward compatibility with
    existing frontend calls; only the semantics and stored status values
    changed.
    """
    try:
        db = get_admin_client()

        # Verify record exists and is pending review
        credit_result = db.table("carbon_credits")\
            .select("*, land_plots(owner_id, name)")\
            .eq("id", data.credit_id)\
            .execute()

        if not credit_result.data:
            raise HTTPException(status_code=404, detail="Verification record not found")

        credit = credit_result.data[0]

        if credit["status"] not in ("pending_approval", "pending_review"):
            raise HTTPException(
                status_code=400,
                detail=f"Record is not pending review (current status: {credit['status']})"
            )

        # Update verification status
        new_status = "verified" if data.approved else "flagged"
        update_data = {
            "status": new_status,
            "updated_at": datetime.now().isoformat()
        }

        if new_status == "verified":
            update_data["listed_at"] = datetime.now().isoformat()  # reused as "verified_at" timestamp

        db.table("carbon_credits")\
            .update(update_data)\
            .eq("id", data.credit_id)\
            .execute()

        logger.info(f"Verification record {data.credit_id} marked '{new_status}' by verifier-analyst")

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
                "title": "Verification Complete" if data.approved else "Record Flagged",
                "message": (
                    f"Your submission of {credit['quantity_tco2e']:.2f} tCO2e (biomass-derived estimate) has been {'verified and added to the audit trail' if data.approved else 'flagged'}."
                    if data.approved
                    else f"Your submission was flagged during verification. Reason: {data.rejection_reason or 'Not specified'}"
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

        action_text = "verified" if data.approved else "flagged"

        return {
            "message": f"Scan record {action_text} successfully",
            "credit_id": data.credit_id,
            "new_status": new_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process verification")


@router.post("/unsubmit")
async def unsubmit_scan_record(
    data: UnsubmitRequest,
    caller: AuthedUser = Depends(get_current_user),
):
    """
    Steward-side counterpart to verify_scan_record above: verifying/flagging
    a record is an analyst / research_admin action only, so a
    steward who wants to pull back their own not-yet-reviewed submission
    (e.g. to correct a mistake) needs a different action — withdraw it from
    the queue rather than "approve" or "flag" their own work.
    """
    if caller.role not in ("steward", "research_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        db = get_admin_client()

        credit_result = db.table("carbon_credits")\
            .select("*, land_plots(owner_id)")\
            .eq("id", data.credit_id)\
            .execute()

        if not credit_result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        credit = credit_result.data[0]
        plot = credit.get("land_plots") or {}
        owner_id = credit.get("owner_id") or plot.get("owner_id")

        if caller.role != "research_admin" and owner_id != caller.id:
            raise HTTPException(status_code=403, detail="Not authorized to unsubmit this record")

        if credit["status"] not in ("pending_approval", "pending_review"):
            raise HTTPException(
                status_code=400,
                detail=f"Only pending submissions can be unsubmitted (current status: {credit['status']})"
            )

        db.table("carbon_credits")\
            .update({"status": "withdrawn", "updated_at": datetime.now().isoformat()})\
            .eq("id", data.credit_id)\
            .execute()

        logger.info(f"Submission {data.credit_id} withdrawn by {caller.role} {caller.id}")

        return {
            "message": "Submission withdrawn",
            "credit_id": data.credit_id,
            "new_status": "withdrawn",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubmitting record: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to unsubmit record")


@router.get("/my-credits")
async def get_my_submissions(
    limit: int = 50,
    offset: int = 0,
    caller: AuthedUser = Depends(get_current_user),
):
    """Get all scan/verification records for the authenticated steward's projects (all statuses)."""
    if caller.role not in ("steward", "research_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        db = get_admin_client()

        result = db.table("carbon_credits")\
            .select("*, land_plots(name, area_hectares), scan_results(mean_ndvi, mean_evi)")\
            .eq("owner_id", caller.id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        return {"credits": result.data or []}

    except Exception as e:
        logger.error(f"Error fetching submissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch submissions")
