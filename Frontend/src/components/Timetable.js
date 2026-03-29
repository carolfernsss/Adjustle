import { API_BASE } from "../api_config";

// This function converts the day name to proper case for consistency
const normalizeDay = function (day) {
    if (!day) return "";
    const mapping = {
        "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
        "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday",
    };
    const lower = day.toLowerCase();
    return mapping[lower] || day;
};

// This object maps short subject codes to their full descriptive names
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

// This mapping helps in getting the short code from a full subject name
const subjectAliasToCode = {
    "ARTIFICIAL INTELLIGENCE": "AI",
    "INTERNET OF THINGS": "IOT",
    "CLOUD COMPUTING": "CC",
    "DEEP LEARNING": "DL"
};

// This function extracts the clean subject code from raw text strings
const getSubjectCode = function (subjectText) {
    if (!subjectText) return "";
    const withoutId = subjectText.split("-")[0].replace(/\d+$/, "").trim().toUpperCase();
    return subjectAliasToCode[withoutId] || withoutId;
};

// This helper function returns the standardized full family name of a subject
const getSubjectFamily = function (subjectText) {
    const code = getSubjectCode(subjectText);
    const display = subjectLabelByCode[code];
    if (display) {
        return display.toUpperCase();
    }
    return code;
};

import React, { useState, useEffect } from "react";
import "../css/Timetable.css";

// This is the main component that renders the interactive weekly timetable grid
export default function Timetable(props) {
    const {
        username, onDaySelect, role, onScheduleChange, refreshTrigger,
        viewMode = "original", setViewMode = function () { }, branch
    } = props;

    // State variable for storing the list of schedule alerts from the server
    const [alertsList, setAlertsList] = useState([]);
    // State variable for storing the full weekly schedule structure
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
    // State for showing the loading spinner during data fetching
    const [isLoading, setIsLoading] = useState(false);

    // States for managing the custom confirmation popup modal
    const [showConfirm, setShowConfirm] = useState(false);
    const [confirmMsg, setConfirmMsg] = useState("");
    const [onConfirmAction, setOnConfirmAction] = useState(null);
    const [confirmTitle, setConfirmTitle] = useState("Confirm Action");
    const [confirmType, setConfirmType] = useState("default");
    const [currentTestSubject, setCurrentTestSubject] = useState(null);
    const [testPeriodQueue, setTestPeriodQueue] = useState([]);

    // Function to fetch the latest schedule alerts based on the selected branch
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
    }, [branch]); // eslint-disable-line react-hooks/exhaustive-deps

    // Function to load the current notifications
    const loadNotifications = React.useCallback(function () {
        const branchParam = branch || "BCA";
        fetch(API_BASE + "/notifications?branch=" + branchParam)
            .then(function (res) { return res.json(); })
            .catch(function (err) { });
    }, [branch]); // eslint-disable-line react-hooks/exhaustive-deps

    // Function to check if any test periods have completed (Teacher role only)
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
    }, [role]); // eslint-disable-line react-hooks/exhaustive-deps

    // Hook to set up an interval for polling fresh data every 30 seconds
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
    }, [fetchAlerts, loadNotifications, checkTestPeriods, refreshTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

    // Hook to show a confirmation dialog when a test period is finished
    useEffect(function () {
        if (testPeriodQueue.length > 0 && !showConfirm) {
            const next = testPeriodQueue[0];
            setConfirmTitle("Test Period Complete");
            setConfirmMsg("Test period for " + next.subject + " is over. Do you want the permanent position of \"" + next.subject + "\" to be \"" + next.new_time.split(' ')[0] + "\" at \"" + next.new_time.split(' ')[1] + "\"?");
            setConfirmType("completion");
            setCurrentTestSubject(next);
            setShowConfirm(true);
        }
    }, [testPeriodQueue, showConfirm]);

    // Hook to fetch the full timetable grid data whenever view mode or branch changes
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

    /* ---- Helper functions ---- */

    // Helper to clean up raw subject strings for display in the table cells
    const extractSubjectName = function (rawSubjectText) {
        if (!rawSubjectText) return "";
        if (rawSubjectText === "LUNCH") return "";
        const splitParts = rawSubjectText.split("-");
        const baseName = splitParts[0].trim();
        // Strip trailing digits (e.g., MA1 -> MA) for cleaner shortlist in cell
        return baseName.replace(/\d+$/, '');
    };

    // Logic to determine if a class has been moved or cancelled in the latest view
    const checkIfSubjectIsRescheduled = function (subjectName, currentDay) {
        if (!subjectName || !alertsList) return null;
        const currentDayShort = normalizeDay(currentDay);
        const subjectRawLower = String(subjectName).toLowerCase();
        const subjectFamily = getSubjectFamily(subjectName);

        // Find the record that applies to this cell
        const record = alertsList.find(function (r) {
            const isValidStatus = (r.status === "Rescheduled" || r.status === "Cancelled" || r.status === "Merged" || r.status === "Delayed");
            if (!isValidStatus || r.is_active === false) return false;

            // 1. Check if this is the NEW home of a moved class
            if (r.new_time) {
                const [targetDay] = r.new_time.split(" ");
                // Ideally we'd check targetSlot too, but since subject name matches
                // and day matches, it's almost certainly the right cell.
                if (normalizeDay(targetDay) === currentDayShort) {
                    if (getSubjectFamily(r.subject) === subjectFamily) return true;
                }
            }

            // 2. Check if this is OR was the original home
            const recordDay = normalizeDay(r.original_time);
            const dayMatches = !recordDay || recordDay === currentDayShort;
            if (!dayMatches) return false;

            const recordRaw = String(r.subject || "");
            if (recordRaw.toLowerCase() === subjectRawLower) {
                return true;
            }

            // Fallback to family match only for explicitly day-tagged updates.
            if (!recordDay) return false;

            return getSubjectFamily(recordRaw) === subjectFamily;
        });

        return record ? record.status : null;
    };

    // Function to assign CSS classes to cells based on their current status
    const determineCellClassName = function (subjectName, currentDay) {
        if (subjectName === "LUNCH") return "lunch-cell";
        if (!subjectName) return "empty-cell";

        const status = checkIfSubjectIsRescheduled(subjectName, currentDay);
        if (!status) return "class-cell";

        if (status === "Rescheduled") return "rescheduled-cell";
        if (status === "Delayed") return "delayed-cell";
        if (status === "Cancelled") return "cancelled-cell";
        if (status === "Merged") return "rescheduled-cell"; // Use orange for merged too

        return "rescheduled-cell";
    };

    // Handler for when a teacher clicks a slot to revert it to original state
    const handleSubjectCellClick = function (e, subjectName, dayName, dayScheduleTimes) {
        if (role !== 'teacher' || !subjectName || subjectName === "LUNCH") return;

        const status = checkIfSubjectIsRescheduled(subjectName, dayName);
        if (!status) return; // Only modified classes can be reverted

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

    // Handler for clicking a day label to see the detailed list of classes
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

            // Find actual record to get specific status (Delayed, Merged, etc)
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

                // Family fallback is safe only when backend tagged the update day.
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

        // Merge consecutive labs logic here if needed, but for now simple list is fine or re-add merge logic
        // Re-adding merge logic for completeness as it was there before
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


    // Function that resets the entire timetable back to the original schedule
    const handleRevertChanges = function () {
        setConfirmMsg("Users will be notified: 'Timetable is reverted to its original form'");
        setOnConfirmAction(function () {
            return function () {
                fetch(API_BASE + "/reset_timetable", {
                    method: "POST"
                })
                    .then(function (data) {
                        fetchAlerts();
                        loadNotifications(); // Refresh bell badge
                        setShowConfirm(false);
                        if (onScheduleChange) onScheduleChange();
                    });
            };
        });
        setShowConfirm(true);
    };

    // Function to restore all scheduled changes that were previously made
    const handleRestoreChanges = function () {
        setConfirmMsg("Restore Changes? This will re-apply all scheduled changes.");
        setOnConfirmAction(function () {
            return function () {
                const endpoint = API_BASE + "/restore_timetable";
                fetch(endpoint, { method: 'POST' })
                    .then(function (response) { return response.json(); })
                    .then(function () {
                        fetchAlerts();
                        loadNotifications(); // Refresh bell badge
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
            {/* ---- Timetable Top Header Section ---- */}
            <div className="timetable-header">
                <h3>
                    {(username ? username.toUpperCase() + "'S " : "") + "TIMETABLE"}
                </h3>

                {role === 'teacher' && (
                    <div className="timetable-controls">
                        {/* Dept Controls Group */}
                        <div style={{ display: 'flex', gap: '8px', borderRight: '1px solid #d9bc9433', paddingRight: '10px', marginRight: '10px' }}>
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

                        {/* View Mode Toggle */}
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
                )}
            </div>

            <div className="table-responsive" onClick={function (e) {
                // Clear selection if clicking outside cells
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
                                    onClick={function (e) {
                                        e.stopPropagation(); // Prevent bubbling up to the reset handler
                                        handleDayClicked(daySchedule.day, daySchedule.times);
                                    }}
                                >
                                    <td className="timetable-day-cell">{daySchedule.day}</td>

                                    {daySchedule.times.map(function (subjectObj, colIndex) {
                                        const currentSubject = subjectObj.name;
                                        const currentTimeSlot = timeSlotHeaders[colIndex];
                                        const isLunchTime = (currentTimeSlot === "12:50-1:50");

                                        // // Special handling for the lunch break column
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

                                        const shouldMergeWithNext = (currentSubject && currentSubject === nextSubject && nextTimeSlot !== "12:50-1:50");
                                        const isMergedWithPrevious = (currentSubject && currentSubject === previousSubject && previousTimeSlot !== "12:50-1:50");

                                        // // Logic to handle subjects that span multiple slots (like Labs)
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
            {/* ---- Confirmation Modals for Schedule Changes ---- */}
            {showConfirm && (
                <div className="modal-overlay">
                    <div className="modal-content animate-up">
                        <h3 style={{ color: '#d9bc94', fontFamily: 'Garamond, serif' }}>{confirmTitle}</h3>
                        <p style={{ color: '#e8d4b8', margin: '20px 0' }}>{confirmMsg}</p>
                        <div className="modal-actions">
                            {confirmType === "completion" ? (
                                <>
                                    <button
                                        className="button primary"
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
                                        YES (MAKE PERMANENT)
                                    </button>
                                    <button
                                        className="button secondary"
                                        onClick={function () {
                                            setConfirmTitle("Decide Next Step");
                                            setConfirmMsg("What should happen to \"" + currentTestSubject.subject + "\"?");
                                            setConfirmType("test_followup");
                                        }}
                                    >
                                        NO
                                    </button>
                                </>
                            ) : confirmType === "test_followup" ? (
                                <>
                                    <button
                                        className="button primary"
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
                                    <button
                                        className="button primary"
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
                                        ANOTHER TEST PERIOD (2 WEEKS)
                                    </button>
                                </>
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
