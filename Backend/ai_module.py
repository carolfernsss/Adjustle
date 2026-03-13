# ai processing using yolo model
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

# loading environment variables
load_dotenv()

# Load configurations from environment variables
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8s.pt")
RESULTS_DIR = os.getenv("RESULTS_DIR", "backend_static/results")
ATTEND_LOW = int(os.getenv("ATTENDANCE_LOW", "30"))
ATTEND_MEDIUM = int(os.getenv("ATTENDANCE_MEDIUM", "40"))
ATTEND_HIGH = int(os.getenv("ATTENDANCE_HIGH", "60"))

# setting up the fastapi router
ai_router = APIRouter()

# loading the detection model
yolo_model = YOLO(YOLO_MODEL_PATH)

os.makedirs(RESULTS_DIR, exist_ok=True)


# structure for schedule update requests
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


# function to save approved schedule changes
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


# main function for image counting
@ai_router.post("/count")
async def analyze_classroom_image(
    imagefile: UploadFile = File(...),
    subjectname: str = "AI",
    totalstudents: int = 40,
    dayofweek: str = "Monday",
    branch: str = "BCA",
    timeslot: Optional[str] = None
):
    # Enforce student count limits (1 to 250)
    totalstudents = max(1, min(250, totalstudents))

    start_time = time.time()

    img_bytes = await imagefile.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    img_array = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Image could not be decoded")

    # ---------------------------------------------------------------
    # Reliable pure-numpy NMS (avoids cv2.dnn.NMSBoxes API differences)
    # ---------------------------------------------------------------
    def numpy_nms(boxes, confs, iou_threshold=0.25):
        """NMS on [x1,y1,x2,y2] boxes, returns kept indices."""
        if len(boxes) == 0:
            return []
        boxes = np.array(boxes, dtype=np.float32)
        confs = np.array(confs, dtype=np.float32)
        order = confs.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            if order.size == 1:
                break
            rest = order[1:]
            xx1 = np.maximum(boxes[i, 0], boxes[rest, 0])
            yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
            xx2 = np.minimum(boxes[i, 2], boxes[rest, 2])
            yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            area_i    = (boxes[i, 2]    - boxes[i, 0])    * (boxes[i, 3]    - boxes[i, 1])
            area_rest = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
            iou = inter / (area_i + area_rest - inter + 1e-6)
            order = rest[iou <= iou_threshold]
        return keep

    # ---------------------------------------------------------------
    # METHOD 1: YOLO tile-based detection
    # Sliding window so back-row people are seen at full resolution
    # ---------------------------------------------------------------
    try:
        h, w = img.shape[:2]
        TILE    = 640
        OVERLAP = 0.35
        stride  = int(TILE * (1 - OVERLAP))

        raw_yolo_boxes = []
        raw_yolo_confs = []

        # Full-image pass (broad context, catches large/mid-size people)
        res_full = yolo_model.predict(
            img, classes=[0], conf=0.001, imgsz=1280,
            iou=0.15, max_det=600, agnostic_nms=True, augment=True, verbose=False
        )
        for box in res_full[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            raw_yolo_boxes.append([x1, y1, x2, y2])
            raw_yolo_confs.append(float(box.conf[0]))

        # Tile pass (catches small back-row people at high resolution)
        for y0 in range(0, h, stride):
            for x0 in range(0, w, stride):
                tile = img[y0:min(y0+TILE, h), x0:min(x0+TILE, w)]
                if tile.shape[0] < 64 or tile.shape[1] < 64:
                    continue
                res_t = yolo_model.predict(
                    tile, classes=[0], conf=0.001, imgsz=640,
                    iou=0.15, max_det=200, agnostic_nms=True, verbose=False
                )
                for box in res_t[0].boxes:
                    bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                    raw_yolo_boxes.append([bx1+x0, by1+y0, bx2+x0, by2+y0])
                    raw_yolo_confs.append(float(box.conf[0]))

        # Merge with global NMS at IOU=0.2 (keeps overlapping real people)
        kept = numpy_nms(raw_yolo_boxes, raw_yolo_confs, iou_threshold=0.20)
        yolo_boxes = np.array(raw_yolo_boxes, dtype=np.float32)[kept] if kept else np.array([])
        yolo_confs = np.array(raw_yolo_confs, dtype=np.float32)[kept] if kept else np.array([])
        yolo_count = len(yolo_boxes)

    except Exception as e:
        print(f"YOLO Error: {str(e)}")
        yolo_boxes = np.array([])
        yolo_confs = np.array([])
        yolo_count = 0

    # ---------------------------------------------------------------
    # METHOD 2: Haar Cascade face detection
    # Built into OpenCV, specifically tuned for group/crowd photos.
    # Much better at catching dense rows of frontal faces than YOLO.
    # ---------------------------------------------------------------
    face_boxes  = []
    face_count  = 0
    try:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_eq = cv2.equalizeHist(gray)   # improves contrast for distant faces

        # minNeighbors=3/4 balances recall vs false positives on wall posters etc.
        f_a = face_cascade.detectMultiScale(gray_eq, scaleFactor=1.05, minNeighbors=3, minSize=(15, 15))
        f_b = face_cascade.detectMultiScale(gray,    scaleFactor=1.08, minNeighbors=4, minSize=(20, 20))

        all_face_rects = []
        if len(f_a) > 0:
            all_face_rects.extend(f_a.tolist())
        if len(f_b) > 0:
            all_face_rects.extend(f_b.tolist())

        # Convert [x,y,w,h] → [x1,y1,x2,y2] and NMS to remove duplicates
        face_xyxy  = [[fx, fy, fx+fw, fy+fh] for fx, fy, fw, fh in all_face_rects]
        face_c_arr = [0.6] * len(face_xyxy)
        fkept = numpy_nms(face_xyxy, face_c_arr, iou_threshold=0.30)
        face_boxes = [face_xyxy[i] for i in fkept]
        face_count = len(face_boxes)
    except Exception as e:
        print(f"Face cascade error: {str(e)}")
        face_count = 0

    # ---------------------------------------------------------------
    # Smart merge: YOLO as base + only cascade faces YOLO missed
    #
    # WHY: "take max" inflates count for small classes (Haar false-positives
    # on posters/backgrounds). Cross-referencing by face-centre avoids this.
    #
    # Small class (20 people): YOLO≈18, cascade≈20 faces, almost all face
    #   centres land inside a YOLO body box → extra_faces≈0 → total≈18-20 ✓
    # Dense group (57 people): YOLO≈21, cascade≈50 faces, ~30 face centres
    #   fall outside YOLO boxes (back rows YOLO missed) → total≈50 ✓
    # ---------------------------------------------------------------
    extra_face_boxes = []
    if face_boxes and len(yolo_boxes) > 0:
        for fb in face_boxes:
            fx1, fy1, fx2, fy2 = fb
            fcx = (fx1 + fx2) / 2   # face centre x
            fcy = (fy1 + fy2) / 2   # face centre y
            covered = False
            for yb in yolo_boxes:
                yx1, yy1, yx2, yy2 = yb.tolist()
                # Face centre inside (or near) the YOLO body box?
                if yx1 <= fcx <= yx2 and yy1 <= fcy <= yy2:
                    covered = True
                    break
            if not covered:
                extra_face_boxes.append(fb)
    elif face_boxes and len(yolo_boxes) == 0:
        # YOLO found nothing at all – trust cascade fully
        extra_face_boxes = face_boxes

    extra_count = len(extra_face_boxes)

    # Combine: YOLO bodies + uncovered cascade faces
    detected_count = yolo_count + extra_count

    # Merge box lists for visualisation
    if extra_face_boxes:
        extra_np = np.array(extra_face_boxes, dtype=np.float32)
        extra_c  = np.full(extra_count, 0.55, dtype=np.float32)
        final_boxes = np.concatenate([yolo_boxes, extra_np]) if len(yolo_boxes) > 0 else extra_np
        final_confs = np.concatenate([yolo_confs, extra_c])  if len(yolo_confs) > 0 else extra_c
    else:
        final_boxes = yolo_boxes
        final_confs = yolo_confs

    print(f"Final: {detected_count} (YOLO={yolo_count} + CascadeExtra={extra_count}, faces_total={face_count})")

    # Calculate attendance based on detected count (people)
    attendance = (detected_count / totalstudents) * 100 if totalstudents > 0 else 0

    # saving the count to database
    await update_occupancy(subjectname, detected_count, dayofweek)

    detections = []
    for i, box in enumerate(final_boxes):
        x1, y1, x2, y2 = box.tolist()
        conf = float(final_confs[i])
        detections.append({"text": "person", "confidence": round(conf, 2), "box": [int(x1), int(y1), int(x2), int(y2)]})
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

    # print("Evaluating attendance rules")

    # rules for attendance decisions
    P = detected_count
    T = totalstudents
    A = attendance
    
    status = "On Schedule"
    suggestion = None
    student_msg = ""
    teacher_msg_reason = ""

    # checking minimum headcount
    if P < 8:
        status = "Rescheduled"
        teacher_msg_reason = f"Attendance at {A:.1f}% (Too low)."
    elif P < 15:
        status = "Merged"
        teacher_msg_reason = f"Attendance at {A:.1f}%."
    else:
        # checking rules based on class size
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

    # checking for shared resources
    is_shared = await is_subject_shared(subjectname)
    
    # SYSTEM OVERRIDE: If any subject is shared between timetables (e.g. AI, IoT, Internship), 
    # we NEVER reschedule if Merge is possible. We force the coordination request.
    if is_shared and status in ["Rescheduled", "Delayed"]:
        status = "Merged"
        teacher_msg_reason = f"Institutional Shared Resource detected. {teacher_msg_reason}"
    
    # Final safety check: Cant merge a non-shared class
    if status == "Merged" and not is_shared:
        status = "Rescheduled"

    # creating notifications based on result
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
        "detection_breakdown": {
            "yolo_bodies": yolo_count,
            "cascade_faces_extra": extra_count,
            "cascade_faces_total": face_count
        },
        "timing": {
            "total_ms": total_time,
            "total_sec": total_time / 1000
        },
        "status": status,
        "attendance": attendance,
        "suggested_action": suggestion
    }
