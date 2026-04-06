from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import time
from database import db, update_schedule, add_notification, choose_reschedule_day, update_occupancy, merge_requests_table, is_subject_shared
from ultralytics import YOLO
import cv2
import numpy as np
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "Backend/yolov8n.pt")
RESULTS_DIR = os.getenv("RESULTS_DIR", "backend_static/results")
ATTEND_LOW = int(os.getenv("ATTENDANCE_LOW", "30"))
ATTEND_MEDIUM = int(os.getenv("ATTENDANCE_MEDIUM", "40"))
ATTEND_HIGH = int(os.getenv("ATTENDANCE_HIGH", "60"))

ai_router = APIRouter()

yolo_model = YOLO(YOLO_MODEL_PATH)

os.makedirs(RESULTS_DIR, exist_ok=True)

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

# Safely applies a schedule update once a teacher approves it
@ai_router.post("/approve_schedule_change")
async def commit_schedule_change(req: ScheduleChangeRequest):
    teacher_message = req.teacher_message or req.notification_teacher_message

    if req.status:
        if req.status != "Merged":
            try:
                from database import normalize_day
                norm_day = normalize_day(req.day) if req.day else None
                resolved_subject = await update_schedule(req.subject, req.status, 60, target_day=norm_day, present_count=req.present_count)
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err))
        else:
            from database import resolve_subject_instance
            resolved_subject = resolve_subject_instance(req.subject, req.day) or req.subject
    else:
        resolved_subject = req.subject

    # Intercept and dynamically enrich the AI's generic notification message using the final placement data!
    if req.status in ["Delayed", "Rescheduled"]:
        from database import schedule_table
        updated_row = await db.fetch_one(schedule_table.select().where(
            (schedule_table.c.subject == resolved_subject) &
            (schedule_table.c.branch == req.branch)
        ))
        if updated_row and updated_row["new_time"]:
            final_time = updated_row["new_time"]
            req.notification_message = f"{resolved_subject} was shifted to {final_time}."
            if req.notification_teacher_message:
                teacher_message = req.notification_teacher_message + f" Final placement: {final_time}."

    if req.notification_title is not None and req.notification_message is not None:
        await add_notification(
            title=req.notification_title,
            message=req.notification_message,
            n_type=req.notification_type or "info",
            teacher_message=teacher_message,
            branch=req.branch
        )
    elif req.status and req.status not in ["On Schedule", "Active"]:
        fallback_msg = f"{req.subject} shifted to new timing on {req.day} at {req.time_slot}." if req.time_slot else f"{req.subject} shifted to new timing on {req.day}."
        teacher_msg = f"{req.subject} class shifted to new timing on {req.day}. Est test period: 2 weeks."
        if req.notification_teacher_message:
            teacher_msg = req.notification_teacher_message
            
        await add_notification(
            title="Schedule Updated",
            message=fallback_msg,
            n_type="schedule_change",
            teacher_message=teacher_msg,
            branch=req.branch
        )

    if req.status == "Merged":
        other_branch = "BCADA" if req.branch == "BCA" else "BCA"
        
        conflict_subject = None
        if req.time_slot:
            from database import check_teacher_availability
            conflict_subject = await check_teacher_availability(other_branch, req.day, req.time_slot)
        
        time_info = f"{req.time_slot}, {req.day}" if req.time_slot else req.day
        merge_msg = f"{req.requestor_name} wants to merge {req.subject} at {time_info}?"
        
        if conflict_subject:
            merge_msg = f"[URGENT] {req.requestor_name} wants to merge {req.subject} at {time_info}. WARNING: You already have {conflict_subject} scheduled then. PLEASE DECLINE THIS REQUEST."
            
        notif_id = await add_notification(
            title="Merge Request",
            message=merge_msg,
            n_type="merge_request",
            teacher_message=merge_msg,
            branch=other_branch
        )

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

    return {"success": True, "message": "Changes approved.", "updated_subject": resolved_subject}

# Uses AI to detect students in an image and suggest changes
@ai_router.post("/count")
async def analyze_classroom_image(
    imagefile: UploadFile = File(...),
    subjectname: str = "AI",
    totalstudents: int = 40,
    dayofweek: str = "Monday",
    branch: str = "BCA",
    timeslot: Optional[str] = None
):
    totalstudents = max(1, min(250, totalstudents))

    from database import normalize_day
    dayofweek = normalize_day(dayofweek)
    start_time = time.time()
    
    try:
        img_bytes = await imagefile.read()
        if not img_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        img_array = np.frombuffer(img_bytes, np.uint8)
        img_raw = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img_raw is None:
            raise HTTPException(status_code=400, detail="Image could not be decoded")
        
        h_orig, w_orig = img_raw.shape[:2]
        MAX_DIM = 1200
        if max(h_orig, w_orig) > MAX_DIM:
            scale = MAX_DIM / max(h_orig, w_orig)
            img = cv2.resize(img_raw, (int(w_orig * scale), int(h_orig * scale)), interpolation=cv2.INTER_AREA)
        else:
            img = img_raw
            
        h, w = img.shape[:2]

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

        try:
            h, w = img.shape[:2]
            TILE    = 600
            OVERLAP = 0.05  # Dropped overlap strictly for speed
            stride  = int(TILE * (1 - OVERLAP))

            raw_yolo_boxes = []
            raw_yolo_confs = []

            t0 = time.time()
            res_full = yolo_model.predict(
                img, classes=[0], conf=0.01, imgsz=640,
                iou=0.25, max_det=600, agnostic_nms=True, augment=False, verbose=False
            )
            # print(f"Full-pass took {(time.time()-t0)*1000:.0f}ms")
            for box in res_full[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                raw_yolo_boxes.append([x1, y1, x2, y2])
                raw_yolo_confs.append(float(box.conf[0]))

            for y0 in range(0, h, stride):
                if time.time() - start_time > 22:
                    print("ANALYSIS WARNING: Nearing timeout, skipping remaining tiles")
                    break
                    
                for x0 in range(0, w, stride):
                    if y0 > (h * 0.7): continue
                    
                    tile = img[y0:min(y0+TILE, h), x0:min(x0+TILE, w)]
                    if tile.shape[0] < 200 or tile.shape[1] < 200:
                        continue
                    res_t = yolo_model.predict(
                        tile, classes=[0], conf=0.05, imgsz=640,
                        iou=0.25, max_det=200, agnostic_nms=True, verbose=False
                    )
                    for box in res_t[0].boxes:
                        bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                        raw_yolo_boxes.append([bx1+x0, by1+y0, bx2+x0, by2+y0])
                        raw_yolo_confs.append(float(box.conf[0]))

            p0 = time.time()
            kept = numpy_nms(raw_yolo_boxes, raw_yolo_confs, iou_threshold=0.20)
            # print(f"Tiling & NMS took {(p0-t0)*1000:.0f}ms (Total {len(raw_yolo_boxes)} raw boxes down to {len(kept)})")
            yolo_boxes = np.array(raw_yolo_boxes, dtype=np.float32)[kept] if kept else np.array([])
            yolo_confs = np.array(raw_yolo_confs, dtype=np.float32)[kept] if kept else np.array([])
            yolo_count = len(yolo_boxes)

        except Exception as e:
            print(f"YOLO Error: {str(e)}")
            yolo_boxes = np.array([])
            yolo_confs = np.array([])
            yolo_count = 0

        face_boxes  = []
        face_count  = 0
        try:
            hf0 = time.time()
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            f_a = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=4, minSize=(30, 30))
            
            all_face_rects = []
            if len(f_a) > 0:
                all_face_rects.extend(f_a.tolist())

            # print(f"Face cascade took {(time.time()-hf0)*1000:.0f}ms")

            face_xyxy  = [[fx, fy, fx+fw, fy+fh] for fx, fy, fw, fh in all_face_rects]
            face_c_arr = [0.6] * len(face_xyxy)
            fkept = numpy_nms(face_xyxy, face_c_arr, iou_threshold=0.30)
            face_boxes = [face_xyxy[i] for i in fkept]
            face_count = len(face_boxes)
        except Exception as e:
            print(f"Face cascade error: {str(e)}")
            face_count = 0

        extra_face_boxes = []
        if face_boxes and len(yolo_boxes) > 0:
            for fb in face_boxes:
                fx1, fy1, fx2, fy2 = fb
                fcx = (fx1 + fx2) / 2   # face centre x
                fcy = (fy1 + fy2) / 2   # face centre y
                covered = False
                for yb in yolo_boxes:
                    yx1, yy1, yx2, yy2 = yb.tolist()
                    if yx1 <= fcx <= yx2 and yy1 <= fcy <= yy2:
                        covered = True
                        break
                if not covered:
                    extra_face_boxes.append(fb)
        elif face_boxes and len(yolo_boxes) == 0:
            extra_face_boxes = face_boxes

        extra_count = len(extra_face_boxes)

        detected_count = yolo_count + extra_count

        if extra_face_boxes:
            extra_np = np.array(extra_face_boxes, dtype=np.float32)
            extra_c  = np.full(extra_count, 0.55, dtype=np.float32)
            final_boxes = np.concatenate([yolo_boxes, extra_np]) if len(yolo_boxes) > 0 else extra_np
            final_confs = np.concatenate([yolo_confs, extra_c])  if len(yolo_confs) > 0 else extra_c
        else:
            final_boxes = yolo_boxes
            final_confs = yolo_confs

        # print(f"Final: {detected_count} (YOLO={yolo_count} + CascadeExtra={extra_count}, faces_total={face_count})")

        attendance = (detected_count / totalstudents) * 100 if totalstudents > 0 else 0

        await update_occupancy(subjectname, detected_count, dayofweek)

        detections = []
        for i, box in enumerate(final_boxes):
            x1, y1, x2, y2 = box.tolist()
            conf = float(final_confs[i])
            detections.append({"text": "person", "confidence": round(conf, 2), "box": [int(x1), int(y1), int(x2), int(y2)]})
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        P = detected_count
        T = totalstudents
        A = attendance
        
        status = "On Schedule"
        suggestion = None
        student_msg = ""
        teacher_msg_reason = ""

        if A >= 60:
            status = "On Schedule"
        elif A >= 40:
            status = "Delayed"
            teacher_msg_reason = f"Attendance at {A:.1f}%."
        else:
            status = "Rescheduled"
            teacher_msg_reason = f"Attendance at {A:.1f}% (Low - below 40%)."

        is_shared = await is_subject_shared(subjectname)
        
        if is_shared and A < 60:
            status = "Merged"
            teacher_msg_reason = f"Shared resource ({subjectname}) detected with low attendance ({A:.1f}%). Requesting merge."
        
        if status == "Merged" and not is_shared:
            if A >= 40:
                status = "Delayed"
            else:
                status = "Rescheduled"

        if status == "On Schedule":
            suggestion = None
        elif status == "Delayed":
            student_msg = f"{subjectname} (normally at {timeslot}) shifted to 1 hour later."
            suggestion = {
                "update_db": True,
                "db_status": "Delayed",
                "notification": {
                    "title": "Class Delayed",
                    "message": student_msg,
                    "teacher_message": f"[TEST PERIOD] {teacher_msg_reason} Shifting from {timeslot} to 1 hour later.",
                    "type": "schedule_change"
                }
            }
        elif status == "Merged":
            target_branch = "BCADA" if branch == "BCA" else "BCA"
            suggestion = {
                "update_db": True,
                "db_status": "Merged",
                "notification": {
                    "title": "Merge Requested",
                    "message": "", # EMPTY for students
                    "teacher_message": f"[MERGE REQUEST] {teacher_msg_reason} Requesting merge of {subjectname} ({timeslot}) with {target_branch}.",
                    "type": "merge_request"
                }
            }
        elif status == "Rescheduled":
            target_day = choose_reschedule_day(dayofweek)
            student_msg = f"{subjectname} ({dayofweek} at {timeslot}) shifted to {target_day}."
            suggestion = {
                "update_db": True,
                "db_status": "Rescheduled",
                "notification": {
                    "title": "Class Shifted",
                    "message": student_msg,
                    "teacher_message": f"[TEST PERIOD] {teacher_msg_reason} Shifting {subjectname} from {dayofweek} {timeslot} to {target_day}.",
                    "type": "schedule_change"
                }
            }

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

    except Exception as e:
        print(f"ANALYSIS CRASH: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Analysis Error: {str(e)}")
