from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from database import (
    get_all_schedules, 
    get_timetable_data, 
    cancel_class, 
    reset_all_schedules, 
    restore_all_schedules, 
    add_notification,
    clear_all_notifications,
    _seed_schedule_alerts,
    reset_subject_schedule,
    make_schedule_permanent,
    process_merge_response,
    check_teacher_availability,
    merge_requests_table,
    db,
    time_slots
)

scheduling_router = APIRouter()

class ClassCancellationRequest(BaseModel):
    subject: str
    targetday: str

class SubjectResetRequest(BaseModel):
    subject: str
    family: Optional[str] = None

class MergeResponseRequest(BaseModel):
    notification_id: int
    approved: bool

class NegotiateMergeRequest(BaseModel):
    request_id: int
    action: str  # 'accept', 'reject', 'propose', 'later'
    proposed_day: Optional[str] = None
    proposed_time_slot: Optional[str] = None
    branch: str = "BCA"  # The branch of the person responding (Target or Requester)

# Finds a time where both departments are free for a merge
async def find_mutual_free_slot(branch_a: str, branch_b: str) -> Optional[str]:
    grid_a = await get_timetable_data(is_revised=True, branch=branch_a)
    grid_b = await get_timetable_data(is_revised=True, branch=branch_b)
    
    occupied_a = set()
    for r in grid_a:
        if r["subject"] and r["subject"] != "LUNCH" and r["subject"] != "":
            occupied_a.add(f"{r['day']} {r['time_slot']}")
            
    occupied_b = set()
    for r in grid_b:
        if r["subject"] and r["subject"] != "LUNCH" and r["subject"] != "":
            occupied_b.add(f"{r['day']} {r['time_slot']}")
            
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    for d in days:
        for t in time_slots:
            if t == "12:50-1:50": continue # Skip Lunch
            key = f"{d} {t}"
            if key not in occupied_a and key not in occupied_b:
                return key # Returns "Day TimeSlot" string
                
    return None

# Lists all awaiting merge requests for a teacher's branch
@scheduling_router.get("/pending_merges")
async def get_pending_merges(branch: str = "BCA"):
    
    from sqlalchemy import or_, and_
    
    query = merge_requests_table.select().where(
        or_(
            and_(
                or_(
                    ((merge_requests_table.c.target_branch == branch) & 
                     ((merge_requests_table.c.target_consent == False) | (merge_requests_table.c.target_consent == None))),
                    ((merge_requests_table.c.requestor_branch == branch) & 
                     ((merge_requests_table.c.requester_consent == False) | (merge_requests_table.c.requester_consent == None)))
                ),
                (merge_requests_table.c.status.in_(["pending", "negotiation"]))
            ),
            and_(
                (merge_requests_table.c.requestor_branch == branch),
                (merge_requests_table.c.status == "fallback_pending")
            )
        )
    )
    records = await db.fetch_all(query)
    
    results = []
    for r in records:
        d = dict(r)
        
        conflict = await check_teacher_availability(branch, d["day"], d["time_slot"])
        d["has_conflict"] = conflict is not None
        d["conflict_details"] = conflict
        
        suggested = await find_mutual_free_slot(d["requestor_branch"], d["target_branch"])
        d["suggested_alternative"] = suggested
        
        results.append(d)
        
    return {"requests": results}

# Rejects all currently pending merge requests at once
@scheduling_router.post("/clear_merges")
async def clear_merges(branch: str = "BCA"):
    await db.execute(merge_requests_table.update().where(
        (merge_requests_table.c.target_branch == branch) &
        (merge_requests_table.c.status.in_(["pending", "negotiation"]))
    ).values(status="rejected"))
    
    await db.execute(merge_requests_table.update().where(
        (merge_requests_table.c.requestor_branch == branch) &
        (merge_requests_table.c.status.in_(["pending", "negotiation"]))
    ).values(status="rejected"))
    
    return {"success": True, "message": "All pending merge requests have been cleared."}

# Handles the decision-making process for a merge request
@scheduling_router.post("/negotiate_merge")
async def negotiate_merge(req: NegotiateMergeRequest):
    
    query = merge_requests_table.select().where(merge_requests_table.c.id == req.request_id)
    record = await db.fetch_one(query)
    
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
        
    r_dict = dict(record)
    
    if req.action == "reject":
        if r_dict["notification_id"]:
            await process_merge_response(r_dict["notification_id"], False)
        else:
            await db.execute(merge_requests_table.update().where(
                merge_requests_table.c.id == req.request_id
            ).values(status="rejected"))
            
        return {"success": True, "message": "Request rejected"}
        
    elif req.action == "fallback_delay":
        from database import update_schedule, add_notification, schedule_table
        await update_schedule(r_dict["subject"], "Delayed", target_day=r_dict["day"])
        await db.execute(merge_requests_table.update().where(
            merge_requests_table.c.id == req.request_id
        ).values(status="rejected"))
        
        # Look up the new time that update_schedule settled on
        updated_row = await db.fetch_one(schedule_table.select().where(
            (schedule_table.c.subject == r_dict["subject"]) &
            (schedule_table.c.branch == req.branch)
        ))
        
        new_time_str = updated_row["new_time"] if (updated_row and updated_row["new_time"]) else "a new timing"
        
        await add_notification(
            title=f"{r_dict['subject']} Rescheduled",
            message=f"{r_dict['subject']} was shifted to {new_time_str}.",
            n_type="schedule_change",
            teacher_message=f"{r_dict['subject']} delayed by 1 hour as fallback to declined merge.",
            branch=req.branch
        )
        
        return {"success": True, "message": "Class shifted 1 hour later."}
        
    elif req.action == "fallback_leave":
        from database import update_schedule
        await update_schedule(r_dict["subject"], "On Schedule", target_day=r_dict["day"])
        await db.execute(merge_requests_table.update().where(
            merge_requests_table.c.id == req.request_id
        ).values(status="rejected"))
        return {"success": True, "message": "Class left as is."}

    elif req.action == "accept":
        is_target = (req.branch == r_dict["target_branch"])
        
        # Check for conflict if accepting onto target branch
        if is_target:
            from database import check_teacher_availability
            conflict = await check_teacher_availability(r_dict["target_branch"], r_dict["day"], r_dict["time_slot"])
            if conflict:
                return {"success": False, "message": f"Conflict detected: You already have {conflict} at {r_dict['time_slot']}."}
                
        update_values = {}
        if is_target:
            update_values["target_consent"] = True
        else:
            update_values["requester_consent"] = True
            
        target_agreed = r_dict["target_consent"] or (is_target and True)
        requester_agreed = r_dict["requester_consent"] or (not is_target and True)
        
        if target_agreed and requester_agreed:
            
            await db.execute(merge_requests_table.update().where(
                merge_requests_table.c.id == req.request_id
            ).values(**update_values))
            
            if r_dict["notification_id"]:
                await process_merge_response(r_dict["notification_id"], True)
                
            return {"success": True, "message": "Merge finalized and scheduled!"}
        else:
            await db.execute(merge_requests_table.update().where(
                merge_requests_table.c.id == req.request_id
            ).values(**update_values))
            
            return {"success": True, "message": "Consent recorded. Waiting for other party."}
            
    elif req.action == "propose":
        
        if not req.proposed_day or not req.proposed_time_slot:
             raise HTTPException(status_code=400, detail="Missing proposed time")

        is_requester = (req.branch == r_dict["requestor_branch"])
        
        new_requester_consent = True if is_requester else False
        new_target_consent = True if not is_requester else False # Wait, if Target proposes, Target consents.

        update_values = {
            "proposed_day": req.proposed_day,
            "proposed_time_slot": req.proposed_time_slot,
            "status": "negotiation",
            "requester_consent": True if (req.branch == r_dict["requestor_branch"]) else False,
            "target_consent": True if (req.branch == r_dict["target_branch"]) else False
        }
        
        await db.execute(merge_requests_table.update().where(
            merge_requests_table.c.id == req.request_id
        ).values(**update_values))
        
        other_branch = r_dict["target_branch"] if (req.branch == r_dict["requestor_branch"]) else r_dict["requestor_branch"]
        
        msg = f"New time proposed for merge: {req.proposed_day} {req.proposed_time_slot}. Please accept or reject."
        await add_notification(
            title="Merge Time Proposal",
            message="",
            n_type="merge_proposal", # Special type for frontend handling?
            branch=other_branch,
            teacher_message=msg # Visible to teacher
        )
        
        return {"success": True, "message": "Proposal sent."}
        
    return {"success": False, "message": "Invalid action"}

# Submits a final approve or reject response to a merge
@scheduling_router.post("/respond_to_merge")
async def respond_to_merge(req: MergeResponseRequest):
    success, msg = await process_merge_response(req.notification_id, req.approved)
    return {"success": success, "message": msg}

# Gets a list of every class that has been moved
@scheduling_router.get("/reschedule")
async def fetch_rescheduled_classes(branch: str = "BCA"):
    statuslist = await get_all_schedules(branch=branch)
    return {"classes": statuslist}

# Returns a structured timetable ready for the frontend grid
@scheduling_router.get("/timetable")
async def retrieve_formatted_timetable(revised: bool = False, branch: str = "BCA"):
    rawtimetablerecords = await get_timetable_data(is_revised=revised, branch=branch)
    
    daysofweek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    def shorten_name(name):
        if not name: return ""
        n = name.upper()
        if "ARTIFICIAL INTELLIGENCE" in n or n == "AI": return "AI"
        if "INTERNET OF THINGS" in n or n == "IOT": return "IoT"
        return name

    formattedschedule = []

    for dayname in daysofweek:
        subjectsforday = []
        for slot in time_slots:
            match_row = next((r for r in rawtimetablerecords if r["day"] == dayname and r["time_slot"] == slot), None)
            
            if match_row:
                subjectsforday.append({
                    "name": shorten_name(match_row["subject"]),
                    "occupancy": match_row.get("occupancy_count", 0)
                })
            else:
                subjectsforday.append({
                    "name": "",
                    "occupancy": 0
                })
        
        formattedschedule.append({
            "day": dayname, 
            "times": subjectsforday
        })
        
    return {"schedule": formattedschedule}

# Triggers the removal of a class from the daily schedule
@scheduling_router.post("/cancel_class")
async def process_class_cancellation(requestdata: ClassCancellationRequest):
    await cancel_class(requestdata.subject, requestdata.targetday)
    
    return {
        "success": True, 
        "message": f"Successfully cancelled {requestdata.subject} for {requestdata.targetday}"
    }

# Reverts the entire timetable back to its original state
@scheduling_router.post("/reset_timetable")
async def revert_timetable_to_original():
    await reset_all_schedules()
    await clear_all_notifications()
    await _seed_schedule_alerts()
    
    await add_notification(
        title="Timetable Reset",
        message="Timetable has been reverted to original timings.",
        n_type="alert",
        teacher_message="Timetable reverted to original."
    )
    
    return {
        "success": True, 
        "message": "Timetable reverted to original state."
    }

# Re-applies all active schedule changes to the grid
@scheduling_router.post("/restore_timetable")
async def restore_timetable_changes():
    from database import schedule_table, db
    active_check = await db.fetch_all(schedule_table.select().where((schedule_table.c.is_active == False) & (schedule_table.c.status != "On Schedule")))
    if len(active_check) == 0:
        return {"success": True, "message": "No changes were made to timetable."}

    await restore_all_schedules()
    await _seed_schedule_alerts()
    
    await add_notification(
        title="Timetable Updated",
        message="The timetable modifications have been restored. Please check for new schedule changes.",
        n_type="info",
        teacher_message="You have restored the revised timetable. Test periods resumed."
    )
    
    return {
        "success": True, 
        "message": "Timetable changes restored successfully."
    }
# Resets a specific subject's schedule to normal
@scheduling_router.post("/reset_subject")
async def reset_specific_subject(req: SubjectResetRequest):
    await reset_subject_schedule(req.subject)
    await _seed_schedule_alerts()
    from database import schedule_table, db
    s_row = await db.fetch_one(schedule_table.select().where(schedule_table.c.subject == req.subject))
    target_branch = s_row["branch"] if s_row else "BCA"

    await add_notification(
        title=f"{req.subject} Reset",
        message=f"The schedule for {req.subject} has been reverted to original.",
        n_type="info",
        teacher_message=f"Changes for {req.subject} were manually reverted.",
        branch=target_branch
    )
    
    return {"success": True, "message": f"Reset {req.subject} successfully."}

# Checks for any trials that have finished their 2-week period
@scheduling_router.get("/check_test_periods")
async def check_completed_test_periods():
    from database import schedule_table, db
    from datetime import datetime
    
    query = schedule_table.select().where(
        (schedule_table.c.is_active == True) & 
        (schedule_table.c.test_period_start.isnot(None)) &
        (schedule_table.c.status != "On Schedule")
    )
    records = await db.fetch_all(query)
    
    completed = []
    now = datetime.now()
    
    for r in records:
        try:
            val = r["test_period_start"]
            if not val:
                continue
            if isinstance(val, str):
                start_date = datetime.fromisoformat(val)
            elif isinstance(val, datetime):
                start_date = val
            else:
                continue
            
            delta = now - start_date
            if delta.days >= 14:
                completed.append({
                    "id": r["id"],
                    "subject": r["subject"],
                    "new_time": r["new_time"],
                    "status": r["status"]
                })
        except Exception:
            continue
            
    return {"completed": completed}

# Adds more time to a class's scheduling trial period
@scheduling_router.post("/extend_test_period")
async def extend_test_period(req: SubjectResetRequest):
    from database import schedule_table, db
    from datetime import datetime
    
    query = schedule_table.update().where(
        schedule_table.c.subject == req.subject
    ).values(
        test_period_start=datetime.now().isoformat(),
        test_weeks_total=2
    )
    await db.execute(query)
    
    s_row = await db.fetch_one(schedule_table.select().where(schedule_table.c.subject == req.subject))
    target_branch = s_row["branch"] if s_row else "BCA"

    await add_notification(
        title=f"{req.subject} Extended",
        message=f"The test period for {req.subject} has been extended by 2 weeks.",
        n_type="info",
        teacher_message=f"Test period for {req.subject} extended due to teacher request.",
        branch=target_branch
    )
    
    return {"success": True}

# Marks a temporary schedule change as the new permanent one
@scheduling_router.post("/make_permanent")
async def commit_subject_change(req: SubjectResetRequest):
    await make_schedule_permanent(req.subject)
    await _seed_schedule_alerts()
    from database import schedule_table, db
    s_row = await db.fetch_one(schedule_table.select().where(schedule_table.c.subject == req.subject))
    target_branch = s_row["branch"] if s_row else "BCA"

    await add_notification(
        title=f"{req.subject} Confirmed",
        message=f"The new schedule for {req.subject} is now permanent.",
        n_type="success",
        teacher_message=f"Change for {req.subject} was marked as permanent.",
        branch=target_branch
    )
    return {"success": True, "message": f"Made {req.subject} permanent."}
