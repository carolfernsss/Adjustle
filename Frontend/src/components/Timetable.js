import { API_BASE } from "../api_config";
import React, { useState, useEffect } from "react";
import "../css/Timetable.css";

const normalizeDay = function (day) {
    if (!day) return "";
    const mapping = {
        "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
        "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday",
    };
    const lower = day.toLowerCase();
    return mapping[lower] || day;
};

const subjectLabelByCode = {
    "AI": "Artificial Intelligence",
    "IOT": "Internet of Things",
    "MA": "Mobile Applications",
    "PBI": "Power BI",
    "SE": "Software Engineering",
    "PROJECT LAB": "Project Lab",
    "MA LAB": "Mobile Applications Lab",
    "INTERNSHIP": "Internship",
    "LIBRARY": "Library",
    "CC": "Cloud Computing",
    "DL": "Deep Learning"
};

const subjectAliasToCode = {
    "ARTIFICIAL INTELLIGENCE": "AI",
    "INTERNET OF THINGS": "IOT",
    "CLOUD COMPUTING": "CC",
    "DEEP LEARNING": "DL"
};

const getSubjectCode = function (subjectText) {
    if (!subjectText) return "";
    const withoutId = subjectText.split("-")[0].replace(/\d+$/, "").trim().toUpperCase();
    return subjectAliasToCode[withoutId] || withoutId;
};

const getSubjectFamily = function (subjectText) {
    const code = getSubjectCode(subjectText);
    const display = subjectLabelByCode[code];
    if (display) {
        return display.toUpperCase();
    }
    return code;
};

export default function Timetable(props) {
    const {
        username, onDaySelect, role, onScheduleChange, refreshTrigger,
        viewMode = "original", setViewMode = function () { }, branch
    } = props;

    const [alertsList, setAlertsList] = useState([]);
    const [weeklySchedule, setWeeklySchedule] = useState([
        {
            day: "Monday", times: [
                { name: "IoT", occupancy: 0 }, { name: "MA", occupancy: 0 }, { name: "SE", occupancy: 0 }, { name: "Internship", occupancy: 0 },
                { name: "LUNCH", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }
            ]
        },
        {
            day: "Tuesday", times: [
                { name: "AI", occupancy: 0 }, { name: "SE", occupancy: 0 }, { name: "IoT", occupancy: 0 }, { name: "PBI", occupancy: 0 },
                { name: "LUNCH", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }
            ]
        },
        {
            day: "Wednesday", times: [
                { name: "MA LAB", occupancy: 0 }, { name: "MA LAB", occupancy: 0 }, { name: "PBI", occupancy: 0 }, { name: "MA", occupancy: 0 },
                { name: "LUNCH", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }
            ]
        },
        {
            day: "Thursday", times: [
                { name: "", occupancy: 0 }, { name: "AI", occupancy: 0 }, { name: "Library", occupancy: 0 }, { name: "IoT", occupancy: 0 },
                { name: "LUNCH", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }
            ]
        },
        {
            day: "Friday", times: [
                { name: "PBI", occupancy: 0 }, { name: "SE", occupancy: 0 }, { name: "AI", occupancy: 0 }, { name: "MA", occupancy: 0 },
                { name: "LUNCH", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }
            ]
        },
        {
            day: "Saturday", times: [
                { name: "", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "Project LAB", occupancy: 0 }, { name: "Project LAB", occupancy: 0 },
                { name: "LUNCH", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }, { name: "", occupancy: 0 }
            ]
        },
    ]);
    const [isLoading, setIsLoading] = useState(false);

    const [showConfirm, setShowConfirm] = useState(false);
    const [confirmMsg, setConfirmMsg] = useState("");
    const [onConfirmAction, setOnConfirmAction] = useState(null);
    const [confirmTitle, setConfirmTitle] = useState("Confirm Action");
    const [confirmType, setConfirmType] = useState("default");
    const [currentTestSubject, setCurrentTestSubject] = useState(null);
    const [testPeriodQueue, setTestPeriodQueue] = useState([]);

    const fetchAlerts = React.useCallback(function () {
        const branchParam = branch || "BCA";
        fetch(API_BASE + "/reschedule?branch=" + branchParam)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.classes) {
                    setAlertsList(data.classes);
                }
            })
            .catch(function (err) { });
    }, [branch]);

    const loadNotifications = React.useCallback(function () {
        const branchParam = branch || "BCA";
        fetch(API_BASE + "/notifications?branch=" + branchParam)
            .then(function (res) { return res.json(); })
            .catch(function (err) { });
    }, [branch]);

    const checkTestPeriods = React.useCallback(function () {
        if (!role || role.toLowerCase() !== 'teacher') return;
        fetch(API_BASE + "/check_test_periods")
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.completed && data.completed.length > 0) {
                    setTestPeriodQueue(data.completed);
                }
            })
            .catch(function (err) { });
    }, [role]);

    useEffect(function () {
        fetchAlerts();
        loadNotifications();
        checkTestPeriods();

        const pollInterval = setInterval(function () {
            fetchAlerts();
            loadNotifications();
            checkTestPeriods();
        }, 30000);

        return function () {
            clearInterval(pollInterval);
        };
    }, [fetchAlerts, loadNotifications, checkTestPeriods, refreshTrigger]);

    useEffect(function () {
        if (testPeriodQueue.length > 0 && !showConfirm) {
            const next = testPeriodQueue[0];
            setConfirmTitle("Test Period Complete");
            setConfirmMsg("The 2-week test period for " + next.subject + " has concluded. Would you like to make the new slot permanent or continue the test period?");
            setConfirmType("completion");
            setCurrentTestSubject(next);
            setShowConfirm(true);
        }
    }, [testPeriodQueue, showConfirm]);

    useEffect(function () {
        setIsLoading(true);
        const isRevised = (viewMode === "revised");
        const branchParam = branch || "BCA";
        const apiUrl = API_BASE + "/timetable?revised=" + isRevised + "&branch=" + branchParam;

        fetch(apiUrl)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.schedule && data.schedule.length > 0) {
                    setWeeklySchedule(data.schedule);
                }
                setIsLoading(false);
            })
            .catch(function (error) {
                setIsLoading(false);
            });
    }, [viewMode, refreshTrigger, branch]);

    const extractSubjectName = function (rawSubjectText) {
        if (!rawSubjectText) return "";
        if (rawSubjectText === "LUNCH") return "";
        const splitParts = rawSubjectText.split("-");
        const baseName = splitParts[0].trim();
        return baseName.replace(/\d+$/, '');
    };

    const checkIfSubjectIsRescheduled = function (subjectName, currentDay) {
        if (!subjectName || !alertsList) return null;
        const currentDayShort = normalizeDay(currentDay);
        const subjectRawLower = String(subjectName).toLowerCase();
        const subjectFamily = getSubjectFamily(subjectName);

        const record = alertsList.find(function (r) {
            const isValidStatus = (r.status === "Rescheduled" || r.status === "Cancelled" || r.status === "Merged" || r.status === "Delayed");
            if (!isValidStatus || r.is_active === false) return false;

            if (r.new_time) {
                const [targetDay] = r.new_time.split(" ");
                if (normalizeDay(targetDay) === currentDayShort) {
                    if (getSubjectFamily(r.subject) === subjectFamily) return true;
                }
            }

            const recordDay = normalizeDay(r.original_time);
            const dayMatches = !recordDay || recordDay === currentDayShort;
            if (!dayMatches) return false;

            const recordRaw = String(r.subject || "");
            if (recordRaw.toLowerCase() === subjectRawLower) {
                return true;
            }

            if (!recordDay) return false;

            return getSubjectFamily(recordRaw) === subjectFamily;
        });

        return record ? record.status : null;
    };

    const determineCellClassName = function (subjectName, currentDay) {
        if (subjectName === "LUNCH") return "lunch-cell";
        if (!subjectName) return "empty-cell";

        const status = checkIfSubjectIsRescheduled(subjectName, currentDay);
        if (!status) return "class-cell";

        if (status === "Rescheduled") return "rescheduled-cell";
        if (status === "Delayed") return "delayed-cell";
        if (status === "Cancelled") return "cancelled-cell";
        if (status === "Merged") return "rescheduled-cell";

        return "rescheduled-cell";
    };

    const handleSubjectCellClick = function (e, subjectName, dayName, dayScheduleTimes) {
        if (role !== 'teacher' || !subjectName || subjectName === "LUNCH") return;

        const status = checkIfSubjectIsRescheduled(subjectName, dayName);
        if (!status) return;

        e.stopPropagation();

        setConfirmMsg("Are you sure you want to revert " + extractSubjectName(subjectName) + " to original position?");
        setOnConfirmAction(function () {
            console.log("Reverting subject: " + subjectName);
            return function () {
                fetch(API_BASE + "/reset_subject", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ subject: subjectName })
                })
                    .then(function (res) { return res.json(); })
                    .then(function () {
                        fetchAlerts();
                        if (onScheduleChange) onScheduleChange();
                        setShowConfirm(false);
                    });
            };
        });
        setShowConfirm(true);
    };

    const handleDayClicked = function (dayName, subjectList) {
        if (!dayName) {
            if (onDaySelect) onDaySelect(null, []);
            return;
        }

        const classesForDay = subjectList.map(function (subjectItem, index) {
            const timeSlot = timeSlotHeaders[index];
            const subject = (subjectItem && typeof subjectItem === 'object') ? subjectItem.name : subjectItem;

            if (!subject || subject === "LUNCH") return null;

            const subjectCode = getSubjectCode(subject);
            const displayName = subjectLabelByCode[subjectCode];
            if (!displayName) return null;

            const subjectRawLower = String(subject).toLowerCase();
            const subjectFamily = getSubjectFamily(subject);
            const currentDayShort = normalizeDay(dayName);
            const record = alertsList.find(function (r) {
                const recordDay = normalizeDay(r.original_time);
                const dayMatches = !recordDay || recordDay === currentDayShort;
                if (!dayMatches || r.is_active === false) return false;

                const recordRaw = String(r.subject || "");
                if (recordRaw.toLowerCase() === subjectRawLower) {
                    return true;
                }

                if (!recordDay) return false;

                return getSubjectFamily(recordRaw) === subjectFamily;
            });

            const status = record ? record.status : "On Schedule";

            return {
                time: timeSlot,
                subject: displayName,
                status: status
            };
        }).filter(Boolean);

        const mergedClasses = [];
        let i = 0;
        while (i < classesForDay.length) {
            const current = classesForDay[i];
            const next = classesForDay[i + 1];

            if (next && current.subject === next.subject &&
                (current.subject === "Mobile Applications Lab" || current.subject === "Project Lab")) {
                const startTime = current.time.split('-')[0];
                const endTime = next.time.split('-')[1];
                mergedClasses.push({ ...current, time: `${startTime}-${endTime}` });
                i += 2;
            } else {
                mergedClasses.push(current);
                i++;
            }
        }

        if (onDaySelect) {
            onDaySelect(dayName, mergedClasses);
        }
    };

    const handleRevertChanges = function () {
        setConfirmMsg("Users will be notified: 'Timetable is reverted to its original form'");
        setOnConfirmAction(function () {
            return function () {
                fetch(API_BASE + "/reset_timetable", {
                    method: "POST"
                })
                    .then(function (data) {
                        fetchAlerts();
                        loadNotifications();
                        setShowConfirm(false);
                        if (onScheduleChange) onScheduleChange();
                    });
            };
        });
        setShowConfirm(true);
    };

    const handleRestoreChanges = function () {
        setConfirmMsg("Restore Changes? This will re-apply all scheduled changes.");
        setOnConfirmAction(function () {
            return function () {
                const endpoint = API_BASE + "/restore_timetable";
                fetch(endpoint, { method: 'POST' })
                    .then(function (response) { return response.json(); })
                    .then(function () {
                        fetchAlerts();
                        loadNotifications();
                        setShowConfirm(false);
                        if (onScheduleChange) onScheduleChange();
                    });
            };
        });
        setShowConfirm(true);
    };

    const timeSlotHeaders = [
        "9:15-10:05", "10:10-11:00", "11:05-11:55", "12:00-12:50", "12:50-1:50", "1:50-2:40", "2:45-3:35", "3:40-4:30"
    ];

    if (isLoading) {
        return <div className="timetable-container">Loading timetable...</div>;
    }

    return (
        <div className="timetable-container">
            { }
            <div className="timetable-header">
                <h3>
                    {(username ? username.toUpperCase() + "'S " : "") + "TIMETABLE"}
                </h3>

                <div className="timetable-controls">
                    { }
                    {role.toLowerCase() === 'teacher' && (
                        <>
                            <div id="dept-controls" style={{ display: 'flex', gap: '8px', borderRight: '1px solid #d9bc9433', paddingRight: '10px', marginRight: '10px' }}>
                                <button
                                    onClick={handleRevertChanges}
                                    className="buttonrev btn-red"
                                >
                                    Revert Changes
                                </button>
                                <button
                                    onClick={handleRestoreChanges}
                                    className="buttonrev btn-green"
                                >
                                    Restore Changes
                                </button>
                            </div>

                            { }
                            <div id="view-controls" style={{ display: 'flex', gap: '8px' }}>
                                <button
                                    className={viewMode === 'original' ? 'buttonog' : 'buttonrev'}
                                    onClick={function () { setViewMode('original'); }}
                                    id="timetable-original"
                                >
                                    Original
                                </button>
                                <button
                                    className={viewMode === 'revised' ? 'buttonog' : 'buttonrev'}
                                    onClick={function () { setViewMode('revised'); }}
                                    id="timetable-latest"
                                >
                                    Latest Changes
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>

            <div id="main-timetable-grid" className="table-responsive" onClick={function (e) {
                if (e.target.tagName === 'DIV') handleDayClicked(null, []);
            }}>
                <table className="timetable">
                    <thead>
                        <tr>
                            <th className="timetable-day-cell">DAY / TIME</th>
                            {timeSlotHeaders.map(function (timeSlotText, index) {
                                return (
                                    <th key={index}>
                                        {timeSlotText === "12:50-1:50" ? "" : timeSlotText}
                                    </th>
                                );
                            })}
                        </tr>
                    </thead>
                    <tbody>
                        {weeklySchedule.map(function (daySchedule, rowIndex) {
                            return (
                                <tr
                                    key={rowIndex}
                                    id={rowIndex === 0 ? "timetable-monday-row" : null}
                                    onClick={function (e) {
                                        e.stopPropagation();
                                        handleDayClicked(daySchedule.day, daySchedule.times);
                                    }}
                                >
                                    <td className="timetable-day-cell">{daySchedule.day}</td>

                                    {daySchedule.times.map(function (subjectObj, colIndex) {
                                        const currentSubject = subjectObj.name;
                                        const currentTimeSlot = timeSlotHeaders[colIndex];
                                        const isLunchTime = (currentTimeSlot === "12:50-1:50");

                                        if (isLunchTime) {
                                            if (rowIndex === 0) {
                                                return (
                                                    <td key={colIndex}
                                                        className="lunch-cell"
                                                        rowSpan={weeklySchedule.length}
                                                        onClick={function (e) {
                                                            e.stopPropagation();
                                                            handleDayClicked(null, []);
                                                        }}
                                                    >
                                                        LUNCH
                                                    </td>
                                                );
                                            }
                                            return null;
                                        }

                                        const nextSubjectObj = daySchedule.times[colIndex + 1];
                                        const prevSubjectObj = daySchedule.times[colIndex - 1];
                                        const nextSubject = nextSubjectObj ? nextSubjectObj.name : "";
                                        const previousSubject = prevSubjectObj ? prevSubjectObj.name : "";

                                        const nextTimeSlot = timeSlotHeaders[colIndex + 1];
                                        const previousTimeSlot = timeSlotHeaders[colIndex - 1];

                                        const shouldMergeWithNext = (currentSubject && currentSubject.toUpperCase().includes('LAB') && currentSubject === nextSubject && nextTimeSlot !== "12:50-1:50");
                                        const isMergedWithPrevious = (currentSubject && currentSubject.toUpperCase().includes('LAB') && currentSubject === previousSubject && previousTimeSlot !== "12:50-1:50");

                                        if (shouldMergeWithNext) {
                                            const cellClassName = determineCellClassName(currentSubject, daySchedule.day);
                                            const cleanName = extractSubjectName(currentSubject);
                                            const isLabSubject = currentSubject.includes("LAB");

                                            return (
                                                <td
                                                    key={colIndex}
                                                    colSpan={2}
                                                    className={cellClassName}
                                                    style={{
                                                        cursor: (role === 'teacher' && checkIfSubjectIsRescheduled(currentSubject, daySchedule.day)) ? 'pointer' : 'default'
                                                    }}
                                                    onClick={function (e) {
                                                        handleSubjectCellClick(e, currentSubject, daySchedule.day, daySchedule.times);
                                                    }}
                                                >
                                                    <div style={{ fontWeight: isLabSubject ? 'bold' : 'normal' }}>
                                                        {cleanName}
                                                    </div>
                                                </td>
                                            );
                                        }

                                        if (isMergedWithPrevious) {
                                            return null;
                                        }

                                        const cellClassName = determineCellClassName(currentSubject, daySchedule.day);
                                        const displayName = extractSubjectName(currentSubject);

                                        return (
                                            <td
                                                key={colIndex}
                                                className={cellClassName}
                                                style={{
                                                    cursor: (role === 'teacher' && checkIfSubjectIsRescheduled(currentSubject, daySchedule.day)) ? 'pointer' : 'default'
                                                }}
                                                onClick={function (e) {
                                                    handleSubjectCellClick(e, currentSubject, daySchedule.day, daySchedule.times);
                                                }}
                                            >
                                                {displayName}
                                            </td>
                                        );
                                    })}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            { }
            {showConfirm && (
                <div className="modal-overlay">
                    <div className="modal-content animate-up">
                        <h3 style={{ color: '#d9bc94', fontFamily: 'Garamond, serif' }}>{confirmTitle}</h3>
                        <p style={{ color: '#e8d4b8', margin: '20px 0' }}>{confirmMsg}</p>
                        <div className="modal-actions">
                            {confirmType === "completion" ? (
                                <div style={{display: 'flex', flexDirection: 'column', gap: '10px', width: '100%'}}>
                                    <button
                                        className="buttonog"
                                        onClick={function () {
                                            fetch(API_BASE + "/make_permanent", {
                                                method: "POST",
                                                headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ subject: currentTestSubject.subject })
                                            }).then(function () {
                                                setShowConfirm(false);
                                                setTestPeriodQueue(function (prev) { return prev.slice(1); });
                                                if (onScheduleChange) onScheduleChange();
                                            });
                                        }}
                                    >
                                        MAKE PERMANENT
                                    </button>
                                    <button
                                        className="buttonog"
                                        style={{ borderColor: '#22c55e', color: '#22c55e' }}
                                        onClick={function () {
                                            fetch(API_BASE + "/extend_test_period", {
                                                method: "POST",
                                                headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ subject: currentTestSubject.subject })
                                            }).then(function () {
                                                setShowConfirm(false);
                                                setTestPeriodQueue(function (prev) { return prev.slice(1); });
                                                if (onScheduleChange) onScheduleChange();
                                            });
                                        }}
                                    >
                                        CONTINUE TEST PERIOD (2 WEEKS)
                                    </button>
                                    <button
                                        className="buttonrev"
                                        style={{ borderColor: '#ef4444', color: '#ef4444' }}
                                        onClick={function () {
                                            fetch(API_BASE + "/reset_subject", {
                                                method: "POST",
                                                headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ subject: currentTestSubject.subject })
                                            }).then(function () {
                                                setShowConfirm(false);
                                                setTestPeriodQueue(function (prev) { return prev.slice(1); });
                                                if (onScheduleChange) onScheduleChange();
                                            });
                                        }}
                                    >
                                        REVERT TO ORIGINAL
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <button
                                        className="button primary"
                                        onClick={function () { if (onConfirmAction) onConfirmAction(); }}
                                    >
                                        YES
                                    </button>
                                    <button
                                        className="button secondary"
                                        onClick={function () { setShowConfirm(false); }}
                                    >
                                        NO
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
