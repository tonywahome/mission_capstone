"""FastAPI dependencies for verifying Supabase Auth JWTs.

Replaces the old `sessions` table + `resolve_role`/`resolve_role_name`
lookup (backend/services/privacy.py, pre-migration) now that the backend
uses real Supabase Auth. There is no JWT secret configured anywhere in this
codebase, so verification goes through `auth.get_user(token)` — a live
GoTrue call via the service-role client — rather than a local signature
decode. This also gets instant revocation on logout for free, since it
checks live GoTrue state instead of trusting a cached secret.

`role` and `assigned_district` are read from the verified user's
`app_metadata`, which only a service-role key can write (see
routers/auth.py's `/set-role`) — so a caller can never self-escalate by
editing a client-side value.
"""
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from database import get_admin_client


class AuthedUser(BaseModel):
    id: str
    email: str
    role: str
    assigned_district: Optional[str] = None


def _parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def _verify(token: str) -> AuthedUser:
    try:
        response = get_admin_client().auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = getattr(response, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    app_metadata = user.app_metadata or {}
    role = app_metadata.get("role")
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has no role assigned — complete signup via /api/auth/set-role",
        )

    return AuthedUser(
        id=user.id,
        email=user.email,
        role=role,
        assigned_district=app_metadata.get("assigned_district"),
    )


def get_current_user(authorization: Optional[str] = Header(None)) -> AuthedUser:
    """Require a valid bearer token. Raises 401 if missing/invalid."""
    token = _parse_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    return _verify(token)


def _verify_no_role_required(token: str) -> AuthedUser:
    """Same as `_verify`, but does not reject an account with no role yet.
    Used only by `/api/auth/set-role` — the endpoint that assigns the role
    in the first place, so it can never require one to already exist.
    Every other endpoint must keep using `_verify` (via `get_current_user`),
    which is intentionally strict."""
    try:
        response = get_admin_client().auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = getattr(response, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    app_metadata = user.app_metadata or {}
    return AuthedUser(
        id=user.id,
        email=user.email,
        role=app_metadata.get("role") or "",
        assigned_district=app_metadata.get("assigned_district"),
    )


def get_current_user_no_role_required(
    authorization: Optional[str] = Header(None),
) -> AuthedUser:
    """Require a valid bearer token (a real, live Supabase user) but do NOT
    require `app_metadata.role` to already be set. Only for
    `/api/auth/set-role` — the one endpoint a brand-new signup with no role
    yet must be able to reach."""
    token = _parse_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    return _verify_no_role_required(token)


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
) -> Optional[AuthedUser]:
    """Best-effort auth for endpoints that serve both authenticated and
    anonymous callers at reduced privilege (e.g. coordinate rounding).
    Never raises — returns None for a missing or invalid token, which
    callers should treat as least-privilege."""
    token = _parse_bearer(authorization)
    if not token:
        return None
    try:
        return _verify(token)
    except HTTPException:
        return None


def require_role(*roles: str):
    """Dependency factory: require the caller be authenticated AND hold one
    of the given roles. Usage: Depends(require_role("research_admin"))."""

    def dependency(caller: AuthedUser = Depends(get_current_user)) -> AuthedUser:
        if caller.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role in {roles}",
            )
        return caller

    return dependency
