/* ---- Image Processing Component ---- */
import React, { useState, useRef, useEffect } from "react";
import {
    Upload,
    CheckCircle,
    XCircle,
    AlertCircle,
    Loader2,
    X,
    ScanLine,
    User,
    Calendar,
    BookOpen,
    Users
} from "lucide-react";
import "../css/UploadImage.css";
import "../css/Notification.css";

const BACKEND_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

const UploadImage = function (props) {
    const onNavigate = props.onNavigate;
    const onScheduleChange = props.onScheduleChange;
    const branch = props.branch || sessionStorage.getItem("adjustle_branch") || "BCA";
    const username = props.username || sessionStorage.getItem("adjustle_username") || "Teacher";

    const [image, setImage] = useState(null);
    const [previewUrl, setPreviewUrl] = useState("");

    /* ---- Main state for inputs and analysis results ---- */
    const [totalStudents, setTotalStudents] = useState(70);
    const [subject, setSubject] = useState("");
    const [selectedDate, setSelectedDate] = useState(new Date().getDate());
    const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth());
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
    const [timeSlot, setTimeSlot] = useState("");

    // Calendar view state
    const [viewMonth, setViewMonth] = useState(new Date().getMonth());
    const [viewYear, setViewYear] = useState(new Date().getFullYear());

    const [day, setDay] = useState(function () {
        return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][new Date().getDay()];
    });

    /* ---- Application States ---- */
    const [loading, setLoading] = useState(false);
    const [approving, setApproving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    /* ---- Results Data ---- */
    const [resultData, setResultData] = useState(null);
    const [resultImageUrl, setResultImageUrl] = useState("");
    const [suggestedAction, setSuggestedAction] = useState(null);

    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);

    const scheduleData = {
        "BCA": {
            "Power BI": { "Tuesday": ["09:00 AM"], "Wednesday": ["11:00 AM", "02:00 PM"], "Friday": ["09:00 AM"] },
            "Mobile Applications": { "Monday": ["10:00 AM"], "Wednesday": ["10:00 AM"], "Friday": ["10:00 AM"] },
            "Mobile Applications Lab": { "Wednesday": ["02:00 PM", "04:00 PM"] },
            "Software Engineering": { "Monday": ["01:00 PM"], "Tuesday": ["11:00 AM"], "Friday": ["11:00 AM"] },
            "Internet of Things": { "Monday": ["11:05 AM"], "Tuesday": ["01:50 PM"], "Wednesday": ["01:50 PM"] },
            "Artificial Intelligence": { "Friday": ["01:00 PM"] }
        },
        "BCADA": {
            "Internet of Things": { "Monday": ["09:00 AM"], "Tuesday": ["01:00 PM"], "Thursday": ["11:00 AM"] },
            "Artificial Intelligence": { "Tuesday": ["09:00 AM", "03:00 PM"], "Thursday": ["09:00 AM"], "Friday": ["01:00 PM"] },
            "Project Lab": { "Saturday": ["09:00 AM", "11:00 AM", "02:00 PM"] }
        }
    };

    const branchSchedule = scheduleData[branch] || scheduleData["BCA"];
    const subjects = Object.keys(branchSchedule);

    useEffect(() => {
        if (!subject || !subjects.includes(subject)) {
            setSubject(subjects[0]);
        }
    }, [branch, subjects, subject]);

    /* --- HANDLERS --- */

    const handleMonthChange = (offset) => {
        const newDate = new Date(viewYear, viewMonth + offset, 1);
        setViewMonth(newDate.getMonth());
        setViewYear(newDate.getFullYear());
    };

    const handleImageUpload = function (file) {
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            setError("Please select a valid image file");
            return;
        }
        setImage(file);
        setPreviewUrl(URL.createObjectURL(file));
        setResultData(null);
        setResultImageUrl("");
        setSuggestedAction(null);
        setError("");
        setSuccess("");
    };

    const resetForm = function () {
        setImage(null);
        setPreviewUrl("");
        setResultData(null);
        setResultImageUrl("");
        setSuggestedAction(null);
        setError("");
        setSuccess("");
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const processImage = async function () {
        if (!image) {
            setError("Please upload an image first.");
            return;
        }
        setLoading(true);
        setError("");
        setSuccess("");

        const formData = new FormData();
        formData.append("imagefile", image);
        const params = new URLSearchParams({
            subjectname: subject,
            totalstudents: totalStudents,
            dayofweek: day,
            timeslot: timeSlot
        });

        try {
            const response = await fetch(BACKEND_URL + "/count?" + params.toString(), {
                method: "POST",
                body: formData
            });
            if (!response.ok) throw new Error("Failed to analyze image");
            const data = await response.json();
            setResultData(data);
            setSuggestedAction(data.suggested_action);
            if (data.output_filename) {
                setResultImageUrl(BACKEND_URL + "/static/results/" + data.output_filename + "?t=" + Date.now());
            }
        } catch (err) {
            setError("Analysis failed. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const approveChange = async function () {
        if (!suggestedAction) return;
        setApproving(true);
        const payload = {
            subject,
            status: suggestedAction.db_status,
            day,
            time_slot: timeSlot,
            branch: branch,
            requestor_name: username // Correct field name for backend
        };
        if (suggestedAction.notification) {
            payload.notification_title = suggestedAction.notification.title;
            payload.notification_message = suggestedAction.notification.message;
            payload.teacher_message = suggestedAction.notification.teacher_message;
            payload.notification_type = suggestedAction.notification.type;
        }
        try {
            const response = await fetch(BACKEND_URL + "/approve_schedule_change", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error("Failed to update schedule.");
            const data = await response.json();
            if (data.success) {
                const isMerge = suggestedAction && suggestedAction.db_status === "Merged";
                setSuccess(isMerge ? "Merge request sent to Teacher!" : "Schedule updated and students notified!");
                if (onScheduleChange) onScheduleChange();
                setTimeout(() => onNavigate && onNavigate("timetable"), 1500);
            } else {
                setError(data.message || "Failed to update schedule.");
            }
        } catch (err) {
            setError(err.message || "Failed to update schedule.");
        } finally {
            setApproving(false);
        }
    };


    /* --- RENDERERS --- */
    const renderDropzone = () => (
        <div
            id="upload-dropzone"
            className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleImageUpload(e.dataTransfer.files[0]); }}
            onClick={() => fileInputRef.current && fileInputRef.current.click()}
        >
            <input ref={fileInputRef} type="file" accept="image/*" onChange={(e) => handleImageUpload(e.target.files[0])} style={{ display: 'none' }} />
            <div className="dropzone-content">
                <div className="dropzone-icon"><Upload size={32} /></div>
                <h3 className="dropzone-text"><strong>Click to upload</strong> or drag and drop</h3>
                <p className="dropzone-hint">Upload a classroom photo to count attendance</p>
            </div>
        </div>
    );

    const renderPreview = () => {
        const availableSlots = (branchSchedule[subject] && branchSchedule[subject][day]) || [];
        return (
            <div className="preview-card">
                <div className="preview-image-section">
                    <button className="remove-btn-absolute" onClick={resetForm}><X size={18} /></button>
                    <img src={previewUrl} alt="Preview" className="preview-image" />
                </div>
                <div className="preview-controls-section" id="detection-settings-panel">
                    <div className="preview-header"><h3>Detection Settings</h3></div>

                    {/* 1. Subject */}
                    <div className="input-group" id="input-subject">
                        <label className="input-label"><BookOpen size={14} /> Class (Subject)</label>
                        <select value={subject} onChange={(e) => {
                            const newSub = e.target.value;
                            setSubject(newSub);
                            const sch = branchSchedule[newSub] || {};
                            const pDays = Object.keys(sch);
                            if (pDays.length > 0 && !pDays.includes(day)) {
                                setDay(pDays[0]);
                                setTimeSlot((sch[pDays[0]] || [])[0] || "");
                            }
                        }} className="upload-select">
                            {subjects.map(s => <option key={s} className="upload-option">{s}</option>)}
                        </select>
                    </div>

                    {/* 2. Calendar */}
                    <div className="input-group" id="input-calendar">
                        <label className="input-label"><Calendar size={14} /> Class Schedule</label>
                        <div className="calendar-wrapper">
                            <div className="calendar-nav-header">
                                <button onClick={() => handleMonthChange(-1)} className="cal-nav-btn">&lt;</button>
                                <div className="calendar-title">{new Date(viewYear, viewMonth).toLocaleString('default', { month: 'long', year: 'numeric' })}</div>
                                <button onClick={() => handleMonthChange(1)} className="cal-nav-btn">&gt;</button>
                            </div>
                            <div className="calendar-grid">
                                {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(d => <div key={d} className="calendar-day-header">{d}</div>)}
                                {Array.from({ length: 42 }).map((_, i) => {
                                    const first = new Date(viewYear, viewMonth, 1).getDay();
                                    const dNum = i - first + 1;
                                    const maxD = new Date(viewYear, viewMonth + 1, 0).getDate();
                                    if (dNum <= 0 || dNum > maxD) return <div key={i} className="calendar-day-cell empty" />;
                                    const dObj = new Date(viewYear, viewMonth, dNum);
                                    const dName = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][dObj.getDay()];
                                    const isSch = !!(branchSchedule[subject] || {})[dName];
                                    const isSel = selectedDate === dNum && selectedMonth === viewMonth && selectedYear === viewYear;
                                    const isFut = dObj > new Date();
                                    return (
                                        <div key={i} className={`calendar-day-cell ${isSch ? 'active' : ''} ${isSel ? 'selected' : ''} ${isFut ? 'future' : ''}`}
                                            onClick={() => { if (!isFut && isSch) { setSelectedDate(dNum); setSelectedMonth(viewMonth); setSelectedYear(viewYear); setDay(dName); setTimeSlot(((branchSchedule[subject] || {})[dName] || [])[0] || ""); } }}>
                                            {dNum}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>


                    {/* 3. Time Slots */}
                    <div className="input-group" id="input-time-slot">
                        <label className="input-label">Pick Time Slot ({availableSlots.length} sessions)</label>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            {availableSlots.map(slot => (
                                <button key={slot} className={`time-slot-btn ${timeSlot === slot ? 'active' : ''}`} onClick={() => setTimeSlot(slot)}>{slot}</button>
                            ))}
                        </div>
                    </div>

                    {/* 4. Total Students */}
                    <div className="input-group" id="input-total-students">
                        <label className="input-label"><Users size={14} /> Students</label>
                        <input type="number" value={totalStudents} onChange={(e) => setTotalStudents(Number(e.target.value))} className="upload-input" />
                    </div>

                    <div className="action-row">
                        <button className="button-gold" id="count-action-btn" onClick={processImage} disabled={loading}>
                            {loading ? <Loader2 size={18} className="spin" /> : <ScanLine size={18} />} COUNT STUDENTS
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    const renderResults = () => {
        const isLab = subject && subject.toUpperCase().includes("LAB");

        let statusText = "Class will be on Schedule";
        let statusClass = "success";

        if (resultData.status === "Rescheduled") {
            statusText = isLab ? "Lab Rescheduling (2hr block)" : "Class will be Rescheduled";
            statusClass = "error";
        } else if (resultData.status === "Merged") {
            // Labs cannot be merged
            if (isLab) {
                statusText = "Lab Rescheduled (2hr block)";
            } else {
                statusText = "Class will be Merged";
            }
            statusClass = "error";
        } else if (resultData.status === "Delayed") {
            statusText = "Class will be Delayed";
            statusClass = "error";
        }

        return (
            <div className="result-card">
                <div className="result-image-area">
                    <div className={`status-badge-overlay ${statusClass}`}>
                        {statusText}
                    </div>
                    <div className="result-image-wrapper">
                        <img src={resultImageUrl} alt="Result" className="result-img" onClick={() => window.open(resultImageUrl, "_blank")} />
                    </div>
                </div>
                <div className="result-details-area">
                    <div className="result-stat-box">
                        <div className="result-stat-number">{resultData.count}</div>
                        <div className="result-stat-label">People Detected</div>
                    </div>

                    <div className="detections-scrollable">
                        <div className="detections-list">
                            {resultData.detections.map((p, i) => (
                                <div key={i} className="detection-item">
                                    <span><User size={12} /> Person {i + 1}</span>
                                    <span>{(p.confidence * 100).toFixed(0)}%</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="action-row">
                        {suggestedAction && suggestedAction.update_db && (
                            <div style={{ display: 'flex', gap: '10px', width: '100%' }}>
                                <button className="button-success" onClick={approveChange} disabled={approving} style={{ flex: 1 }}>
                                    {approving ? <Loader2 className="spin" /> : <CheckCircle size={18} />} Approve
                                </button>
                                <button className="button-error" onClick={resetForm} style={{ flex: 1 }}>
                                    <XCircle size={18} /> Deny
                                </button>
                            </div>
                        )}
                        <button className="button-gold" onClick={resetForm}>
                            <ScanLine size={18} /> NEW SCAN
                        </button>
                        <button className="button-dark" onClick={() => onNavigate && onNavigate("timetable")}>
                            RETURN TO TIMETABLE
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <>

            {error && <div className="message-box error"><AlertCircle size={18} /><span>{error}</span></div>}
            {success && <div className="message-box success"><CheckCircle size={18} /><span>{success}</span></div>}
            {resultData ? renderResults() : (image ? renderPreview() : renderDropzone())}
            {loading && <div className="loading-overlay"><Loader2 size={50} className="spin" /><p>Analyzing...</p></div>}
        </>
    );
};

export default UploadImage;
