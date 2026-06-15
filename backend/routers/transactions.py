import uuid
from fastapi import APIRouter, HTTPException
from models.transaction import TransactionCreate, TransactionResponse
from database import get_supabase_client

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse)
async def create_transaction(tx: TransactionCreate):
    db = get_supabase_client()

    # Get credit to find seller
    credit = db.table("carbon_credits").select("*").eq("id", tx.credit_id).execute()
    if not credit.data:
        raise HTTPException(status_code=404, detail="Credit not found")

    credit_data = credit.data[0]
    if credit_data["status"] not in ("verified", "listed"):
        raise HTTPException(status_code=400, detail="Credit is not available for purchase")

    tx_id = str(uuid.uuid4())
    tx_data = {
        "id": tx_id,
        "credit_id": tx.credit_id,
        "buyer_id": tx.buyer_id,
        "seller_id": credit_data.get("owner_id"),
        "quantity_tco2e": tx.quantity_tco2e,
        "total_price": tx.total_price,
        "currency": tx.currency,
        "status": "completed",
        "certificate_url": f"/api/certificates/{tx_id}",
    }
    result = db.table("transactions").insert(tx_data).execute()

    # Update credit status to sold
    db.table("carbon_credits").update({"status": "sold"}).eq("id", tx.credit_id).execute()

    # Audit log
    try:
        db.table("audit_log").insert({
            "id": str(uuid.uuid4()),
            "entity_type": "transaction",
            "entity_id": tx_id,
            "action": "created",
            "new_value": {"buyer_id": tx.buyer_id, "total_price": tx.total_price},
            "performed_by": tx.buyer_id,
        }).execute()
    except Exception:
        pass

    return result.data[0]


@router.get("/{tx_id}")
async def get_transaction(tx_id: str):
    db = get_supabase_client()
    result = db.table("transactions").select("*").eq("id", tx_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result.data[0]


@router.get("/buyer/{buyer_id}")
async def get_buyer_transactions(buyer_id: str):
    db = get_supabase_client()
    result = (
        db.table("transactions")
        .select("*")
        .eq("buyer_id", buyer_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
