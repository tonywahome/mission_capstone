from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from database import get_admin_client
from services.auth_deps import get_current_user, AuthedUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool
    created_at: str


@router.get("")
async def get_notifications(caller: AuthedUser = Depends(get_current_user)):
    """Get all notifications for the authenticated caller."""
    try:
        db = get_admin_client()
        result = db.table("notifications")\
            .select("*")\
            .eq("user_id", caller.id)\
            .order("created_at", desc=True)\
            .execute()

        return {"notifications": result.data or []}

    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.get("/me")
async def get_my_notifications(caller: AuthedUser = Depends(get_current_user)):
    """Get all notifications for the logged-in user."""
    try:
        db = get_admin_client()
        result = db.table("notifications")\
            .select("*")\
            .eq("user_id", caller.id)\
            .order("created_at", desc=True)\
            .execute()

        return {"notifications": result.data or []}

    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.get("/unread-count")
async def get_unread_count(caller: AuthedUser = Depends(get_current_user)):
    """Get count of unread notifications for the authenticated caller."""
    try:
        db = get_admin_client()
        result = db.table("notifications")\
            .select("id", count="exact")\
            .eq("user_id", caller.id)\
            .eq("read", False)\
            .execute()

        return {"unread_count": result.count or 0}

    except Exception as e:
        logger.error(f"Error counting notifications: {e}")
        return {"unread_count": 0}


@router.patch("/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: str, caller: AuthedUser = Depends(get_current_user)
):
    """Mark a notification as read. Only the owning user may do this."""
    try:
        db = get_admin_client()

        existing = db.table("notifications").select("user_id").eq("id", notification_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Notification not found")
        if existing.data[0].get("user_id") != caller.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this notification")

        result = db.table("notifications")\
            .update({"read": True})\
            .eq("id", notification_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Notification not found")

        return {"message": "Notification marked as read"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")


@router.post("/mark-all-read")
async def mark_all_read(caller: AuthedUser = Depends(get_current_user)):
    """Mark all notifications as read for the authenticated caller."""
    try:
        db = get_admin_client()
        db.table("notifications")\
            .update({"read": True})\
            .eq("user_id", caller.id)\
            .eq("read", False)\
            .execute()

        return {"message": "All notifications marked as read"}

    except Exception as e:
        logger.error(f"Error marking all read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")
