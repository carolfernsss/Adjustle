import os
import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Boolean, create_engine, func, and_
)
from databases import Database

load_dotenv()

DATABASE_CONN_URL = os.getenv("DATABASE_URL")

if not DATABASE_CONN_URL:
    raise ValueError(
        "CRITICAL ERROR: DATABASE_URL environment variable is MISSING. "
        "Please configure your PostgreSQL connection in the .env file."
    )

db = Database(DATABASE_CONN_URL)
metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, index=True),
    Column("email", String),
    Column("password", String),
    Column("role", String, default="student"),
    Column("branch", String, default="BCA"),
)

schedule_table = Table(
    "schedules",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("class_id", Integer), 
    Column("subject", String),
    Column("status", String), 
    Column("original_time", String, nullable=True),
    Column("new_time", String, nullable=True),
    Column("reason", String, nullable=True),
    Column("total_students", Integer, default=40),
    Column("is_active", Boolean, default=True),
    Column("test_period_start", String, nullable=True),
    Column("test_weeks_total", Integer, default=2),
    Column("branch", String, default="BCA"),
    Column("present_count", Integer, default=0),
)

notifications_table = Table(
    "notifications",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String),
    Column("message", String),
    Column("teacher_message", String, nullable=True),
    Column("type", String),
    Column("read", Boolean, default=False),
    Column("created_at", String), 
    Column("branch", String, default="BCA"),
)

timetable_table = Table(
    "timetable",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("day", String),
    Column("time_slot", String),
    Column("subject", String),
    Column("is_revised", Boolean, default=False, index=True),
    Column("branch", String, default="BCA"),
    Column("occupancy_count", Integer, default=0)
)

merge_requests_table = Table(
    "merge_requests",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("subject", String),
    Column("day", String),              # Original Day
    Column("time_slot", String),        # Original Time Slot
    Column("requestor_branch", String),
    Column("target_branch", String),
    Column("status", String, default="pending"), # pending, negotiation, approved, rejected
    Column("proposed_day", String, nullable=True),
    Column("proposed_time_slot", String, nullable=True),
    Column("requester_consent", Boolean, default=True), # Requester implicitly consents to their own request? Not if negotiated.
    Column("target_consent", Boolean, default=False),
    Column("notification_id", Integer, nullable=True),
    Column("requestor_username", String, nullable=True)
)

class UserProfile(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str = "student"

class ScheduleRecord(BaseModel):
    classid: int
    subject: str
    status: str
    originaltime: Optional[str] = None
    newtime: Optional[str] = None
    reason: Optional[str] = None

time_slots = ["9:15-10:05", "10:10-11:00", "11:05-11:55", "12:00-12:50", "12:50-1:50", "1:50-2:40", "2:45-3:35", "3:40-4:30"]

def normalize_time_slot(time_str: str) -> str:
    if not time_str: return ""
    t = time_str.strip().upper().replace("0", "", 1) if time_str.startswith("0") else time_str.strip().upper()
    mapping = {
        "9:15 AM": "9:15-10:05",
        "10:10 AM": "10:10-11:00",
        "11:05 AM": "11:05-11:55",
        "12:00 PM": "12:00-12:50",
        "1:50 PM": "1:50-2:40",
        "2:45 PM": "2:45-3:35",
        "3:40 PM": "3:40-4:30",
        # Including versions with leading zeros
        "09:15 AM": "9:15-10:05",
        "01:50 PM": "1:50-2:40",
        "02:45 PM": "2:45-3:35",
        "03:40 PM": "3:40-4:30"
    }
    return mapping.get(time_str.strip().upper(), mapping.get(t, time_str))

original_schedule_map = {
    "Monday":    ["AI", "", "IoT", "MA", "LUNCH", "Internship", "", "SE"],
    "Tuesday":   ["", "SE", "", "AI", "LUNCH", "", "PBI", ""],
    "Wednesday": ["MA", "MA LAB", "MA LAB", "", "LUNCH", "IoT", "PBI", ""],
    "Thursday":  ["", "SE", "", "", "LUNCH", "Library", "", ""],
    "Friday":    ["PBI", "", "IoT", "SE", "LUNCH", "AI", "", "MA"],
    "Saturday":  ["", "", "Project LAB", "Project LAB", "LUNCH", "", "", ""]
}

revised_schedule_map = {
    "Monday":    ["AI", "", "IoT", "MA", "LUNCH", "Internship", "", "SE"],
    "Tuesday":   ["", "SE", "", "AI", "LUNCH", "", "PBI", ""],
    "Wednesday": ["MA", "MA LAB", "MA LAB", "", "LUNCH", "IoT", "PBI", ""],
    "Thursday":  ["", "SE", "", "", "LUNCH", "Library", "", ""],
    "Friday":    ["PBI", "", "IoT", "SE", "LUNCH", "AI", "", "MA"],
    "Saturday":  ["", "", "Project LAB", "Project LAB", "LUNCH", "", "", ""]
}

bcada_original_map = {
    "Monday":    ["AI", "IoT", "", "CC", "LUNCH", "DL", "", ""],
    "Tuesday":   ["DL", "", "AI", "IoT", "LUNCH", "CC", "", "AI"],
    "Wednesday": ["IoT", "CC", "", "DL", "LUNCH", "AI", "", ""],
    "Thursday":  ["CC", "AI", "", "IoT", "LUNCH", "DL", "", "IoT"],
    "Friday":    ["DL", "", "CC", "", "LUNCH", "AI", "", ""],
    "Saturday":  ["", "", "Project LAB", "Project LAB", "LUNCH", "", "", ""]
}

bcada_revised_map = {
    "Monday":    ["AI", "IoT", "", "CC", "LUNCH", "DL", "", ""],
    "Tuesday":   ["DL", "", "AI", "IoT", "LUNCH", "CC", "", "AI"],
    "Wednesday": ["IoT", "CC", "", "DL", "LUNCH", "AI", "", ""],
    "Thursday":  ["CC", "AI", "", "IoT", "LUNCH", "DL", "", "IoT"],
    "Friday":    ["DL", "", "CC", "", "LUNCH", "AI", "", ""],
    "Saturday":  ["", "", "Project LAB", "Project LAB", "LUNCH", "", "", ""]
}

subject_family_map = {
    "AI": "ARTIFICIAL INTELLIGENCE",
    "IOT": "INTERNET OF THINGS",
    "MA": "MOBILE APPLICATIONS",
    "PBI": "POWER BI",
    "SE": "SOFTWARE ENGINEERING",
    "MA LAB": "MOBILE APPLICATIONS LAB",
    "CC": "CLOUD COMPUTING",
    "DL": "DEEP LEARNING"
}

# Cleans and standardizes the subject name for processing
def normalize_subject_token(subject_text: str) -> str:
    if not subject_text:
        return ""
    token = subject_text.strip().replace("-", " ")
    token = re.sub(r"\d+$", "", token)
    token = re.sub(r"\s+", " ", token).strip().upper()
    return token

# Maps specific class names to their broader subject category
def get_subject_family(subject_text: str) -> str:
    token = normalize_subject_token(subject_text)
    return subject_family_map.get(token, token)

# Finds the correct subject instance for a specific day and time
def resolve_subject_instance(subject_input: str, target_day: Optional[str]) -> Optional[str]:
    normalized_day = normalize_day(target_day) if target_day else None
    requested_family = get_subject_family(subject_input)
    requested_token = normalize_subject_token(subject_input)

    if normalized_day in original_schedule_map:
        for candidate in original_schedule_map[normalized_day]:
            if not candidate or candidate == "LUNCH":
                continue
            if get_subject_family(candidate) == requested_family:
                return candidate

    for subjects in original_schedule_map.values():
        for candidate in subjects:
            if not candidate or candidate == "LUNCH":
                continue
            if normalize_subject_token(candidate) == requested_token:
                return candidate

    return None

# Checks if a subject is taught in both departments
async def is_subject_shared(subject_name: str) -> bool:
    bca_subjects = set()
    for day_list in original_schedule_map.values():
        for s in day_list:
            if s and s != "LUNCH":
                bca_subjects.add(get_subject_family(s))
    
    bcada_subjects = set()
    for day_list in bcada_original_map.values():
        for s in day_list:
            if s and s != "LUNCH":
                bcada_subjects.add(get_subject_family(s))
                
    family = get_subject_family(subject_name)
    return family in bca_subjects and family in bcada_subjects

# Looks up a user account by their username
async def find_user(target_username: str) -> Optional[dict]:
    query = users_table.select().where(func.lower(users_table.c.username) == target_username.lower())
    user_record = await db.fetch_one(query)
    
    if user_record:
        return dict(user_record)

    return None

# Expands short day names to their full forms
def normalize_day(day_name: str) -> str:
    if not day_name: return "Monday"
    d = day_name.lower().replace(".", "").strip()
    mapping = {
        "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
        "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday", "sunday": "Sunday",
        "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
        "mondy": "Monday", "tuesdy": "Tuesday", "wednesdy": "Wednesday", "thursdy": "Thursday", "fridy": "Friday", "saturdy": "Saturday", "sundy": "Sunday",
        "thusdy": "Thursday"
    }
    return mapping.get(d, day_name)

# Picks the following day in the weekly cycle
def choose_reschedule_day(source_day: str) -> str:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    s = normalize_day(source_day or "Monday")
    if s not in days:
        return "Tuesday"
    
    idx = days.index(s)
    next_idx = (idx + 1) % len(days)
    return days[next_idx]

    return None

# Locates an empty time slot within a specific day
def find_smart_slot_for_day(records: List[dict], day: str, ignore_subject: Optional[str] = None, required_slots: int = 1, min_index: int = 0) -> Optional[str]:
    normalized_day = normalize_day(day)
    taken_indices = []
    ignore_lower = (ignore_subject or "").lower()

    for row in records:
        if normalize_day(row.get("day")) != normalized_day:
            continue
        subject = (row.get("subject") or "").strip()
        if not subject or subject == "LUNCH" or subject == "":
            continue
        if ignore_lower and subject.lower() == ignore_lower:
            continue
        try:
            taken_indices.append(time_slots.index(row.get("time_slot")))
        except ValueError:
            continue

    max_idx_limit = len(time_slots)
    if normalized_day == "Saturday":
        max_idx_limit = 4 

    candidates = []
    for idx in range(min_index, max_idx_limit):
        if time_slots[idx] == "12:50-1:50":
            continue
        if idx + required_slots > max_idx_limit:
            continue
            
        all_available = True
        for offset in range(required_slots):
            check_idx = idx + offset
            if check_idx >= max_idx_limit or time_slots[check_idx] == "12:50-1:50" or check_idx in taken_indices:
                all_available = False
                break
        
        if all_available:
            return time_slots[idx]

    return None

# Removes a specific subject from the active schedule grid
async def clear_subject_from_revised_grid(subject_id: str, branch: str, day: Optional[str] = None, time_slot: Optional[str] = None):
    query = timetable_table.update().where(
        (timetable_table.c.is_revised == True) &
        (timetable_table.c.branch == branch) &
        (func.lower(timetable_table.c.subject) == subject_id.lower())
    )
    if day:
        query = query.where(timetable_table.c.day == normalize_day(day))
    if time_slot:
        t = normalize_time_slot(time_slot)
        query = query.where(timetable_table.c.time_slot == t)
        
    await db.execute(query.values(subject=""))

# Puts a subject back into its original timetable positions
async def reset_subject_revised_position(subject_id: str):
    original_positions = await db.fetch_all(
        timetable_table.select().where(
            (timetable_table.c.is_revised == False) &
            (func.lower(timetable_table.c.subject) == subject_id.lower())
        )
    )
    if not original_positions:
        return
        
    target_branch = original_positions[0]["branch"]
    await clear_subject_from_revised_grid(subject_id, branch=target_branch)

    for pos in original_positions:
        pos_dict = dict(pos)
        await db.execute(
            timetable_table.update().where(
                (timetable_table.c.is_revised == True) &
                (timetable_table.c.day == pos_dict["day"]) &
                (timetable_table.c.time_slot == pos_dict["time_slot"]) &
                (timetable_table.c.branch == target_branch)
            ).values(subject=subject_id)
        )

# Shifts a class to a new day or time while moving others
async def apply_subject_change_to_revised_grid(subject_id: str, new_status: str, source_day: Optional[str] = None):
    normalized_source_day = normalize_day(source_day) if source_day else None

    if new_status in ["On Schedule", "Active"]:
        await reset_subject_revised_position(subject_id)
        return

    if new_status == "Merged":
        await reset_subject_revised_position(subject_id)
        return

    if new_status == "Cancelled":
        await clear_subject_from_revised_grid(subject_id, branch=target_branch, day=normalized_source_day)
        return

    original_positions = await db.fetch_all(
        timetable_table.select().where(
            (timetable_table.c.is_revised == False) &
            (func.lower(timetable_table.c.subject) == subject_id.lower())
        )
    )
    if not original_positions:
        return
        
    target_branch = original_positions[0]["branch"]

    if new_status == "Cancelled":
        await clear_subject_from_revised_grid(subject_id, branch=target_branch, day=normalized_source_day)
        return

    origin = None
    if normalized_source_day:
        origin = next((dict(p) for p in original_positions if dict(p).get("day") == normalized_source_day), None)
    if origin is None:
        origin = dict(original_positions[0])

    origin_day = origin["day"]
    origin_slot = origin["time_slot"]
    
    revised_records = [dict(r) for r in await db.fetch_all(
        timetable_table.select().where(
            (timetable_table.c.is_revised == True) & 
            (timetable_table.c.branch == target_branch)
        )
    )]

    target_day = origin_day
    target_slot = origin_slot

    is_lab = "LAB" in (subject_id or "").upper()
    req_count = 2 if is_lab else 1

    shared = await is_subject_shared(subject_id)
    branches_to_process = ["BCA", "BCADA"] if shared else [target_branch]

    if new_status == "Delayed":
        try:
            start_search_idx = time_slots.index(origin_slot) + 1
        except ValueError:
            start_search_idx = 0
            
        # Skip lunch
        if start_search_idx < len(time_slots) and time_slots[start_search_idx] == "12:50-1:50":
            start_search_idx += 1

        if start_search_idx < len(time_slots):
            target_slot = time_slots[start_search_idx]
        else:
            new_status = "Rescheduled"

    if new_status == "Rescheduled":
        # Search every day starting from next day until we find a spot or end up back at origin
        days_cycle = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        try:
            current_day_idx = days_cycle.index(normalize_day(origin_day))
        except ValueError:
            current_day_idx = 0
            
        found = False
        for i in range(1, 7): # Try next 6 days
            check_day_idx = (current_day_idx + i) % len(days_cycle)
            candidate_day = normalize_day(days_cycle[check_day_idx])
            
            candidate_slot = find_smart_slot_for_day(
                revised_records,
                candidate_day,
                ignore_subject=subject_id,
                required_slots=req_count
            )
            if candidate_slot:
                target_day = candidate_day
                target_slot = candidate_slot
                found = True
                break
        
        if not found:
            fallback_slot = find_smart_slot_for_day(
                revised_records,
                origin_day,
                ignore_subject=subject_id,
                required_slots=req_count,
                min_index=0
            )
            if fallback_slot:
                target_slot = fallback_slot
            else:
                await reset_subject_revised_position(subject_id)
                return

    # Recursively moves classes when a slot becomes occupied
    async def displace_and_place(subj_to_place, day, slot, branch_list, depth=0):
        if depth > 10: return # Prevent infinite recursion
        
        try:
            idx = time_slots.index(slot)
        except ValueError:
            return

        # Identify occupants at destination
        occ_to_displace = set()
        for i in range(req_count if "LAB" in subj_to_place.upper() else 1):
            curr_idx = idx + i
            if curr_idx >= len(time_slots): continue
            
            for b in branch_list:
                row = await db.fetch_one(timetable_table.select().where(
                    (timetable_table.c.is_revised == True) &
                    (timetable_table.c.day == day) &
                    (timetable_table.c.time_slot == time_slots[curr_idx]) &
                    (timetable_table.c.branch == b)
                ))
                if row and row["subject"] and row["subject"].strip() != "" and row["subject"] != "LUNCH":
                    if row["subject"].lower() != subj_to_place.lower():
                        occ_to_displace.add((row["subject"], b))

        # Place the subject
        for i in range(req_count if "LAB" in subj_to_place.upper() else 1):
            curr_idx = idx + i
            if curr_idx < len(time_slots):
                for b in branch_list:
                    await db.execute(timetable_table.update().where(
                        (timetable_table.c.is_revised == True) &
                        (timetable_table.c.day == day) &
                        (timetable_table.c.time_slot == time_slots[curr_idx]) &
                        (timetable_table.c.branch == b)
                    ).values(subject=subj_to_place))

        # Update schedule record
        for b in branch_list:
            final_status = "Rescheduled" if depth > 0 else new_status
            await db.execute(schedule_table.update().where(
                (func.lower(schedule_table.c.subject) == subj_to_place.lower()) &
                (schedule_table.c.branch == b)
            ).values(new_time=f"{day} {slot}", status=final_status, is_active=True))
            
            # Autogenerate an alert if this subject was bumped automatically
            if depth > 0:
                await add_notification(
                    title=f"{subj_to_place} Shifted",
                    message=f"{subj_to_place} shifted to {day} at {slot}.",
                    n_type="schedule_change",
                    teacher_message=f"{subj_to_place} clashed with a schedule change and was displaced to {day} at {slot}.",
                    branch=b
                )

        # Displace others
        for occ, occ_branch in occ_to_displace:
            next_idx = idx + (req_count if "LAB" in subj_to_place.upper() else 1)
            if next_idx < len(time_slots) and time_slots[next_idx] == "12:50-1:50":
                next_idx += 1
            
            if next_idx >= len(time_slots) or (day == "Saturday" and next_idx >= 4):
                # Move to next day
                next_day = choose_reschedule_day(day)
                await displace_and_place(occ, next_day, time_slots[0], [occ_branch], depth + 1)
            else:
                await displace_and_place(occ, day, time_slots[next_idx], [occ_branch], depth + 1)

    # Clear original position if moving within same day or to another day
    for b in branches_to_process:
        await clear_subject_from_revised_grid(subject_id, branch=b, day=origin_day)
    
    # Perform the displacement and placement
    await displace_and_place(subject_id, target_day, target_slot, branches_to_process)

# Retrieves all currently active schedule adjustments for a branch
async def get_all_schedules(branch: Optional[str] = "BCA") -> List[dict]:
    query = schedule_table.select().where(
        (schedule_table.c.is_active == True) & 
        (schedule_table.c.branch == branch)
    ).order_by(schedule_table.c.class_id.asc())
    records = await db.fetch_all(query)
    return [dict(r) for r in records]

# Fetches recent alerts and coordination requests for the user
async def get_notifs(branch: str = "BCA") -> List[dict]:
    query = notifications_table.select().where(notifications_table.c.branch == branch).order_by(notifications_table.c.id.desc())
    records = await db.fetch_all(query)
    
    results = []
    for r in records:
        d = dict(r)
        
        if d["type"] == "merge_request":
            mr_query = merge_requests_table.select().where(merge_requests_table.c.notification_id == d["id"])
            mr_record = await db.fetch_one(mr_query)
            if mr_record:
                d["merge_request_id"] = mr_record["id"]
                d["mr_status"] = mr_record["status"]
        if "test period" in (d.get("teacher_message") or "").lower():
            active_schedules = await db.fetch_all(schedule_table.select().where(schedule_table.c.is_active == True))
            for s in active_schedules:
                if get_subject_family(s["subject"]) in d["teacher_message"].upper():
                    rem = await calculate_remaining_weeks(s["test_period_start"], s["test_weeks_total"])
                    d["teacher_message"] = re.sub(
                        r"(remaining\s+)?test\s+period\s+(\(\d+\s+weeks\)?|\d+\s+weeks?)", 
                        f"remaining test period {rem}", 
                        d["teacher_message"], 
                        flags=re.IGNORECASE
                    )
        results.append(d)
    return results

# Sends a system or coordination message to the dashboard
async def add_notification(title: str, message: str, n_type: str, teacher_message: Optional[str] = None, branch: str = "BCA"):
    query = notifications_table.insert().values(
        title=title,
        message=message,
        teacher_message=teacher_message,
        type=n_type,
        read=False,
        created_at=datetime.now().isoformat(),
        branch=branch
    )
    return await db.execute(query)

# Works out how much time is left in a scheduling trial
async def calculate_remaining_weeks(start_date_val: Optional[any], total_weeks: int = 2) -> str:
    if not start_date_val:
        return f"{total_weeks} weeks"
    try:
        if isinstance(start_date_val, str):
            try:
                start_date = datetime.fromisoformat(start_date_val)
            except ValueError:
                return f"{total_weeks} weeks"
        elif isinstance(start_date_val, datetime):
            start_date = start_date_val
        else:
            return f"{total_weeks} weeks"
            
        delta = datetime.now() - start_date
        weeks_passed = delta.days // 7
        remaining = total_weeks - weeks_passed
        if remaining <= 0:
            return "0 weeks (Complete)"
        return f"{remaining} week" if remaining == 1 else f"{remaining} weeks"
    except Exception:
        return f"{total_weeks} weeks"

# Changes the status and timing of a class in the records
async def update_schedule(subjectprefix: str, new_status: str, totalstudents: Optional[int] = None, target_day: Optional[str] = None, present_count: Optional[int] = None):
    valid_subjects_map = {
        "AI": "Artificial Intelligence",
        "IoT": "Internet of Things",
        "MA": "Mobile Applications",
        "PBI": "Power BI",
        "SE": "Software Engineering",
        "Project LAB": "Project Lab",
        "MA LAB": "Mobile Applications Lab",
        "Internship": "Internship",
        "Library": "Library",
        "CC": "Cloud Computing",
        "DL": "Deep Learning"
    }
    reverse_map = {v.lower(): k for k, v in valid_subjects_map.items()}
    if subjectprefix.lower() in reverse_map:
        subjectprefix = reverse_map[subjectprefix.lower()]

    normalized_day = normalize_day(target_day) if target_day else None
    
    resolved_subject = None
    check_exact_query = schedule_table.select().where(
        func.lower(schedule_table.c.subject) == subjectprefix.lower()
    )
    existing = await db.fetch_one(check_exact_query)
    if existing:
        resolved_subject = subjectprefix
        
    if not resolved_subject:
        resolved_subject = get_subject_family(subjectprefix)
        check_exact_query2 = schedule_table.select().where(
            func.lower(schedule_table.c.subject) == resolved_subject.lower()
        )
        existing2 = await db.fetch_one(check_exact_query2)
        if not existing2:
            resolved_subject = None

    if not resolved_subject:
        raise ValueError(
            "No schedule entry found for subject '" + subjectprefix + "' on day '" + (target_day or "None") + "'."
        )

    update_values = {"status": new_status, "is_active": True}
    
    if new_status in ["Delayed", "Rescheduled", "Merged"]:
        update_values["test_period_start"] = datetime.now().isoformat()
        update_values["test_weeks_total"] = 2
    
    if totalstudents is not None:
        update_values["total_students"] = totalstudents
    
    if present_count is not None:
        update_values["present_count"] = present_count
    
    if normalized_day:
        update_values["original_time"] = normalized_day
        
    query = schedule_table.update().where(
        func.lower(schedule_table.c.subject) == resolved_subject.lower()
    ).values(**update_values)
    
    await db.execute(query)
    await apply_subject_change_to_revised_grid(resolved_subject, new_status, normalized_day)

    changed_statuses = {"Delayed", "Rescheduled", "Merged", "Cancelled"}
    if normalized_day and new_status in changed_statuses:
        resolved_family = get_subject_family(resolved_subject)
        active_rows = await db.fetch_all(
            schedule_table.select().where(schedule_table.c.is_active == True)
        )

        for row in active_rows:
            row_dict = dict(row)
            row_subject = row_dict.get("subject") or ""
            if row_subject.lower() == resolved_subject.lower():
                continue
            if get_subject_family(row_subject) != resolved_family:
                continue

            if row_dict.get("status") == "On Schedule" and row_dict.get("original_time") is None:
                continue

            await db.execute(
                schedule_table.update().where(
                    schedule_table.c.id == row_dict["id"]
                ).values(status="On Schedule", original_time=None)
            )
            await reset_subject_revised_position(row_subject)

    return resolved_subject

# Reverts all changes for a specific subject back to normal
async def reset_subject_schedule(subject_name: str):
    family = get_subject_family(subject_name)
    
    all_alerts = await db.fetch_all(schedule_table.select())
    for alert in all_alerts:
        a_dict = dict(alert)
        if get_subject_family(a_dict["subject"]) == family:
            await db.execute(
                schedule_table.update().where(
                    schedule_table.c.id == a_dict["id"]
                ).values(status="On Schedule", is_active=False, original_time=None, test_period_start=None)
            )
            await reset_subject_revised_position(a_dict["subject"])

# Commits temporary schedule changes to the permanent grid
async def make_schedule_permanent(subject_name: str):
    revised_records = await db.fetch_all(timetable_table.select().where(
        (timetable_table.c.is_revised == True) & (timetable_table.c.subject == subject_name)
    ))
    
    await db.execute(timetable_table.update().where(
        (timetable_table.c.is_revised == False) & (timetable_table.c.subject == subject_name)
    ).values(subject=""))
    
    for r in revised_records:
        await db.execute(timetable_table.update().where(
            (timetable_table.c.is_revised == False) & 
            (timetable_table.c.day == r["day"]) & 
            (timetable_table.c.time_slot == r["time_slot"])
        ).values(subject=subject_name))

    family = get_subject_family(subject_name)
    all_alerts = await db.fetch_all(schedule_table.select())
    for alert in all_alerts:
        a_dict = dict(alert)
        if get_subject_family(a_dict["subject"]) == family:
            await db.execute(
                schedule_table.update().where(
                    schedule_table.c.id == a_dict["id"]
                ).values(status="On Schedule", is_active=False, original_time=None, new_time=None, test_period_start=None)
            )

# Deletes all alerts from the entire system database
async def clear_all_notifications():
    query = notifications_table.delete()
    await db.execute(query)

# Removes all coordination messages for a single branch
async def clear_notifications_by_branch(branch: str):
    query = notifications_table.delete().where(notifications_table.c.branch == branch)
    await db.execute(query)

# Marks a specific class session as cancelled
async def cancel_class(target_subject: str, target_day: str):
    normalized_day = normalize_day(target_day)
    check_query = schedule_table.select().where(
        (schedule_table.c.subject == target_subject) & 
        (schedule_table.c.original_time == normalized_day)
    )
    existing_record = await db.fetch_one(check_query)
    
    if existing_record:
        update_query = schedule_table.update().where(
            (schedule_table.c.subject == target_subject) & 
            (schedule_table.c.original_time == target_day)
        ).values(status="Cancelled")
        await db.execute(update_query)
    else:
        insert_query = schedule_table.insert().values(
            subject=target_subject,
            status="Cancelled",
            original_time=normalized_day, # Store the day here
            total_students=40 
        )
        await db.execute(insert_query)
    
    msg = f"{target_subject} has been cancelled."
    if "PBI" in target_subject.upper():
        msg = "PBI class rescheduled/cancelled."

    await add_notification(
        title="Class Cancelled",
        message=msg,
        n_type="cancellation",
        teacher_message=f"Class {target_subject} cancelled. Est period: 2 weeks."
    )

# Completely clears all adjustments and resets the timetable
async def reset_all_schedules():
    # 1. Reset all schedule markers
    await db.execute(schedule_table.update().values(status="On Schedule", is_active=False, original_time=None, new_time=None, test_period_start=None))
    
    # 2. Reset the timetable grid to match original state
    original_data = await db.fetch_all(timetable_table.select().where(timetable_table.c.is_revised == False))
    
    # Simple and fast: clear revised first
    await db.execute(timetable_table.update().where(timetable_table.c.is_revised == True).values(subject="", occupancy_count=0))
    
    # Then match from original
    for r in original_data:
        await db.execute(
            timetable_table.update().where(
                (timetable_table.c.is_revised == True) &
                (timetable_table.c.day == r["day"]) &
                (timetable_table.c.time_slot == r["time_slot"]) &
                (timetable_table.c.branch == r["branch"])
            ).values(subject=r["subject"], occupancy_count=r["occupancy_count"])
        )

# Reactiveates all modified schedules to the latest saved state
async def restore_all_schedules():
    query = schedule_table.update().values(is_active=True)
    await db.execute(query)

    await db.execute(timetable_table.delete().where(timetable_table.c.is_revised == True))
    
    entries = []
    def add_map(schedule_map, branch_name):
        for day, subjects in schedule_map.items():
            for index, subject in enumerate(subjects):
                entries.append({
                    "day": day, 
                    "time_slot": time_slots[index], 
                    "subject": subject, 
                    "is_revised": True,
                    "branch": branch_name
                })

    add_map(revised_schedule_map, "BCA")
    add_map(bcada_revised_map, "BCADA")
    
    await db.execute_many(timetable_table.insert(), entries)

# Provides a list of classes for the timetable view
async def get_timetable_data(is_revised: bool = False, branch: Optional[str] = "BCA") -> List[dict]:
    conditions = [timetable_table.c.is_revised == is_revised]
    if branch:
        conditions.append(timetable_table.c.branch == branch)
        
    query = timetable_table.select().where(and_(*conditions))
    records = await db.fetch_all(query)
    return [dict(r) for r in records]

# Sets up the database with the initial class information
async def _seed_timetable_grid():
    await db.execute(timetable_table.delete())
    
    entries_to_insert = []

    def add_map(schedule_map, is_revised_flag, branch_name):
        for day, subjects in schedule_map.items():
            for index, subject in enumerate(subjects):
                entries_to_insert.append({
                    "day": day, 
                    "time_slot": time_slots[index], 
                    "subject": subject, 
                    "is_revised": is_revised_flag,
                    "branch": branch_name
                })

    add_map(original_schedule_map, False, "BCA")
    add_map(revised_schedule_map, True, "BCA")
    
    add_map(bcada_original_map, False, "BCADA")
    add_map(bcada_revised_map, True, "BCADA")
            
    await db.execute_many(timetable_table.insert(), entries_to_insert)

# Creates auto-alerts for any detected schedule inconsistencies
async def _seed_schedule_alerts():
    # FIRST, restore the grid to the original state from maps
    await _seed_timetable_grid()

    current_schedule = { (r["subject"], r["branch"]): dict(r) for r in await db.fetch_all(schedule_table.select()) }
    
    await db.execute(schedule_table.delete())
    
    orig_records = await get_timetable_data(is_revised=False, branch=None)
    revised_records = await get_timetable_data(is_revised=True, branch=None)
    
    valid_subjects_map = {
        "AI": "Artificial Intelligence",
        "IoT": "Internet of Things",
        "MA": "Mobile Applications",
        "PBI": "Power BI",
        "SE": "Software Engineering",
        "Project LAB": "Project Lab",
        "MA LAB": "Mobile Applications Lab",
        "Internship": "Internship",
        "Library": "Library",
        "CC": "Cloud Computing",
        "DL": "Deep Learning"
    }
    subjects = set()
    for row in orig_records + revised_records:
        subject_str = row["subject"]
        if subject_str and subject_str != "LUNCH" and subject_str != "":
            subjects.add(subject_str)
    
    alerts_to_insert = []
    
    await db.execute(notifications_table.delete())
    
    def get_base_name(s):
        import re
        return re.sub(r'\d+$', '', s)

    for branch in ["BCA", "BCADA"]:
        branch_orig = [r for r in orig_records if r.get("branch") == branch]
        branch_revised = [r for r in revised_records if r.get("branch") == branch]
        
        branch_subjects = set()
        for row in branch_orig + branch_revised:
            subject_str = row["subject"]
            if subject_str and subject_str != "LUNCH" and subject_str != "":
                branch_subjects.add(subject_str)

        # Mapping subjects to their proper departements
        for subject in sorted(list(branch_subjects)):
            orig_positions = [
                f"{normalize_day(r['day'])} {r['time_slot']}" for r in branch_orig if r['subject'] == subject
            ]
            revised_positions = [
                f"{normalize_day(r['day'])} {r['time_slot']}" for r in branch_revised if r['subject'] == subject
            ]
            
            status = "On Schedule"
            base_name = get_base_name(subject)
            display_name = valid_subjects_map.get(base_name, base_name)
            prev_record = current_schedule.get((subject, branch))
            
            if not revised_positions and orig_positions:
                status = "Cancelled"
                msg = f"{display_name} ({branch}) class has been cancelled."
                await add_notification(
                    title=f"{display_name} Update",
                    message=msg,
                    n_type="alert",
                    teacher_message=msg,
                    branch=branch
                )
            elif sorted(orig_positions) != sorted(revised_positions):
                orig_days = set(p.split(' ')[0] for p in orig_positions)
                revised_days = set(p.split(' ')[0] for p in revised_positions)
                
                new_slot = revised_positions[0] if revised_positions else "Unknown"
                
                # Check for merged status
                merge_query = merge_requests_table.select().where(
                    (merge_requests_table.c.status == "approved") & 
                    (merge_requests_table.c.subject == subject) &
                    ((merge_requests_table.c.target_branch == branch) | (merge_requests_table.c.requestor_branch == branch))
                )
                merge_record = await db.fetch_one(merge_query)
                other_dept = None
                if merge_record:
                    other_dept = merge_record["target_branch"] if merge_record["requestor_branch"] == branch else merge_record["requestor_branch"]

                attendance_info = ""
                if prev_record and prev_record.get("total_students", 0) > 0:
                    p = prev_record.get("present_count", 0)
                    t = prev_record["total_students"]
                    if p > 0:
                        attendance_info = " Attendance at " + str(round((p/t)*100, 1)) + "%."
                
                if other_dept:
                    status = "Merged"
                    # Format strictly per user request: "{subjectname} merged with {classname} a {time,day}"
                    main_msg = f"{display_name} merged with {other_dept} a {new_slot}"
                    t_msg = main_msg + attendance_info + " (Test period: 2 weeks)."
                elif orig_days == revised_days:
                    status = "Delayed"
                    main_msg = display_name + " (" + branch + ") class is delayed. New timing: " + new_slot + "."
                    t_msg = main_msg + attendance_info + " Shifting 1 hour later in test period (2 weeks)."
                else:
                    status = "Rescheduled"
                    main_msg = display_name + " (" + branch + ") class has been rescheduled to " + new_slot + "."
                    t_msg = main_msg + attendance_info + " Rescheduled in test period (2 weeks)."
                
                await add_notification(
                    title=display_name + " Update",
                    message=main_msg,
                    n_type="schedule_change",
                    teacher_message=t_msg,
                    branch=branch
                )
                
            alerts_to_insert.append({
                "class_id": 100 + len(alerts_to_insert),
                "subject": subject, 
                "status": status,
                "is_active": (status != "On Schedule"),
                "branch": branch,
                "test_period_start": prev_record["test_period_start"] if (prev_record and status != "On Schedule") else None,
                "present_count": prev_record["present_count"] if prev_record else 0,
                "total_students": prev_record["total_students"] if prev_record else 40
            })
    
    await db.execute_many(schedule_table.insert(), alerts_to_insert)

# Updates the attendance numbers for a specific day and class
async def update_occupancy(subject: str, count: int, day: str):
    d = normalize_day(day)
    await db.execute(
        timetable_table.update().where(
            (timetable_table.c.is_revised == True) &
            (timetable_table.c.subject == subject) &
            (timetable_table.c.day == d)
        ).values(occupancy_count=count)
    )

# Checks if a teacher is already busy at a certain time
async def check_teacher_availability(branch: str, day: str, time_slot: str) -> Optional[str]:
    d = normalize_day(day)
    t = normalize_time_slot(time_slot)
    query = timetable_table.select().where(
        (timetable_table.c.is_revised == True) &
        (timetable_table.c.branch == branch) &
        (timetable_table.c.day == d) &
        (timetable_table.c.time_slot == t)
    )
    result = await db.fetch_one(query)
    if result and result["subject"] and result["subject"] != "LUNCH" and result["subject"] != "":
        return result["subject"]
    return None

# Finalizes a merge request based on teacher coordination
async def process_merge_response(notif_id: int, approved: bool):
    req = await db.fetch_one(merge_requests_table.select().where(merge_requests_table.c.notification_id == notif_id))
    if not req:
        return False, "Request not found"

    requestor_branch = req["requestor_branch"]
    target_branch = req["target_branch"]
    subject_id = req["subject"]

    if not approved:
        await db.execute(merge_requests_table.update().where(merge_requests_table.c.id == req["id"]).values(status="fallback_pending"))
        
        fallback_day = req["proposed_day"] if req["proposed_day"] else req["day"]
        fallback_slot = req["proposed_time_slot"] if req["proposed_time_slot"] else req["time_slot"]
        reject_msg = f"[TEST PERIOD] The proposed merge for {subject_id} on {fallback_day} at {fallback_slot} was declined by {target_branch}. Would you prefer to shift the class a hour later or remain on schedule?"
        await add_notification(
            title="Merge Declined - Action Required",
            message="",
            n_type="alert",
            teacher_message=reject_msg,
            branch=requestor_branch
        )
        await add_notification(
            title="Merge Declined",
            message="",
            n_type="info",
            teacher_message=f"You declined the merge request for {subject_id}.",
            branch=target_branch
        )
        return True, "Merge declined. Fallback decision routed to requestor."

    final_day = req["proposed_day"] if req["proposed_day"] else req["day"]
    final_slot = normalize_time_slot(req["proposed_time_slot"] if req["proposed_time_slot"] else req["time_slot"])

    await clear_subject_from_revised_grid(subject_id, branch=requestor_branch, day=req["day"], time_slot=req["time_slot"])

    await db.execute(
        timetable_table.update().where(
            (timetable_table.c.is_revised == True) &
            (timetable_table.c.day == final_day) &
            (timetable_table.c.time_slot == final_slot) &
            (timetable_table.c.branch.in_([requestor_branch, target_branch]))
        ).values(subject=subject_id)
    )

    await db.execute(
        schedule_table.update().where(schedule_table.c.subject == subject_id).values(
            status="Merged",
            new_time=f"{final_day} {final_slot}",
            is_active=True
        )
    )

    await db.execute(merge_requests_table.update().where(merge_requests_table.c.id == req["id"]).values(status="approved"))

    # Format strictly per user request: "{subjectname} merged with {classname} a {time,day}"
    student_msg_requestor = f"{subject_id} merged with {target_branch} a {final_slot}, {final_day}"
    student_msg_target = f"{subject_id} merged with {requestor_branch} a {final_slot}, {final_day}"
    
    await add_notification(
        title="Merge Finalized",
        message=student_msg_requestor,
        n_type="success",
        teacher_message=student_msg_requestor + " Attendance improved, shifting to test period (2 weeks).",
        branch=requestor_branch
    )
    
    await add_notification(
        title="Merge Finalized",
        message=student_msg_target,
        n_type="success",
        teacher_message=student_msg_target + " Shared merge finalized. Test period active.",
        branch=target_branch
    )

    return True, "Merge success"

# Opens the connection to the application database
async def init_db():
    engine = create_engine(DATABASE_CONN_URL)
    metadata.create_all(engine)
    await db.connect()

# Safely shuts down the connection to the database
async def close_db():
    await db.disconnect()
