from pydantic import BaseModel
from typing import Optional


class TransactionCreate(BaseModel):
    credit_id: str
    buyer_id: str
    quantity_tco2e: float
    total_price: float
    currency: str = "USD"


class TransactionResponse(BaseModel):
    id: str
    credit_id: str
    buyer_id: str
    seller_id: Optional[str] = None
    quantity_tco2e: float
    total_price: float
    currency: str
    certificate_url: Optional[str] = None
    status: str
    created_at: Optional[str] = None
