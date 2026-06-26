from pydantic import BaseModel
from typing import Optional


class CreditCreate(BaseModel):
    scan_id: str
    plot_id: str
    owner_id: str
    vintage_year: int
    quantity_tco2e: float
    price_per_tonne: float
    integrity_score: float
    risk_score: float = 0.0
    permanence_discount: float = 0.0


class CreditResponse(BaseModel):
    id: str
    scan_id: Optional[str] = None
    plot_id: str
    owner_id: str
    vintage_year: int
    quantity_tco2e: float
    price_per_tonne: float
    status: str
    integrity_score: float
    risk_score: float
    permanence_discount: float
    listed_at: Optional[str] = None
    sold_at: Optional[str] = None
    retired_at: Optional[str] = None
    created_at: Optional[str] = None
    # Joined fields
    region: Optional[str] = None
    plot_name: Optional[str] = None


class CreditStatusUpdate(BaseModel):
    status: str


class CreditStats(BaseModel):
    total_credits: int
    total_verified: int
    total_pending_approval: int
    total_listed: int
    total_sold: int
    total_retired: int
    total_tco2e: float
    avg_price: float
    avg_integrity: float
