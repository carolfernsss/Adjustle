# // Import the required libraries for database and system operations
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

# Load environment variables (like the database URL)
load_dotenv()

DATABASE_CONN_URL = os.getenv("DATABASE_URL")

if not DATABASE_CONN_URL:
    raise ValueError(
        "CRITICAL ERROR: DATABASE_URL environment variable is MISSING. "
        "Please configure your PostgreSQL connection in the .env file."
    )

# // Initialize the database connection using the provided configuration URL
db = Database(DATABASE_CONN_URL)
metadata = MetaData()

# Table definitions for the system

# // Define the table structure for storing user account information
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

# Pydantic models for data validation

class UserProfile(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str = "student"

# // Class model for representing a single schedule record in our system
class ScheduleRecord(BaseModel):
    classid: int
    subject: str
    status: str
    originaltime: Optional[str] = None
    newtime: Optional[str] = None
    reason: Optional[str] = None

# User related database functions

time_slots = ["9:15-10:05", "10:10-11:00", "11:05-11:55", "12:00-12:50", "12:50-1:50", "1:50-2:40", "2:45-3:35", "3:40-4:30"]

# BCA Schedule Maps
original_schedule_map = {
    "Monday": ["AI", "", "IoT", "MA", "LUNCH", "Internship", "", "SE"],
    "Tuesday": ["", "SE", "", "AI", "LUNCH", "IoT", "PBI", ""],
    "Wednesday": ["MA", "MA LAB", "MA LAB", "", "LUNCH", "IoT", "", ""],
    "Thursday": ["", "SE", "", "AI", "LUNCH", "Library", "", "MA"],
    "Friday": ["PBI", "", "IoT", "SE", "LUNCH", "AI", "", ""],
    "Saturday": ["", "", "", "Project LAB", "LUNCH", ""]
}

revised_schedule_map = {
    "Monday": ["AI", "", "IoT", "MA", "LUNCH", "Internship", "", "SE"],
    "Tuesday": ["", "SE", "", "AI", "LUNCH", "IoT", "PBI", ""],
    "Wednesday": ["MA", "MA LAB", "MA LAB", "", "LUNCH", "IoT", "", ""],
    "Thursday": ["", "SE", "", "AI", "LUNCH", "Library", "", "MA"],
    "Friday": ["PBI", "", "IoT", "SE", "LUNCH", "AI", "", ""],
    "Saturday": ["", "", "", "Project LAB", "LUNCH", ""]
}

# BCADA Schedule Maps (Semester 6)
bcada_original_map = {
    "Monday": ["AI", "", "IoT", "CC", "LUNCH", "Internship", "DL", ""],
    "Tuesday": ["CC", "", "", "AI", "LUNCH", "IoT", "DL", ""],
    "Wednesday": ["", "IoT", "", "DL", "LUNCH", "AI", "", "CC"],
    "Thursday": ["CC", "", "AI", "", "LUNCH", "DL", "IoT", ""],
    "Friday": ["", "DL", "AI", "", "LUNCH", "CC", "", "IoT"],
    "Saturday": ["", "", "", "Project LAB", "LUNCH", ""]
}

bcada_revised_map = {
    "Monday": ["AI", "", "IoT", "CC", "LUNCH", "Internship", "DL", ""],
    "Tuesday": ["CC", "", "", "AI", "LUNCH", "IoT", "DL", ""],
    "Wednesday": ["", "IoT", "", "DL", "LUNCH", "AI", "", "CC"],
    "Thursday": ["CC", "", "AI", "", "LUNCH", "DL", "IoT", ""],
    "Friday": ["", "DL", "AI", "", "LUNCH", "CC", "", "IoT"],
    "Saturday": ["", "", "", "Project LAB", "LUNCH", ""]
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


# // Helper function to clean the subject name and remove any unwanted characters or IDs
def normalize_subject_token(subject_text: str) -> str:
    if not subject_text:
        return ""
    token = subject_text.strip().replace("-", " ")
    token = re.sub(r"\d+$", "", token)
    token = re.sub(r"\s+", " ", token).strip().upper()
    return token


# // Function to find the group/category that a particular subject belongs to
def get_subject_family(subject_text: str) -> str:
    token = normalize_subject_token(subject_text)
    return subject_family_map.get(token, token)


# // Logic to match a raw subject input to its actual database instance based on the day
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

async def is_subject_shared(subject_name: str) -> bool:
    # Identify if a subject exists in both BCA and BCADA timetables
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

# // Asynchronous function to search for a specific user record in the users table
async def find_user(target_username: str) -> Optional[dict]:
    # Finds a user by their username (case-insensitive). 
    # print(f"DEBUG: Looking for user '{target_username}'...")
    query = users_table.select().where(func.lower(users_table.c.username) == target_username.lower())
    user_record = await db.fetch_one(query)
    
    if user_record:
        return dict(user_record)

    return None

# // Utility to convert long day names to shortened 3-letter strings for internal use
def normalize_day(day_name: str) -> str:
    # Converts full day names to long form (e.g., 'Mon' -> 'Monday')
    mapping = {
        "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
        "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday", "sunday": "Sunday",
        "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"
    }
    return mapping.get(day_name.lower(), day_name)


# // Simple logic to pick the next available teaching day after a specific day
def choose_reschedule_day(source_day: str) -> str:
    # Always picks the next chronological day (forward in time)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    s = (source_day or "Mon")[:3].title()
    if s not in days:
        return "Tue"
    
    idx = days.index(s)
    next_idx = (idx + 1) % len(days)
    return days[next_idx]


    return None


# // Algorithm to find the most optimal empty time slot in a day for classes
def find_smart_slot_for_day(records: List[dict], day: str, ignore_subject: Optional[str] = None, required_slots: int = 1) -> Optional[str]:
    # This finds the best slot to pack the schedule "one before another"
    taken_indices = []
    ignore_lower = (ignore_subject or "").lower()

    for row in records:
        if row.get("day") != day:
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

    if not taken_indices:
        # Default to 9:15 (index 2) as a standard start if day is empty
        return time_slots[2]

    candidates = []
    for idx in range(len(time_slots)):
        # Skip lunch and taken slots
        if time_slots[idx] == "12:50-1:50":
            continue
            
        all_available = True
        for offset in range(required_slots):
            check_idx = idx + offset
            if check_idx >= len(time_slots) or time_slots[check_idx] == "12:50-1:50" or check_idx in taken_indices:
                all_available = False
                break
        
        if not all_available:
            continue
        
        # Distance to existing cluster
        min_dist = min(abs(idx - t) for t in taken_indices)
        
        # Count adjacent slots to prefer filling gaps (adj_count 2 > adj_count 1)
        adj_count = 0
        for offset in range(required_slots):
            curr_idx = idx + offset
            if any(abs(curr_idx - t) == 1 for t in taken_indices):
                adj_count += 1
        
        # Penalize larger distances heavily to prefer packing
        # Subtract adjacency bonus (higher adj_count = better)
        score = min_dist * 10 - (adj_count * 15)
            
        candidates.append((idx, score))

    if not candidates:
        return None

    # Sort by improved score (packing + gap filling), then by index
    candidates.sort(key=lambda x: (x[1], x[0]))
    return time_slots[candidates[0][0]]


async def clear_subject_from_revised_grid(subject_id: str):
    await db.execute(
        timetable_table.update().where(
            (timetable_table.c.is_revised == True) &
            (func.lower(timetable_table.c.subject) == subject_id.lower())
        ).values(subject="")
    )


async def reset_subject_revised_position(subject_id: str):
    original_positions = await db.fetch_all(
        timetable_table.select().where(
            (timetable_table.c.is_revised == False) &
            (func.lower(timetable_table.c.subject) == subject_id.lower())
        )
    )

    await clear_subject_from_revised_grid(subject_id)

    for pos in original_positions:
        pos_dict = dict(pos)
        await db.execute(
            timetable_table.update().where(
                (timetable_table.c.is_revised == True) &
                (timetable_table.c.day == pos_dict["day"]) &
                (timetable_table.c.time_slot == pos_dict["time_slot"])
            ).values(subject=subject_id)
        )


async def apply_subject_change_to_revised_grid(subject_id: str, new_status: str, source_day: Optional[str] = None):
    normalized_source_day = normalize_day(source_day) if source_day else None

    if new_status in ["On Schedule", "Active", "Merged"]:
        await reset_subject_revised_position(subject_id)
        return

    if new_status == "Cancelled":
        await clear_subject_from_revised_grid(subject_id)
        return

    original_positions = await db.fetch_all(
        timetable_table.select().where(
            (timetable_table.c.is_revised == False) &
            (func.lower(timetable_table.c.subject) == subject_id.lower())
        )
    )
    target_branch = original_positions[0]["branch"]

    origin = None
    if normalized_source_day:
        origin = next((dict(p) for p in original_positions if dict(p).get("day") == normalized_source_day), None)
    if origin is None:
        origin = dict(original_positions[0])

    origin_day = origin["day"]
    origin_slot = origin["time_slot"]
    
    # Filter revised records by SAME branch for smart slot calculation
    revised_records = [dict(r) for r in await db.fetch_all(
        timetable_table.select().where(
            (timetable_table.c.is_revised == True) & 
            (timetable_table.c.branch == target_branch)
        )
    )]

    target_day = origin_day
    target_slot = origin_slot

    # Determine required slots (Labs need 2 hours/slots)
    is_lab = "LAB" in (subject_id or "").upper()
    req_count = 2 if is_lab else 1

    if new_status == "Delayed":
        delayed_slot = find_smart_slot_for_day(
            revised_records,
            origin_day,
            ignore_subject=subject_id,
            required_slots=req_count
        )
        if delayed_slot:
            target_slot = delayed_slot
    elif new_status == "Rescheduled":
        rescheduled_day = choose_reschedule_day(origin_day)
        # Use the 'Smart' slot finder to group classes together
        rescheduled_slot = find_smart_slot_for_day(
            revised_records,
            rescheduled_day,
            ignore_subject=subject_id,
            required_slots=req_count
        )

        if rescheduled_slot:
            target_day = rescheduled_day
            target_slot = rescheduled_slot
        else:
            # Fallback to same day clustering
            fallback_slot = find_smart_slot_for_day(
                revised_records,
                origin_day,
                ignore_subject=subject_id,
                required_slots=req_count
            )
            if fallback_slot:
                target_slot = fallback_slot
            else:
                await reset_subject_revised_position(subject_id)
                return

    await clear_subject_from_revised_grid(subject_id)
    
    # Occupy the required number of slots
    try:
        start_idx = time_slots.index(target_slot)
        for i in range(req_count):
            current_idx = start_idx + i
            if current_idx < len(time_slots):
                await db.execute(
                    timetable_table.update().where(
                        (timetable_table.c.is_revised == True) &
                        (timetable_table.c.day == target_day) &
                        (timetable_table.c.time_slot == time_slots[current_idx]) &
                        (timetable_table.c.branch == target_branch)
                    ).values(subject=subject_id)
                )
    except ValueError:
        pass

    # Update the schedule record with the new location
    await db.execute(
        schedule_table.update().where(
            (schedule_table.c.subject == subject_id) &
            (schedule_table.c.original_time == normalized_source_day)
        ).values(new_time=f"{target_day} {target_slot}")
    )

# --- SCHEDULING AND NOTIFICATIONS FUNCTIONS ---

async def get_all_schedules(branch: Optional[str] = "BCA") -> List[dict]:
    # Filter by branch if specified
    query = schedule_table.select().where(
        (schedule_table.c.is_active == True) & 
        (schedule_table.c.branch == branch)
    ).order_by(schedule_table.c.class_id.asc())
    records = await db.fetch_all(query)
    return [dict(r) for r in records]

async def get_notifs(branch: str = "BCA") -> List[dict]:
    query = notifications_table.select().where(notifications_table.c.branch == branch).order_by(notifications_table.c.id.desc())
    records = await db.fetch_all(query)
    
    results = []
    for r in records:
        d = dict(r)
        
        # If it's a merge request, attach the request ID so the UI can take action
        if d["type"] == "merge_request":
            mr_query = merge_requests_table.select().where(merge_requests_table.c.notification_id == d["id"])
            mr_record = await db.fetch_one(mr_query)
            if mr_record:
                d["merge_request_id"] = mr_record["id"]
                d["mr_status"] = mr_record["status"]
        # Dynamically inject remaining test period if it exists in the message
        # This is a bit of a hack but avoids storing transient data
        if "test period" in (d.get("teacher_message") or "").lower():
            # Find the subject family mentioned in the message
            # Look for active test periods in schedule_table
            active_schedules = await db.fetch_all(schedule_table.select().where(schedule_table.c.is_active == True))
            for s in active_schedules:
                if get_subject_family(s["subject"]) in d["teacher_message"].upper():
                    rem = await calculate_remaining_weeks(s["test_period_start"], s["test_weeks_total"])
                    # Replace whatever was there with the new remaining period
                    d["teacher_message"] = re.sub(
                        r"(remaining\s+)?test\s+period\s+(\(\d+\s+weeks\)?|\d+\s+weeks?)", 
                        f"remaining test period {rem}", 
                        d["teacher_message"], 
                        flags=re.IGNORECASE
                    )
        results.append(d)
    return results

async def add_notification(title: str, message: str, n_type: str, teacher_message: Optional[str] = None, branch: str = "BCA"):
    # Inserts a new notification into the database. 
    # title: notification title, message: body message for students, n_type: type of notification.
    # print(f"DEBUG: Adding new notification: {title}")
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

async def calculate_remaining_weeks(start_date_val: Optional[any], total_weeks: int = 2) -> str:
    if not start_date_val:
        return f"{total_weeks} weeks"
    try:
        if isinstance(start_date_val, str):
            # Try parsing ISO format first
            try:
                start_date = datetime.fromisoformat(start_date_val)
            except ValueError:
                # Fallback for other formats if any
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

async def update_schedule(subjectprefix: str, new_status: str, totalstudents: Optional[int] = None, target_day: Optional[str] = None, present_count: Optional[int] = None):
    # Updates exactly one schedule entry based on subject + day.
    normalized_day = normalize_day(target_day) if target_day else None
    resolved_subject = resolve_subject_instance(subjectprefix, target_day)

    if not resolved_subject:
        check_exact_query = schedule_table.select().where(
            func.lower(schedule_table.c.subject) == subjectprefix.lower()
        )
        existing = await db.fetch_one(check_exact_query)
        if existing:
            resolved_subject = subjectprefix

    if not resolved_subject:
        check_all = await db.fetch_all(schedule_table.select())
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

    # Enforce one active modified class per subject family.
    # If one instance is delayed/rescheduled/merged, every sibling instance
    # must return to On Schedule so changes don't spill to multiple days.
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

            # Skip rows that are already fully clean.
            if row_dict.get("status") == "On Schedule" and row_dict.get("original_time") is None:
                continue

            await db.execute(
                schedule_table.update().where(
                    schedule_table.c.id == row_dict["id"]
                ).values(status="On Schedule", original_time=None)
            )
            await reset_subject_revised_position(row_subject)

    return resolved_subject

async def reset_subject_schedule(subject_name: str):
    # This function reverts a specific subject family to its original state
    # print(f"DEBUG: Manually resetting schedule for subject: {subject_name}")
    family = get_subject_family(subject_name)
    
    # 1. Deactivate status alerts for this subject family
    # We find all records where the subject belongs to this family
    all_alerts = await db.fetch_all(schedule_table.select())
    for alert in all_alerts:
        a_dict = dict(alert)
        if get_subject_family(a_dict["subject"]) == family:
            await db.execute(
                schedule_table.update().where(
                    schedule_table.c.id == a_dict["id"]
                ).values(status="On Schedule", is_active=False, original_time=None, test_period_start=None)
            )
            # 2. Reset its position in the revised grid
            await reset_subject_revised_position(a_dict["subject"])

async def make_schedule_permanent(subject_name: str):
    # This function marks a subject change as the new 'normal' (permanent)
    # 1. Find the current position in the REVISED grid
    revised_records = await db.fetch_all(timetable_table.select().where(
        (timetable_table.c.is_revised == True) & (timetable_table.c.subject == subject_name)
    ))
    
    # 2. Clear this subject from the ORIGINAL grid
    await db.execute(timetable_table.update().where(
        (timetable_table.c.is_revised == False) & (timetable_table.c.subject == subject_name)
    ).values(subject=""))
    
    # 3. Update the ORIGINAL grid entries to match the REVISED spots
    # This makes original_pos == revised_pos for future comparisons
    for r in revised_records:
        await db.execute(timetable_table.update().where(
            (timetable_table.c.is_revised == False) & 
            (timetable_table.c.day == r["day"]) & 
            (timetable_table.c.time_slot == r["time_slot"])
        ).values(subject=subject_name))

    family = get_subject_family(subject_name)
    # Update all alerts in this family to be 'On Schedule' and inactive
    all_alerts = await db.fetch_all(schedule_table.select())
    for alert in all_alerts:
        a_dict = dict(alert)
        if get_subject_family(a_dict["subject"]) == family:
            await db.execute(
                schedule_table.update().where(
                    schedule_table.c.id == a_dict["id"]
                ).values(status="On Schedule", is_active=False, original_time=None, new_time=None, test_period_start=None)
            )

async def clear_all_notifications():
    # print("DEBUG: Clearing all notifications...")
    query = notifications_table.delete()
    await db.execute(query)

async def clear_notifications_by_branch(branch: str):
    # print(f"DEBUG: Clearing notifications for branch {branch}...")
    query = notifications_table.delete().where(notifications_table.c.branch == branch)
    await db.execute(query)

async def cancel_class(target_subject: str, target_day: str):
    # print(f"DEBUG: Cancelling class '{target_subject}' on {target_day}...")
    # 1. Check if a record already exists for this class AND day
    normalized_day = normalize_day(target_day)
    check_query = schedule_table.select().where(
        (schedule_table.c.subject == target_subject) & 
        (schedule_table.c.original_time == normalized_day)
    )
    existing_record = await db.fetch_one(check_query)
    
    # 2. Update or Insert
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
    
    # 3. Add Notification
    msg = f"{target_subject} has been cancelled."
    if "PBI" in target_subject.upper():
        msg = "PBI class rescheduled/cancelled."

    await add_notification(
        title="Class Cancelled",
        message=msg,
        n_type="cancellation",
        teacher_message=f"Class {target_subject} cancelled. Est period: 2 weeks."
    )

# --- Global Control Operations ---

async def reset_all_schedules():
    # 1. Hide all status alerts
    query = schedule_table.update().values(is_active=False)
    await db.execute(query)

    # 2. Overwrite revised grid with original data for all branches
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
    
    add_map(original_schedule_map, "BCA")
    add_map(bcada_original_map, "BCADA")
    
    await db.execute_many(timetable_table.insert(), entries)

async def restore_all_schedules():
    # 1. Restore status alerts
    query = schedule_table.update().values(is_active=True)
    await db.execute(query)

    # 2. Put back the actual physical movements in the revised grid for all branches
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

# --- Timetable Grid Operations ---

async def get_timetable_data(is_revised: bool = False, branch: Optional[str] = "BCA") -> List[dict]:
    # print(f"DEBUG: Fetching timetable data (revised={is_revised})...")
    conditions = [timetable_table.c.is_revised == is_revised]
    if branch:
        conditions.append(timetable_table.c.branch == branch)
        
    query = timetable_table.select().where(and_(*conditions))
    records = await db.fetch_all(query)
    return [dict(r) for r in records]

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
    # print("Timetable seeded successfully!")

async def _seed_schedule_alerts():
    # print("DEBUG: Fetching and calculating schedule status alerts from database...")
    # 1. Fetch current schedule state to preserve attendance and test period data
    current_schedule = { (r["subject"], r["branch"]): r for r in await db.fetch_all(schedule_table.select()) }
    
    # 2. Clear existing alerts
    await db.execute(schedule_table.delete())
    
    # 3. Fetch original and revised grid data from database (All Branches)
    orig_records = await get_timetable_data(is_revised=False, branch=None)
    revised_records = await get_timetable_data(is_revised=True, branch=None)
    
    # 3. Extract unique, valid subjects (Filtered and mapped as per user request)
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
    
    time_slots = ["7:00-7:50", "7:55-8:45", "9:15-10:05", "10:10-11:00", "11:05-11:55", "12:00-12:50", "12:50-1:50", "1:50-2:40", "2:45-3:35", "3:40-4:30"]

    alerts_to_insert = []
    
    # Clear old notifications to avoid cluttering on re-seed
    await db.execute(notifications_table.delete())
    
    # Helper to strip instance IDs for display/mapping
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

        # Pre-fetch approved merges for this branch to identify "Merged" status
        merge_query = merge_requests_table.select().where(
            (merge_requests_table.c.status == "approved") & 
            ((merge_requests_table.c.target_branch == branch) | (merge_requests_table.c.requestor_branch == branch))
        )
        approved_merges = await db.fetch_all(merge_query)
        merged_subjects = {}
        for m in approved_merges:
            other = m["target_branch"] if m["requestor_branch"] == branch else m["requestor_branch"]
            merged_subjects[m["subject"]] = other

        for subject in sorted(list(branch_subjects)):
            # Calculate status by checking positions in fetched records
            orig_positions = [
                f"{r['day']} {r['time_slot']}" for r in branch_orig if r['subject'] == subject
            ]
            revised_positions = [
                f"{r['day']} {r['time_slot']}" for r in branch_revised if r['subject'] == subject
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
                other_dept = merged_subjects.get(subject)
                
                # Fetch preserved data (Like attendance / headcount) from previous state
                attendance_info = ""
                if prev_record and prev_record.get("total_students", 0) > 0:
                    p = prev_record.get("present_count", 0)
                    t = prev_record["total_students"]
                    if p > 0:
                        attendance_info = " Attendance at " + str(round((p/t)*100, 1)) + "%."
                
                if other_dept:
                    status = "Merged"
                    # Specific message for students as per requested format
                    main_msg = display_name + " at " + new_slot + " is merged with " + other_dept + "."
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
                "is_active": True,
                "branch": branch,
                "test_period_start": prev_record["test_period_start"] if (prev_record and status != "On Schedule") else None,
                "present_count": prev_record["present_count"] if prev_record else 0,
                "total_students": prev_record["total_students"] if prev_record else 40
            })
    
    await db.execute_many(schedule_table.insert(), alerts_to_insert)
    # print(f"Success: {len(alerts_to_insert)} alerts calculated and notifications broadcasted.")

async def update_occupancy(subject: str, count: int, day: str):
    # This records how many people were detected in a class for live monitoring
    # Points to the REVISED grid where the class is currently active
    d = normalize_day(day)
    # print(f"DEBUG: Updating occupancy for {subject} on {d} to {count}")
    await db.execute(
        timetable_table.update().where(
            (timetable_table.c.is_revised == True) &
            (timetable_table.c.subject == subject) &
            (timetable_table.c.day == d)
        ).values(occupancy_count=count)
    )

async def check_teacher_availability(branch: str, day: str, time_slot: str) -> Optional[str]:
    # Checks if a teacher (branch) already has a class in a specific slot in the REVISED grid
    d = normalize_day(day)
    query = timetable_table.select().where(
        (timetable_table.c.is_revised == True) &
        (timetable_table.c.branch == branch) &
        (timetable_table.c.day == d) &
        (timetable_table.c.time_slot == time_slot)
    )
    result = await db.fetch_one(query)
    if result and result["subject"] and result["subject"] != "LUNCH" and result["subject"] != "":
        return result["subject"]
    return None

async def process_merge_response(notif_id: int, approved: bool):
    # Process the decision made by the recipient teacher
    # 1. Find the request
    req = await db.fetch_one(merge_requests_table.select().where(merge_requests_table.c.notification_id == notif_id))
    if not req:
        return False, "Request not found"

    requestor_branch = req["requestor_branch"]
    target_branch = req["target_branch"]
    subject_id = req["subject"]

    if not approved:
        # Mark as rejected
        await db.execute(merge_requests_table.update().where(merge_requests_table.c.id == req["id"]).values(status="rejected"))
        
        # Broadcast notifications to participating departments
        reject_msg = f"The proposed merge for {subject_id} (from {requestor_branch}) was declined."
        await add_notification(
            title="Merge Declined",
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
        return True, "Merge declined"

    # If approved:
    # 2. Update the grid for the requestor's subject
    # Use negotiated time if present, else original request time
    final_day = req["proposed_day"] if req["proposed_day"] else req["day"]
    final_slot = req["proposed_time_slot"] if req["proposed_time_slot"] else req["time_slot"]

    # Clear old position
    await clear_subject_from_revised_grid(subject_id)

    # Insert into new position in the requestor's department timetable
    await db.execute(
        timetable_table.update().where(
            (timetable_table.c.is_revised == True) &
            (timetable_table.c.day == final_day) &
            (timetable_table.c.time_slot == final_slot) &
            (timetable_table.c.branch == requestor_branch)
        ).values(subject=subject_id)
    )

    # 3. Update the schedule status record
    await db.execute(
        schedule_table.update().where(schedule_table.c.subject == subject_id).values(
            status="Merged",
            new_time=f"{final_day} {final_slot}",
            is_active=True
        )
    )

    # 4. Mark request as approved
    await db.execute(merge_requests_table.update().where(merge_requests_table.c.id == req["id"]).values(status="approved"))

    # 5. Notify EVERYONE Concerned (Both branches)
    # Use branch-specific messages for students as requested
    student_msg_requestor = f"{subject_id} merged with {target_branch} at {final_day} {final_slot}."
    student_msg_target = f"{subject_id} merged with {requestor_branch} at {final_day} {final_slot}."
    
    # Notify Requestor Branch (Students and Teacher)
    await add_notification(
        title="Merge Finalized",
        message=student_msg_requestor,
        n_type="success",
        teacher_message=student_msg_requestor + " Attendance improved, shifting to test period (2 weeks).",
        branch=requestor_branch
    )
    
    # Notify Target Branch (Students and Teacher)
    await add_notification(
        title="Merge Finalized",
        message=student_msg_target,
        n_type="success",
        teacher_message=student_msg_target + " Shared merge finalized. Test period active.",
        branch=target_branch
    )

    return True, "Merge success"

# --- Lifecycle Management ---

# // Function to initialize and open the connection to the postgres database
async def init_db():
    engine = create_engine(DATABASE_CONN_URL)
    metadata.create_all(engine)
    await db.connect()

async def close_db():
    # print("DEBUG: Closing database connection...")
    await db.disconnect()
