# code for managing class times
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

# setting up the setup for schedule requests
scheduling_router = APIRouter()

# --- Data Models ---

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

# --- Helper Functions ---

# finding a time when both classes are free
async def find_mutual_free_slot(branch_a: str, branch_b: str) -> Optional[str]:
    # Finds a common free slot between two branches in the REVISED grid
    grid_a = await get_timetable_data(is_revised=True, branch=branch_a)
    grid_b = await get_timetable_data(is_revised=True, branch=branch_b)
    
    # Identify occupied slots
    occupied_a = set()
    for r in grid_a:
        if r["subject"] and r["subject"] != "LUNCH" and r["subject"] != "":
            occupied_a.add(f"{r['day']} {r['time_slot']}")
            
    occupied_b = set()
    for r in grid_b:
        if r["subject"] and r["subject"] != "LUNCH" and r["subject"] != "":
            occupied_b.add(f"{r['day']} {r['time_slot']}")
            
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # Iterate through days and slots to find a match
    for d in days:
        for t in time_slots:
            if t == "12:50-1:50": continue # Skip Lunch
            key = f"{d} {t}"
            if key not in occupied_a and key not in occupied_b:
                return key # Returns "Day TimeSlot" string
                
    return None

# --- Endpoints ---

# getting all the pending merge requests
@scheduling_router.get("/pending_merges")
async def get_pending_merges(branch: str = "BCA"):
    # Returns pending merge requests where the USER (branch) needs to act.
    # print(f"DEBUG: Fetching pending merges for branch: {branch}")
    
    from sqlalchemy import or_, and_
    
    # Query pending and negotiation status requests for this branch
    query = merge_requests_table.select().where(
        and_(
            or_(
                ((merge_requests_table.c.target_branch == branch) & 
                 ((merge_requests_table.c.target_consent == False) | (merge_requests_table.c.target_consent == None))),
                ((merge_requests_table.c.requestor_branch == branch) & 
                 ((merge_requests_table.c.requester_consent == False) | (merge_requests_table.c.requester_consent == None)))
            ),
            (merge_requests_table.c.status.in_(["pending", "negotiation"]))
        )
    )
    records = await db.fetch_all(query)
    # print(f"DEBUG: Found {len(records)} pending requests for {branch}")
    
    results = []
    for r in records:
        d = dict(r)
        
        # Check for potential conflicts with existing classes for the current branch
        conflict = await check_teacher_availability(branch, d["day"], d["time_slot"])
        d["has_conflict"] = conflict is not None
        d["conflict_details"] = conflict
        
        # If conflict exists or negotiation requested, find free slot
        suggested = await find_mutual_free_slot(d["requestor_branch"], d["target_branch"])
        d["suggested_alternative"] = suggested
        
        results.append(d)
        
    return {"requests": results}

@scheduling_router.post("/clear_merges")
async def clear_merges(branch: str = "BCA"):
    # Rejects all pending merge requests for the given branch
    # Update as target
    await db.execute(merge_requests_table.update().where(
        (merge_requests_table.c.target_branch == branch) &
        (merge_requests_table.c.status.in_(["pending", "negotiation"]))
    ).values(status="rejected"))
    
    # Update as requester
    await db.execute(merge_requests_table.update().where(
        (merge_requests_table.c.requestor_branch == branch) &
        (merge_requests_table.c.status.in_(["pending", "negotiation"]))
    ).values(status="rejected"))
    
    return {"success": True, "message": "All pending merge requests have been cleared."}

# letting teachers approve or reject merges
@scheduling_router.post("/negotiate_merge")
async def negotiate_merge(req: NegotiateMergeRequest):
    # Handles complex merge negotiation (Accept, Reject, Propose New Time)
    
    # 1. Fetch request record
    query = merge_requests_table.select().where(merge_requests_table.c.id == req.request_id)
    record = await db.fetch_one(query)
    
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
        
    r_dict = dict(record)
    
    if req.action == "reject":
        # Simply mark rejected via existing logic
        if r_dict["notification_id"]:
            await process_merge_response(r_dict["notification_id"], False)
        else:
            await db.execute(merge_requests_table.update().where(
                merge_requests_table.c.id == req.request_id
            ).values(status="rejected"))
            
        return {"success": True, "message": "Request rejected"}

    elif req.action == "accept":
        # Determines who accepted and if we can finalize
        is_target = (req.branch == r_dict["target_branch"])
        
        update_values = {}
        if is_target:
            update_values["target_consent"] = True
        else:
            update_values["requester_consent"] = True
            
        # Check if BOTH consented (including the update we are about to make)
        target_agreed = r_dict["target_consent"] or (is_target and True)
        requester_agreed = r_dict["requester_consent"] or (not is_target and True)
        
        if target_agreed and requester_agreed:
            # Both agreed! Finalize.
            # We use notification_id to trigger process_merge_response logic if available
            # But process_merge_response updates DB based on requester/target logic assumption
            # It should just work if we update consents first?
            # Actually process_merge_response logic (Line 908) does NOT check consents. It assumes "Approved" means Go.
            # So we can call it directly.
            
            # Update DB consents
            await db.execute(merge_requests_table.update().where(
                merge_requests_table.c.id == req.request_id
            ).values(**update_values))
            
            if r_dict["notification_id"]:
                await process_merge_response(r_dict["notification_id"], True)
                
            return {"success": True, "message": "Merge finalized and scheduled!"}
        else:
            # Update DB only
            await db.execute(merge_requests_table.update().where(
                merge_requests_table.c.id == req.request_id
            ).values(**update_values))
            
            return {"success": True, "message": "Consent recorded. Waiting for other party."}
            
    elif req.action == "propose":
        # Propose a new time
        # Reset consents because terms changed!
        # Both must agree to the NEW time.
        # But the PROPOSER implicitly consents.
        
        if not req.proposed_day or not req.proposed_time_slot:
             raise HTTPException(status_code=400, detail="Missing proposed time")

        is_requester = (req.branch == r_dict["requestor_branch"])
        
        new_requester_consent = True if is_requester else False
        new_target_consent = True if not is_requester else False # Wait, if Target proposes, Target consents.
        
        # logic:
        # If Target proposes: target_consent=True, requester_consent=False
        # If Requester proposes: requester_consent=True, target_consent=False
        
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
        
        # Notify the OTHER party
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


# saving the final merge decision
@scheduling_router.post("/respond_to_merge")
async def respond_to_merge(req: MergeResponseRequest):
    success, msg = await process_merge_response(req.notification_id, req.approved)
    return {"success": success, "message": msg}

@scheduling_router.get("/reschedule")
async def fetch_rescheduled_classes(branch: str = "BCA"):
    statuslist = await get_all_schedules(branch=branch)
    return {"classes": statuslist}

# getting the full timetable display
@scheduling_router.get("/timetable")
async def retrieve_formatted_timetable(revised: bool = False, branch: str = "BCA"):
    # 1. Fetch raw records from database
    rawtimetablerecords = await get_timetable_data(is_revised=revised, branch=branch)
    
    # 2. Define the structural order of days and time slots
    daysofweek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    # time_slots imported from database
    local_slots = [
        "9:15-10:05", "10:10-11:00", "11:05-11:55", "12:00-12:50", 
        "12:50-1:50", "1:50-2:40", "2:45-3:35", "3:40-4:30"
    ]
    
    formattedschedule = []

    # 3. Organize records by day and ensure time slot order
    for dayname in daysofweek:
        subjectsforday = []
        for slot in local_slots:
            # Find the subject and occupancy for this specific day and time slot
            match_row = next((r for r in rawtimetablerecords if r["day"] == dayname and r["time_slot"] == slot), None)
            
            if match_row:
                subjectsforday.append({
                    "name": match_row["subject"],
                    "occupancy": match_row.get("occupancy_count", 0)
                })
            else:
                subjectsforday.append({
                    "name": "",
                    "occupancy": 0
                })
        
        # Add the day's schedule to our result
        formattedschedule.append({
            "day": dayname, 
            "times": subjectsforday
        })
        
    return {"schedule": formattedschedule}

@scheduling_router.post("/cancel_class")
async def process_class_cancellation(requestdata: ClassCancellationRequest):
    # Handles a manual request to cancel a specific class instance.
    await cancel_class(requestdata.subject, requestdata.targetday)
    
    return {
        "success": True, 
        "message": f"Successfully cancelled {requestdata.subject} for {requestdata.targetday}"
    }

@scheduling_router.post("/reset_timetable")
async def revert_timetable_to_original():
    # Reverts the timetable to its original, static state.
    # 1. Check if there are any active changes to reset
    from database import schedule_table, db
    active_check = await db.fetch_all(schedule_table.select().where(schedule_table.c.is_active == True))
    if len(active_check) == 0:
        return {"success": True, "message": "No changes were made to timetable."}

    # 2. Perform database update
    await reset_all_schedules()
    await clear_all_notifications()
    await _seed_schedule_alerts()
    
    # 3. Broadcast notification to teachers and students
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

@scheduling_router.post("/restore_timetable")
async def restore_timetable_changes():
    # 1. Check if there are any changes in the database to restore
    from database import schedule_table, db
    active_check = await db.fetch_all(schedule_table.select().where((schedule_table.c.is_active == False) & (schedule_table.c.status != "On Schedule")))
    if len(active_check) == 0:
        return {"success": True, "message": "No changes were made to timetable."}

    # 2. Update the database visibility
    await restore_all_schedules()
    await _seed_schedule_alerts()
    
    # 3. Let the students know that the changes are back
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
@scheduling_router.post("/reset_subject")
async def reset_specific_subject(req: SubjectResetRequest):
    # Resets only a specific subject's visibility and grid position
    await reset_subject_schedule(req.subject)
    await _seed_schedule_alerts()
    # Find branch for the subject to route notification correctly
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

@scheduling_router.get("/check_test_periods")
async def check_completed_test_periods():
    # Find all active schedule changes where the test period has expired
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
            # Test period is 2 weeks (14 days)
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

@scheduling_router.post("/extend_test_period")
async def extend_test_period(req: SubjectResetRequest):
    # Extends the test period by another 2 weeks
    from database import schedule_table, db
    from datetime import datetime
    
    query = schedule_table.update().where(
        schedule_table.c.subject == req.subject
    ).values(
        test_period_start=datetime.now().isoformat(),
        test_weeks_total=2
    )
    await db.execute(query)
    
    # Find branch for routing
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

@scheduling_router.post("/make_permanent")
async def commit_subject_change(req: SubjectResetRequest):
    # Makes a rescheduled/delayed class the new 'permanent' state
    await make_schedule_permanent(req.subject)
    await _seed_schedule_alerts()
    # Find branch for routing
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
