from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from database import get_supabase_client, get_admin_client

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
async def get_notifications(user_id: str):
    """Get all notifications for a user by user_id query param."""
    try:
        # Use admin client to bypass RLS
        db = get_admin_client()
        result = db.table("notifications")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {"notifications": result.data or []}
    
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.get("/me")
async def get_my_notifications(user_id: str):
    """Get all notifications for the logged-in user."""
    try:
        # Use admin client to bypass RLS
        db = get_admin_client()
        result = db.table("notifications")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {"notifications": result.data or []}
    
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.get("/unread-count")
async def get_unread_count(user_id: str):
    """Get count of unread notifications."""
    try:
        # Use admin client to bypass RLS
        db = get_admin_client()
        result = db.table("notifications")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .eq("read", False)\
            .execute()
        
        return {"unread_count": result.count or 0}
    
    except Exception as e:
        logger.error(f"Error counting notifications: {e}")
        return {"unread_count": 0}


@router.patch("/{notification_id}/mark-read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    try:
        # Use admin client to bypass RLS
        db = get_admin_client()
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


class MarkAllReadRequest(BaseModel):
    user_id: str


@router.post("/mark-all-read")
async def mark_all_read(request: MarkAllReadRequest):
    """Mark all notifications as read for a user."""
    try:
        db = get_admin_client()
        db.table("notifications")\
            .update({"read": True})\
            .eq("user_id", request.user_id)\
            .eq("read", False)\
            .execute()

        return {"message": "All notifications marked as read"}

    except Exception as e:
        logger.error(f"Error marking all read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")
