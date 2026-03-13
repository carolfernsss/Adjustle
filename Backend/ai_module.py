# AI Module for person detection using YOLO
from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import time
from Backend.database import db, update_schedule, add_notification, choose_reschedule_day, update_occupancy, merge_requests_table, is_subject_shared
from ultralytics import YOLO
import cv2
import numpy as np
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# // Load environment properties for model path and detection directories
load_dotenv()

# Load configurations from environment variables
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
RESULTS_DIR = os.getenv("RESULTS_DIR", "backend_static/results")
ATTEND_LOW = int(os.getenv("ATTENDANCE_LOW", "30"))
ATTEND_MEDIUM = int(os.getenv("ATTENDANCE_MEDIUM", "40"))
ATTEND_HIGH = int(os.getenv("ATTENDANCE_HIGH", "60"))

# // Initialize the FastAPI router for processing AI related requests
ai_router = APIRouter()

# // Load the YOLOv8 model for computer vision based person detection
yolo_model = YOLO(YOLO_MODEL_PATH)

os.makedirs(RESULTS_DIR, exist_ok=True)


# // Data model for receiving and validating schedule change requests from the UI
class ScheduleChangeRequest(BaseModel):
    subject: str
    status: str
    day: Optional[str] = "Monday"
    notification_title: Optional[str] = None
    notification_message: Optional[str] = None
    teacher_message: Optional[str] = None
    notification_teacher_message: Optional[str] = None
    notification_type: Optional[str] = None
    branch: Optional[str] = "BCA"
    requestor_name: Optional[str] = "Teacher"
    time_slot: Optional[str] = None
    present_count: Optional[int] = 0


# // Endpoint targeted when a teacher manually approves an AI suggested schedule change
@ai_router.post("/approve_schedule_change")
async def commit_schedule_change(req: ScheduleChangeRequest):
    # Commit the proposed schedule changes from AI module
    teacher_message = req.teacher_message or req.notification_teacher_message

    if req.status:
        # CRITICAL: Don't show 'Merged' to students until BOTH teachers approve.
        # So we skip update_schedule here if status is Merged.
        if req.status != "Merged":
            try:
                resolved_subject = await update_schedule(req.subject, req.status, 60, target_day=req.day, present_count=req.present_count)
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err))
        else:
            # Just resolve the name for the request record
            from database import resolve_subject_instance
            resolved_subject = resolve_subject_instance(req.subject, req.day) or req.subject
    else:
        resolved_subject = req.subject

    if req.notification_title and req.notification_message:
        await add_notification(
            title=req.notification_title,
            message=req.notification_message,
            n_type=req.notification_type or "info",
            teacher_message=teacher_message
        )
    elif req.status and req.status not in ["On Schedule", "Active"]:
        # Standard notification logic for non-merge updates
        teacher_msg = req.subject + " class shifted to new timing. Est test period: 2 weeks."
        if req.notification_teacher_message:
            teacher_msg = req.notification_teacher_message
            
        await add_notification(
            title="Schedule Updated",
            message=req.subject + " shifted to new timing.",
            n_type="schedule_change",
            teacher_message=teacher_msg,
            branch=req.branch
        )

    # Special logic for Merge Requests (Teacher to Teacher)
    if req.status == "Merged":
        other_branch = "BCADA" if req.branch == "BCA" else "BCA"
        
        # Check if the other teacher is already busy
        conflict_subject = None
        if req.time_slot:
            from database import check_teacher_availability
            conflict_subject = await check_teacher_availability(other_branch, req.day, req.time_slot)
        
        time_info = f"{req.time_slot}, {req.day}" if req.time_slot else req.day
        merge_msg = f"{req.requestor_name} wants to merge {req.subject} at {time_info}?"
        
        if conflict_subject:
            merge_msg = f"{req.requestor_name} wants to merge {req.subject} at {time_info}? Note: You have {conflict_subject} then."
            
        notif_id = await add_notification(
            title="Merge Request",
            message=merge_msg,
            n_type="merge_request",
            teacher_message=merge_msg,
            branch=other_branch
        )

        # Store merge request details
        await db.execute(
            merge_requests_table.insert().values(
                subject=resolved_subject,
                day=req.day,
                time_slot=req.time_slot,
                requestor_branch=req.branch,
                target_branch=other_branch,
                status="pending",
                notification_id=notif_id,
                requester_consent=True,
                requestor_username=req.requestor_name
            )
        )

        return {"success": True, "message": "Merge request sent to the other department.", "updated_subject": req.subject}

    # print(f"Schedule update done for {req.subject} -> {resolved_subject} on {req.day}")
    return {"success": True, "message": "Changes approved.", "updated_subject": resolved_subject}


# // Main processing endpoint that accepts a classroom image and counts the students
@ai_router.post("/count")
async def analyze_classroom_image(
    imagefile: UploadFile = File(...),
    subjectname: str = "AI",
    totalstudents: int = 40,
    dayofweek: str = "Monday",
    branch: str = "BCA"
):
    # Enforce student count limits (1 to 150)
    totalstudents = max(1, min(150, totalstudents))

    start_time = time.time()

    img_bytes = await imagefile.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    img_array = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Image could not be decoded")

    # Pass 1: Detect Humans
    results = yolo_model(img, classes=[0], conf=0.15, imgsz=1280, iou=0.5, max_det=150, verbose=False)
    human_boxes = results[0].boxes
    detected_count = len(human_boxes)
    
    current_boxes = human_boxes
    names = results[0].names
    
    # Pass 2: Fallback if no humans detected (Detect anything)
    if detected_count == 0:
        results_all = yolo_model(img, classes=None, conf=0.15, imgsz=1280, iou=0.5, max_det=150, verbose=False)
        current_boxes = results_all[0].boxes
        names = results_all[0].names
    
    # Calculate attendance based on detected count (humans)
    attendance = (detected_count / totalstudents) * 100 if totalstudents > 0 else 0
    
    # // Updating the live occupancy status in the shared database grid
    await update_occupancy(subjectname, detected_count, dayofweek)

    detections = []
    for box in current_boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = names[cls_id]
        
        detections.append({"text": label, "confidence": round(conf, 2), "box": [int(x1), int(y1), int(x2), int(y2)]})
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(img, f"{label} {conf:.2f}", (int(x1), int(y1) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # print("Evaluating attendance rules")

    # Antigravity Attendance Decision Rules
    P = detected_count
    T = totalstudents
    A = attendance
    
    status = "On Schedule"
    suggestion = None
    student_msg = ""
    teacher_msg_reason = ""

    # Step 1: Minimum Headcount Overrides
    if P < 8:
        status = "Rescheduled"
        teacher_msg_reason = f"Attendance at {A:.1f}% (Too low)."
    elif P < 15:
        status = "Merged"
        teacher_msg_reason = f"Attendance at {A:.1f}%."
    else:
        # Step 2: Apply Rules by Class Size
        if T <= 50:
            if A >= 75:
                status = "On Schedule"
            elif A >= 55:  # 55 <= A < 75
                status = "Delayed"
                teacher_msg_reason = f"Attendance at {A:.1f}%."
            elif A >= 35:  # 35 <= A < 55
                status = "Merged"
                teacher_msg_reason = f"Attendance at {A:.1f}%."
            else:  # A < 35
                status = "Rescheduled"
                teacher_msg_reason = f"Attendance at {A:.1f}% (Too low)."
        else:  # T >= 51
            if A >= 65:
                status = "On Schedule"
            elif A >= 45:  # 45 <= A < 65
                status = "Delayed"
                teacher_msg_reason = f"Attendance at {A:.1f}%."
            elif A >= 25:  # 25 <= A < 45
                status = "Merged"
                teacher_msg_reason = f"Attendance at {A:.1f}%."
            else:  # A < 25
                status = "Rescheduled"
                teacher_msg_reason = f"Attendance at {A:.1f}% (Too low)."

    # Step 3: Merge Restriction & Shared Subject Check
    is_shared = await is_subject_shared(subjectname)

    if status == "Merged" and not is_shared:
        status = "Rescheduled"

    # // Constructing the appropriate notification or action based on the decision
    if status == "On Schedule":
        suggestion = None
    elif status == "Delayed":
        student_msg = subjectname + " shifted to 1 hour later."
        suggestion = {
            "update_db": True,
            "db_status": "Delayed",
            "notification": {
                "title": "Class Delayed",
                "message": student_msg,
                "teacher_message": teacher_msg_reason + " Shifting 1 hour later in test period.",
                "type": "schedule_change"
            }
        }
    elif status == "Merged":
        target_branch = "BCADA" if branch == "BCA" else "BCA"
        # MERGE IMPORTANT: Students dont get this notification yet.
        suggestion = {
            "update_db": True,
            "db_status": "Merged",
            "notification": {
                "title": "Merge Requested",
                "message": "", # EMPTY for students
                "teacher_message": teacher_msg_reason + " Requesting merge with " + target_branch + ".",
                "type": "merge_request"
            }
        }
    elif status == "Rescheduled":
        target_day = choose_reschedule_day(dayofweek)
        student_msg = subjectname + " (" + dayofweek + ") shifted to " + target_day + "."
        suggestion = {
            "update_db": True,
            "db_status": "Rescheduled",
            "notification": {
                "title": "Class Shifted",
                "message": student_msg,
                "teacher_message": teacher_msg_reason + " Shifting to " + target_day + " in test period.",
                "type": "schedule_change"
            }
        }

    # print(f"Final decision: {status}")

    filename = f"result_{int(time.time() * 1000)}.jpg"
    cv2.imwrite(os.path.join(RESULTS_DIR, filename), img)

    total_time = (time.time() - start_time) * 1000

    return {
        "count": detected_count,
        "output_filename": filename,
        "detections": detections,
        "timing": {
            "total_ms": total_time,
            "total_sec": total_time / 1000
        },
        "status": status,
        "attendance": attendance,
        "suggested_action": suggestion
    }
