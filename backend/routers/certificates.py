from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database import get_supabase_client
from services.certificate_generator import generate_certificate

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("/{tx_id}")
async def get_certificate(tx_id: str):
    db = get_supabase_client()

    # Fetch transaction
    tx_result = db.table("transactions").select("*").eq("id", tx_id).execute()
    if not tx_result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx = tx_result.data[0]

    # Fetch credit
    credit = db.table("carbon_credits").select("*").eq("id", tx["credit_id"]).execute()
    credit_data = credit.data[0] if credit.data else {}

    # Fetch plot
    plot = {}
    if credit_data.get("plot_id"):
        plot_result = db.table("land_plots").select("*").eq("id", credit_data["plot_id"]).execute()
        plot = plot_result.data[0] if plot_result.data else {}

    # Fetch buyer
    buyer = {}
    buyer_result = db.table("users").select("*").eq("id", tx["buyer_id"]).execute()
    if buyer_result.data:
        buyer = buyer_result.data[0]

    # Fetch seller
    seller = {}
    if tx.get("seller_id"):
        seller_result = db.table("users").select("*").eq("id", tx["seller_id"]).execute()
        if seller_result.data:
            seller = seller_result.data[0]

    tx_data = {
        "transaction_id": tx_id,
        "quantity_tco2e": tx["quantity_tco2e"],
        "buyer_name": buyer.get("full_name", "N/A"),
        "buyer_company": buyer.get("company_name", "N/A"),
        "seller_name": seller.get("full_name", "N/A"),
        "plot_region": plot.get("region", "N/A"),
        "plot_name": plot.get("name", "N/A"),
        "area_hectares": plot.get("area_hectares", 0),
        "vintage_year": credit_data.get("vintage_year", 2025),
        "integrity_score": credit_data.get("integrity_score", 0),
        "transaction_date": tx.get("created_at", "N/A"),
    }

    pdf_bytes = generate_certificate(tx_data)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="TerraFoma_Certificate_{tx_id[:8]}.pdf"'
        },
    )
