from fastapi import APIRouter
from Backend.database import get_notifs
from typing import List, Optional

# router for showing notifications
router = APIRouter()

@router.get("/notifications")
async def fetch_notifications(branch: str = "BCA"):
    # getting notifications for a branch
    notifications = await get_notifs(branch)
    return {"notifications": notifications}

# function to clear all notifications
@router.post("/notifications/clear")
async def clear_notifications(branch: str = "BCA"):
    # logic to delete notifications
    from database import clear_notifications_by_branch
    await clear_notifications_by_branch(branch)
    return {"success": True, "message": f"Notifications for {branch} cleared"}
