from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    email: str
    full_name: str
    role: str  # 'landowner', 'buyer', 'admin'
    company_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    company_name: Optional[str] = None
    created_at: Optional[str] = None
