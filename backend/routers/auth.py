from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_admin_client
from services.auth_deps import (
    get_current_user,
    get_current_user_no_role_required,
    require_role,
    AuthedUser,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Roles per the revised capstone proposal (Section 3.4): steward,
# analyst, research_admin. Stored in auth.users.app_metadata (see
# /set-role below), never in a client-writable location.
VALID_ROLES = ("steward", "analyst", "research_admin")


class SetRoleRequest(BaseModel):
    role: str
    assigned_district: Optional[str] = None
    full_name: str
    company_name: Optional[str] = None
    precise_location_consent: bool = False  # Section 3.6 safeguard 3


class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    assigned_district: Optional[str] = None
    company_name: Optional[str] = None
    precise_location_consent: Optional[bool] = False
    created_at: Optional[str] = None


@router.post("/set-role", response_model=ProfileResponse)
async def set_role(data: SetRoleRequest, caller: AuthedUser = Depends(get_current_user_no_role_required)):
    """Complete signup: assign a role (+ optional district) in the caller's
    auth.users.app_metadata — service-role-only writable, so this can never
    be self-escalated by a client — and create their public.profiles row.
    Called by the frontend immediately after supabase.auth.signUp() resolves.
    """
    if data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of {VALID_ROLES}",
        )

    db = get_admin_client()

    try:
        db.auth.admin.update_user_by_id(
            caller.id,
            {
                "app_metadata": {
                    "role": data.role,
                    "assigned_district": data.assigned_district,
                }
            },
        )
    except Exception as e:
        logger.error(f"set-role: failed to update app_metadata for {caller.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role",
        )

    profile_data = {
        "id": caller.id,
        "email": caller.email,
        "full_name": data.full_name,
        "company_name": data.company_name,
        "precise_location_consent": data.precise_location_consent,
        "created_at": datetime.now().isoformat(),
    }

    try:
        # upsert (not insert): makes this endpoint safely retryable — if a
        # prior call updated app_metadata.role but then failed here, the
        # caller now passes get_current_user's role check and may retry
        # set-role, which must not fail on a duplicate-key conflict.
        result = db.table("profiles").upsert(profile_data).execute()
        if not result.data:
            logger.error(f"set-role: profile upsert returned no data for {caller.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create profile",
            )
        profile = result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"set-role: profile upsert failed for {caller.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile",
        )

    logger.info(f"Role assigned: {caller.email} -> {data.role}")

    return ProfileResponse(
        **{
            **profile,
            "role": data.role,
            "assigned_district": data.assigned_district,
        }
    )


@router.get("/me", response_model=ProfileResponse)
async def get_current_profile(caller: AuthedUser = Depends(get_current_user)):
    """Return the verified caller's identity + profile."""
    db = get_admin_client()
    result = db.table("profiles").select("*").eq("id", caller.id).execute()

    profile = result.data[0] if result.data else {}

    return ProfileResponse(
        id=caller.id,
        email=caller.email,
        role=caller.role,
        assigned_district=caller.assigned_district,
        full_name=profile.get("full_name", ""),
        company_name=profile.get("company_name"),
        precise_location_consent=profile.get("precise_location_consent", False),
        created_at=profile.get("created_at"),
    )


@router.get("/user-by-email")
async def get_user_by_email(
    email: str, caller: AuthedUser = Depends(require_role("research_admin"))
):
    """Resolve an email to its profile (id, name, etc). research_admin only —
    used by the admin 'Auto Scan on behalf of a steward' workflow."""
    db = get_admin_client()
    result = db.table("profiles").select("*").eq("email", email.strip().lower()).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return result.data[0]
