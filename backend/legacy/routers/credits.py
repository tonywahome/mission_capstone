import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from models.credit import CreditCreate, CreditResponse, CreditStatusUpdate, CreditStats
from database import get_supabase_client

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("/stats", response_model=CreditStats)
async def get_credit_stats():
    db = get_supabase_client()
    result = db.table("carbon_credits").select("*").execute()
    credits = result.data

    if not credits:
        return CreditStats(
            total_credits=0, total_verified=0, total_pending_approval=0, total_listed=0,
            total_sold=0, total_retired=0, total_tco2e=0,
            avg_price=0, avg_integrity=0,
        )

    return CreditStats(
        total_credits=len(credits),
        total_verified=sum(1 for c in credits if c["status"] == "verified"),
        total_pending_approval=sum(1 for c in credits if c["status"] == "pending_approval"),
        total_listed=sum(1 for c in credits if c["status"] == "listed"),
        total_sold=sum(1 for c in credits if c["status"] == "sold"),
        total_retired=sum(1 for c in credits if c["status"] == "retired"),
        total_tco2e=round(sum(c["quantity_tco2e"] for c in credits), 2),
        avg_price=round(sum(c["price_per_tonne"] for c in credits) / len(credits), 2),
        avg_integrity=round(sum(c["integrity_score"] for c in credits) / len(credits), 1),
    )


@router.get("")
async def list_credits(status: str = None, min_integrity: float = None):
    db = get_supabase_client()
    # Get all credits first
    query = db.table("carbon_credits").select("*")
    if status:
        query = query.eq("status", status)
    if min_integrity:
        query = query.gte("integrity_score", min_integrity)
    result = query.order("created_at", desc=True).execute()
    
    # Now fetch plot info for each credit separately
    credits = []
    for credit in result.data:
        credit_data = {**credit}
        # Try to get plot info if plot_id exists
        if credit.get("plot_id"):
            try:
                plot_result = db.table("land_plots").select("region, name").eq("id", credit["plot_id"]).execute()
                if plot_result.data:
                    credit_data["region"] = plot_result.data[0].get("region")
                    credit_data["plot_name"] = plot_result.data[0].get("name")
            except Exception:
                pass  # Continue without plot info
        credits.append(credit_data)
    
    return credits


@router.get("/{credit_id}")
async def get_credit(credit_id: str):
    db = get_supabase_client()
    result = db.table("carbon_credits").select("*").eq("id", credit_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Credit not found")
    
    credit = result.data[0]
    credit_data = {**credit}
    
    # Try to get plot info if plot_id exists
    if credit.get("plot_id"):
        try:
            plot_result = db.table("land_plots").select("region, name").eq("id", credit["plot_id"]).execute()
            if plot_result.data:
                credit_data["region"] = plot_result.data[0].get("region")
                credit_data["plot_name"] = plot_result.data[0].get("name")
        except Exception:
            pass  # Continue without plot info
    
    return credit_data


@router.post("")
async def create_credit(credit: CreditCreate):
    db = get_supabase_client()
    credit_data = {
        "id": str(uuid.uuid4()),
        **credit.model_dump(),
        "status": "verified",
    }
    result = db.table("carbon_credits").insert(credit_data).execute()

    # Audit log
    try:
        db.table("audit_log").insert({
            "id": str(uuid.uuid4()),
            "entity_type": "credit",
            "entity_id": credit_data["id"],
            "action": "created",
            "new_value": {"status": "verified"},
        }).execute()
    except Exception:
        pass

    return result.data[0]


@router.patch("/{credit_id}/status")
async def update_credit_status(credit_id: str, update: CreditStatusUpdate):
    db = get_supabase_client()

    # Get current credit
    current = db.table("carbon_credits").select("*").eq("id", credit_id).execute()
    if not current.data:
        raise HTTPException(status_code=404, detail="Credit not found")

    old_status = current.data[0]["status"]
    update_data = {"status": update.status}

    # Set timestamps based on status
    now = datetime.utcnow().isoformat()
    if update.status == "listed":
        update_data["listed_at"] = now
    elif update.status == "sold":
        update_data["sold_at"] = now
    elif update.status == "retired":
        update_data["retired_at"] = now

    result = (
        db.table("carbon_credits").update(update_data).eq("id", credit_id).execute()
    )

    # Audit log
    try:
        db.table("audit_log").insert({
            "id": str(uuid.uuid4()),
            "entity_type": "credit",
            "entity_id": credit_id,
            "action": "status_changed",
            "old_value": {"status": old_status},
            "new_value": {"status": update.status},
        }).execute()
    except Exception:
        pass

    return result.data[0]
