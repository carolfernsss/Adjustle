from fastapi import APIRouter
from Backend.database import get_notifs
from typing import List, Optional

# // Create a router specifically for notification-related endpoints
router = APIRouter()

@router.get("/notifications")
async def fetch_notifications(branch: str = "BCA"):
    # // Retrieves the list of notifications filtered by the user's branch
    notifications = await get_notifs(branch)
    return {"notifications": notifications}

# // Potential future extension: mark as read or delete notifications
@router.post("/notifications/clear")
async def clear_notifications(branch: str = "BCA"):
    # // Logic to clear notifications for a specific branch
    from database import clear_notifications_by_branch
    await clear_notifications_by_branch(branch)
    return {"success": True, "message": f"Notifications for {branch} cleared"}
