from pydantic import BaseModel
from typing import Optional

# Roles per the revised capstone proposal (Section 3.4 class diagram):
#   steward          — registers projects, uploads field/scan data (was "landowner")
#   verifier_analyst — reviews submitted scans/field data, confirms or flags
#                      them for the audit trail (replaces self-approval; was
#                      implicitly "business"/"buyer" in the marketplace build)
#   research_admin   — exclusive access to full-precision (unrounded) data
#                      per the Section 3.6 ethical safeguards (was "admin")
VALID_ROLES = ("steward", "verifier_analyst", "research_admin")


class UserCreate(BaseModel):
    email: str
    full_name: str
    role: str  # 'steward', 'verifier_analyst', or 'research_admin'
    company_name: Optional[str] = None
    precise_location_consent: bool = False  # Section 3.6 safeguard 3


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    company_name: Optional[str] = None
    precise_location_consent: Optional[bool] = False
    created_at: Optional[str] = None
