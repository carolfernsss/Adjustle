import React, { useCallback, useState, useEffect } from "react";
import "../css/ClassAlerts.css";

// Defines a static mapping for translating abbreviated subject identifiers into comprehensive academic nomenclature
const SUBJECT_MAPPING = {
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
};

import { API_BASE } from "../api_config";

// React component providing a consolidated view of instructional scheduling adjustments and status alerts
const ClassAlerts = function (props) {
    const { selectedDay, role, onScheduleChange, branch, refreshTrigger } = props;
    const [alerts, setAlerts] = useState([]);
    const [confirmSubject, setConfirmSubject] = useState(null);
    const [showPermanentModal, setShowPermanentModal] = useState(false);
    const [showRevertModal, setShowRevertModal] = useState(false);

    // Implements an asynchronous data retrieval pattern to synchronize local state with remote scheduling records
    const fetchAlerts = useCallback(function () {
        const branchParam = branch || "BCA";
        const alertUrl = `${API_BASE}/reschedule?branch=${branchParam}`;
        const timetableUrl = `${API_BASE}/timetable?revised=false&branch=${branchParam}`;

        Promise.all([
            fetch(alertUrl).then(res => res.json()),
            fetch(timetableUrl).then(res => res.json())
        ])
            .then(([alertData, timetableData]) => {
                // 1. Process active alerts first
                let fetchedClasses = [];
                if (alertData.classes) {
                    fetchedClasses = alertData.classes.filter(c => c.is_active !== false);
                }

                // 2. Identify all possible subjects for this course from the timetable grid
                const courseSubjects = new Set();
                if (timetableData.schedule) {
                    timetableData.schedule.forEach(day => {
                        day.times.forEach(slot => {
                            if (slot.name && slot.name !== "LUNCH" && slot.name !== "") {
                                courseSubjects.add(slot.name);
                            }
                        });
                    });
                }

                // Deduplicate subjects - prioritizing active alerts
                const uniqueMap = {};

                // Initialize with all course subjects as "ON SCHEDULE"
                courseSubjects.forEach(function (subj) {
                    const cleanName = subj.replace(/\d+$/, '');
                    const fullName = SUBJECT_MAPPING[cleanName] || cleanName;
                    uniqueMap[fullName] = {
                        subject: fullName,
                        status: "ON SCHEDULE",
                        cssClass: "alert-green",
                        priority: 1
                    };
                });

                // Overlay active modifications (rescheduled, cancelled, etc.)
                fetchedClasses.forEach(function (cls) {
                    const cleanName = cls.subject.replace(/\d+$/, '');
                    const fullName = SUBJECT_MAPPING[cleanName] || cleanName;

                    let statusLabel = cls.status.toUpperCase();
                    let cssClass = "alert-red";
                    let priority = 0;

                    if (cls.status === "On Schedule") {
                        statusLabel = "ON SCHEDULE";
                        cssClass = "alert-green";
                        priority = 1;
                    } else if (cls.status === "Rescheduled" || cls.status === "Delayed" || cls.status === "Merged") {
                        statusLabel = "RESCHEDULED";
                        cssClass = "alert-red";
                        priority = 3;
                    } else if (cls.status === "Cancelled") {
                        statusLabel = "CANCELLED";
                        cssClass = "alert-red";
                        priority = 4;
                    }

                    if (!uniqueMap[fullName] || priority > uniqueMap[fullName].priority) {
                        uniqueMap[fullName] = {
                            subject: fullName,
                            status: statusLabel,
                            cssClass: cssClass,
                            priority: priority
                        };
                    }
                });

                setAlerts(Object.values(uniqueMap).sort((a, b) => {
                    return b.priority - a.priority; // Show urgent alerts at top
                }));
            })
            .catch(function (err) {
                console.error("Error fetching class data:", err);
            });
    }, [branch]);

    // Establishes a periodic synchronization interval to maintain live schedule awareness
    useEffect(function () {
        fetchAlerts();

        const pollInterval = setInterval(() => {
            fetchAlerts();
        }, 30000);

        return () => {
            clearInterval(pollInterval);
        };
    }, [fetchAlerts, refreshTrigger]);

    // Logic to resolve and display the specific instructional schedule for a selected calendar date
    if (selectedDay) {
        const dayMap = {
            "MON": "MONDAY", "TUE": "TUESDAY", "WED": "WEDNESDAY",
            "THU": "THURSDAY", "FRI": "FRIDAY", "SAT": "SATURDAY"
        };
        const selectedDayUpper = selectedDay.day.toUpperCase();
        let displayDay = selectedDayUpper;
        if (dayMap[selectedDayUpper]) {
            displayDay = dayMap[selectedDayUpper];
        }

        let classListContent = null;
        if (selectedDay.classes.length > 0) {
            classListContent = selectedDay.classes.map(function (cls, index) {
                let statusClass = "alert-red";
                let statusText = cls.status ? cls.status.toUpperCase() : "RESCHEDULED";

                if (cls.status === "On Schedule") {
                    statusClass = "alert-green";
                    statusText = "ON SCHEDULE";
                } else if (cls.status === "Rescheduled" || cls.status === "Delayed") {
                    statusClass = "alert-red";
                    statusText = "RESCHEDULED";
                } else if (cls.status === "Merged") {
                    statusClass = "alert-red";
                    statusText = "MERGED";
                }

                const cleanName = cls.subject.replace(/\d+$/, '');
                const fullName = SUBJECT_MAPPING[cleanName] || cleanName;

                return (
                    <div
                        key={index}
                        className="alert-item"
                        onClick={() => {
                            if (role && role.toLowerCase() === 'teacher' && cls.status !== "On Schedule") {
                                setConfirmSubject(cls.subject);
                                setShowPermanentModal(true);
                            }
                        }}
                        style={{ cursor: (role && role.toLowerCase() === 'teacher' && cls.status !== "On Schedule") ? 'pointer' : 'default' }}
                    >
                        <span className="alert-subject">{fullName}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className={`alert-status ${statusClass}`}>{statusText}</span>
                            {role && role.toLowerCase() === "teacher" && cls.status !== "On Schedule" && (
                                <button
                                    className="revert-btn"
                                    style={{
                                        fontSize: '10px',
                                        padding: '2px 6px',
                                        color: '#ef4444',
                                        backgroundColor: '#ef44441a',
                                        border: '1px solid #ef44444d',
                                        borderRadius: '4px',
                                        cursor: 'pointer'
                                    }}
                                    onClick={function (e) {
                                        e.stopPropagation();
                                        setConfirmSubject(cls.subject);
                                        setShowRevertModal(true);
                                    }}
                                >
                                    Revert
                                </button>
                            )}
                        </div>
                    </div>
                );
            });
        } else {
            classListContent = <div className="class-alert-empty">No classes for this day</div>;
        }

        return (
            <div className="dashboard-section animate-up">
                <h3 className="class-alerts-title">{"SCHEDULE FOR " + displayDay}</h3>
                <div className="class-alerts-list">
                    {classListContent}
                </div>

                {showPermanentModal && (
                    <div className="modal-overlay" style={{
                        position: 'fixed',
                        top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: '#000000d9',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 2000
                    }}>
                        <div className="modal-content" style={{
                            backgroundColor: '#19140e',
                            padding: '30px',
                            borderRadius: '12px',
                            border: '1px solid #d9bc9433',
                            maxWidth: '400px',
                            textAlign: 'center'
                        }}>
                            <h3 style={{ color: '#d9bc94', marginBottom: '15px' }}>Testing Period Over?</h3>
                            <p style={{ color: '#e8d4b8', marginBottom: '25px', lineHeight: '1.5' }}>
                                Would you like to make the new schedule for <strong>{confirmSubject}</strong> permanent?
                            </p>

                            <div style={{ display: 'flex', justifyContent: 'center', gap: '15px' }}>
                                <button
                                    className="button primary"
                                    onClick={() => {
                                        fetch(`${API_BASE}/make_permanent`, {
                                            method: "POST",
                                            headers: { "Content-Type": "application/json" },
                                            body: JSON.stringify({ subject: confirmSubject })
                                        })
                                            .then(() => {
                                                if (onScheduleChange) onScheduleChange();
                                                setShowPermanentModal(false);
                                            });
                                    }}
                                    style={{
                                        padding: '8px 24px',
                                        backgroundColor: '#d9bc94',
                                        color: '#19140e',
                                        border: 'none',
                                        borderRadius: '4px',
                                        fontWeight: 'bold',
                                        cursor: 'pointer'
                                    }}
                                >
                                    YES
                                </button>
                                <button
                                    className="button secondary"
                                    onClick={() => setShowPermanentModal(false)}
                                    style={{
                                        padding: '8px 24px',
                                        backgroundColor: 'transparent',
                                        color: '#d9bc94',
                                        border: '1px solid #d9bc94',
                                        borderRadius: '4px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    NO
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {showRevertModal && (
                    <div className="modal-overlay" style={{
                        position: 'fixed',
                        top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: '#000000d9',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 2000
                    }}>
                        <div className="modal-content" style={{
                            backgroundColor: '#19140e',
                            padding: '30px',
                            borderRadius: '12px',
                            border: '1px solid #d9bc9433',
                            maxWidth: '400px',
                            textAlign: 'center'
                        }}>
                            <h3 style={{ color: '#d9bc94', marginBottom: '15px' }}>Confirm Revert</h3>
                            <p style={{ color: '#e8d4b8', marginBottom: '25px', lineHeight: '1.5' }}>
                                Are you sure you want to revert the changes for <strong>{confirmSubject}</strong>?
                            </p>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: '15px' }}>
                                <button
                                    className="button primary"
                                    onClick={() => {
                                        fetch(`${API_BASE}/reset_subject`, {
                                            method: "POST",
                                            headers: { "Content-Type": "application/json" },
                                            body: JSON.stringify({ subject: confirmSubject })
                                        })
                                            .then(() => {
                                                if (onScheduleChange) onScheduleChange();
                                                setShowRevertModal(false);
                                            });
                                    }}
                                    style={{
                                        padding: '8px 24px',
                                        backgroundColor: '#ef4444',
                                        color: '#ffffff',
                                        border: 'none',
                                        borderRadius: '4px',
                                        fontWeight: 'bold',
                                        cursor: 'pointer'
                                    }}
                                >
                                    YES, REVERT
                                </button>
                                <button
                                    className="button secondary"
                                    onClick={() => setShowRevertModal(false)}
                                    style={{
                                        padding: '8px 24px',
                                        backgroundColor: 'transparent',
                                        color: '#d9bc94',
                                        border: '1px solid #d9bc94',
                                        borderRadius: '4px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    CANCEL
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // Returns the primary interface for non-day-specific class status notifications
    return (
        <div className="dashboard-section animate-up" id="class-alerts-sidebar" style={{ minHeight: '300px' }}>
            <h3 className="class-alerts-title">ALL CLASSES</h3>
            <div className="class-alerts-list">
                {alerts.map(function (alert, index) {
                    return (
                        <div
                            key={index}
                            className="alert-item"
                            onClick={() => {
                                if (role && role.toLowerCase() === 'teacher' && alert.status !== "ON SCHEDULE") {
                                    setConfirmSubject(alert.subject);
                                    setShowPermanentModal(true);
                                }
                            }}
                            style={{ cursor: (role && role.toLowerCase() === 'teacher' && alert.status !== "ON SCHEDULE") ? 'pointer' : 'default' }}
                        >
                            <span className="alert-subject">{alert.subject}</span>
                            <span className={"alert-status " + alert.cssClass}>
                                {alert.status}
                            </span>
                        </div>
                    );
                })}
            </div>
            {
                showPermanentModal && (
                    <div className="modal-overlay" style={{
                        position: 'fixed',
                        top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: '#000000d9',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 2000
                    }}>
                        <div className="modal-content" style={{
                            backgroundColor: '#19140e',
                            padding: '30px',
                            borderRadius: '12px',
                            border: '1px solid #d9bc9433',
                            maxWidth: '400px',
                            textAlign: 'center'
                        }}>
                            <h3 style={{ color: '#d9bc94', marginBottom: '15px' }}>Testing Period Over?</h3>
                            <p style={{ color: '#e8d4b8', marginBottom: '25px', lineHeight: '1.5' }}>
                                Would you like to make the new schedule for <strong>{confirmSubject}</strong> permanent?
                            </p>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: '15px' }}>
                                <button
                                    className="button primary"
                                    onClick={() => {
                                        fetch(`${API_BASE}/make_permanent`, {
                                            method: "POST",
                                            headers: { "Content-Type": "application/json" },
                                            body: JSON.stringify({ subject: confirmSubject })
                                        })
                                            .then(() => {
                                                if (onScheduleChange) onScheduleChange();
                                                setShowPermanentModal(false);
                                            });
                                    }}
                                    style={{
                                        padding: '8px 24px',
                                        backgroundColor: '#d9bc94',
                                        color: '#19140e',
                                        border: 'none',
                                        borderRadius: '4px',
                                        fontWeight: 'bold',
                                        cursor: 'pointer'
                                    }}
                                >
                                    YES
                                </button>
                                <button
                                    className="button secondary"
                                    onClick={() => setShowPermanentModal(false)}
                                    style={{
                                        padding: '8px 24px',
                                        backgroundColor: 'transparent',
                                        color: '#d9bc94',
                                        border: '1px solid #d9bc94',
                                        borderRadius: '4px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    NO
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
};

export default ClassAlerts;
