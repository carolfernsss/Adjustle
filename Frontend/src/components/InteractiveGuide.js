import React, { useState, useEffect, useCallback } from 'react';
import { X, ChevronRight, HelpCircle } from 'lucide-react';

// This component creates an interactive step-by-step introduction guide for the application's features
const InteractiveGuide = function ({ role, currentPage, onNavigate, onClose, showTransition }) {
    const [step, setStep] = useState(0);
    const [pos, setPos] = useState({ top: 0, left: 0, width: 0, height: 0, centered: true });

    // Logic to prepare the guide steps based on the user's role (Student or Teacher)
    const activeSteps = React.useMemo(function () {
        const studentSteps = [
            {
                title: "Your Daily Schedule",
                description: "Here you'll find the live timetable for your Course. You can see all your classes for the week here.",
                page: "timetable",
                targetId: null,
                position: "center"
            },
            {
                title: "Live Timetable",
                description: "This is the live grid showing all class sessions for your course. It's updated in real-time.",
                page: "timetable",
                targetId: "main-timetable-grid",
                position: "top"
            },
            {
                title: "Step 1: Click any Day",
                description: "Click specifically on any Day (e.g. Monday) to focus on its subjects.",
                page: "timetable",
                targetId: "timetable-monday-row",
                position: "bottom"
            },
            {
                title: "Step 2: View Filtered List",
                description: "The list on the right now updates to show only the subjects and status for that specific day.",
                page: "timetable",
                targetId: "right-sidebar-alerts",
                position: "left"
            },
            {
                title: "Real-Time Updates",
                description: "Keep an eye on this sidebar. It shows instant alerts for any rescheduled or cancelled classes in your department.",
                page: "timetable",
                targetId: "class-alerts-sidebar",
                position: "left"
            }
        ];

        const teacherSteps = [
            {
                title: "One-Click Sync",
                description: "REVERT: Undo all current week's changes.\nRESTORE: Bring back your previously saved adjustments across the department.",
                page: "timetable",
                targetId: "dept-controls",
                position: "bottom"
            },
            {
                title: "View Modes",
                description: "ORIGINAL: The standard university timetable.\nLATEST: Shows the adjustments made based on AI attendance data.",
                page: "timetable",
                targetId: "view-controls",
                position: "bottom"
            },
            {
                title: "AI Analysis",
                description: "Go to the 'Count' page to start. First, upload a clear photo of the classroom.",
                page: "count",
                targetId: "upload-dropzone",
                position: "bottom"
            },
            {
                title: "Select Subject",
                description: "Choose the subject you are taking attendance for.",
                page: "count",
                targetId: "input-subject",
                position: "left"
            },
            {
                title: "Pick Date",
                description: "Select the date of the class from the calendar.",
                page: "count",
                targetId: "input-calendar",
                position: "left"
            },

            {
                title: "Select Time Slot",
                description: "Choose the time slot for the class.",
                page: "count",
                targetId: "input-time-slot",
                position: "left"
            },
            {
                title: "Enter Strength",
                description: "Type in the total number of students in the class.",
                page: "count",
                targetId: "input-total-students",
                position: "left"
            },
            {
                title: "Analyze",
                description: "Click here to let our AI count the students in the photo.",
                page: "count",
                targetId: "count-action-btn",
                position: "left"
            },
            {
                title: "AI Outcomes",
                description: "ON SCHEDULE: No changes needed.\nDELAYED: Class moved by 1 hour.\nMERGE: Asks to merge with another class.",
                page: "count",
                targetId: "analysis-results-card",
                position: "right"
            }
        ];

        return role === 'teacher' ? teacherSteps : studentSteps;
    }, [role]);

    // Reset step to 0 when role changes
    useEffect(function () {
        setStep(0);
    }, [role]);

    const currentStepData = activeSteps[step];

    // Logic to calculate where on the screen the highlight spotlight should appear
    const updatePosition = useCallback(function () {
        if (!currentStepData) return;

        if (!currentStepData.targetId) {
            // Center positioning state
            setPos({ top: 0, left: 0, width: 0, height: 0, centered: true });
            return;
        }

        const el = document.getElementById(currentStepData.targetId);
        if (el) {
            const rect = el.getBoundingClientRect();
            setPos({
                top: rect.top + window.scrollY,
                left: rect.left + window.scrollX,
                width: rect.width,
                height: rect.height,
                centered: false
            });
        } else {
            // Reset position if element is missing to avoid "ghost" tooltips from previous steps
            setPos({ top: 0, left: 0, width: 0, height: 0, centered: true });
        }
    }, [currentStepData]);

    // Handle navigation logic
    useEffect(function () {
        if (showTransition) return; // Don't trigger navigation if already transitioning

        if (currentStepData && currentStepData.page !== currentPage) {
            onNavigate(currentStepData.page);
        }
    }, [step, currentPage, currentStepData, onNavigate, showTransition]);

    useEffect(function () {
        // Scroll to target only if it's likely off-screen (bottom elements)
        // Scroll to target only if it's likely off-screen (bottom elements) or needs re-centering (results)
        const bottomTargets = ['input-total-students', 'input-time-slot', 'count-action-btn', 'analysis-results-card'];

        if (currentStepData && bottomTargets.includes(currentStepData.targetId)) {
            setTimeout(function () {
                const el = document.getElementById(currentStepData.targetId);
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
        }

        updatePosition();
        // Page might need a split second to render
        const timer = setTimeout(updatePosition, 300);
        window.addEventListener('resize', updatePosition);
        window.addEventListener('scroll', updatePosition, true); // Capture scroll
        return function () {
            clearTimeout(timer);
            window.removeEventListener('resize', updatePosition);
            window.removeEventListener('scroll', updatePosition, true);
        };
    }, [step, currentPage, currentStepData, updatePosition]);

    // Auto-advance logic for interactive steps
    useEffect(function () {
        if (!currentStepData) return;

        // Clean up any previous interval/timeout
        let intervalId = null;

        // 1. AI Analysis (Step 2): Use interval to check for upload panel
        if (currentStepData.title === "AI Analysis") {
            intervalId = setInterval(function () {
                const panel = document.getElementById("detection-settings-panel");
                if (panel) {
                    clearInterval(intervalId);
                    setTimeout(function () {
                        setStep(function (prev) { return prev + 1; });
                    }, 100);
                }
            }, 1000);
        }

        // 2. Analyze (Step 7): Wait for results card to appear
        if (currentStepData.title === "Analyze") {
            // Once user clicks 'Analyze', wait for result card
            // We can just poll for result card presence
            intervalId = setInterval(function () {
                const resultCard = document.getElementById("analysis-results-card");
                if (resultCard) {
                    clearInterval(intervalId);
                    setTimeout(function () {
                        setStep(function (prev) { return prev + 1; });
                    }, 100);
                }
            }, 1000);
        }

        // 3. AI Outcomes (Step 8): Finish on Approve/Deny
        if (currentStepData.title === "AI Outcomes") {
            const handleOutcomeClick = function () {
                setTimeout(onClose, 500); // Close guide after action
            };

            const approveBtn = document.getElementById("approve-action-btn");
            const denyBtn = document.getElementById("deny-action-btn");

            if (approveBtn) approveBtn.addEventListener('click', handleOutcomeClick);
            if (denyBtn) denyBtn.addEventListener('click', handleOutcomeClick);

            return function () {
                if (approveBtn) approveBtn.removeEventListener('click', handleOutcomeClick);
                if (denyBtn) denyBtn.removeEventListener('click', handleOutcomeClick);
            };
        }

        // 4. Click a Day (Interactive advance)
        if (currentStepData.title === "Step 1: Click any Day" || currentStepData.title === "Focus on a Day") {
            const handleRowClick = function () {
                setTimeout(function () {
                    setStep(function (prev) { return prev + 1; });
                }, 100);
            };

            const mondayRow = document.getElementById("timetable-monday-row");
            if (mondayRow) {
                mondayRow.addEventListener('click', handleRowClick);
                return function () {
                    mondayRow.removeEventListener('click', handleRowClick);
                };
            }
        }

        // 5. Teacher Count flow (Subject, Date, Slot, etc.)
        const countSteps = ["Select Subject", "Pick Date", "Select Time Slot", "Enter Strength"];
        if (role === 'teacher' && countSteps.includes(currentStepData.title)) {
            const handleInteract = function () {
                setTimeout(function () {
                    setStep(function (prev) { return prev + 1; });
                }, 400); 
            };

            const target = document.getElementById(currentStepData.targetId);
            if (target) {
                // For number inputs (Strength), use blur. For others, use change + click for promptness
                if (target.tagName === 'INPUT' && target.type === 'number') {
                    target.addEventListener('blur', handleInteract);
                    return () => target.removeEventListener('blur', handleInteract);
                } else if (currentStepData.targetId === 'input-calendar' || currentStepData.targetId === 'input-time-slot') {
                    // Specific click listeners for non-form elements
                    const handleSpecificClick = function (e) {
                        // For calendar, only advance if a day cell is clicked
                        if (currentStepData.targetId === 'input-calendar' && !e.target.classList.contains('calendar-day-cell')) {
                            return;
                        }
                        // For Time Slot, only advance if a button is clicked
                        if (currentStepData.targetId === 'input-time-slot' && e.target.tagName !== 'BUTTON') {
                            return;
                        }
                        
                        setTimeout(function () {
                            setStep(function (prev) { return prev + 1; });
                        }, 400);
                    };

                    target.addEventListener('click', handleSpecificClick);
                    return function () {
                        target.removeEventListener('click', handleSpecificClick);
                    };
                } else {
                    // Standard change event (for Select dropdowns)
                    target.addEventListener('change', handleInteract);
                    return function () {
                        target.removeEventListener('change', handleInteract);
                    };
                }
            }
        }

        return function () {
            if (intervalId) clearInterval(intervalId);
        };
    }, [step, currentStepData, role, onClose]);

    const nextStep = function () {
        if (step < activeSteps.length - 1) {
            setStep(step + 1);
        } else {
            onClose();
        }
    };

    const prevStep = function () {
        if (step > 0) {
            setStep(step - 1);
        }
    };

    if (!currentStepData) return null;

    // Hide guide if we are waiting for navigation to complete
    if (currentStepData.page !== currentPage) return null;

    // Style logic to position the guide tooltip near its target element
    const getTooltipStyle = function () {
        if (pos.centered) {
            return {
                position: 'fixed',
                zIndex: 6001,
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '320px',
                backgroundColor: '#1c140ca6',
                backdropFilter: 'blur(10px)',
                border: '1px solid #d9bc94',
                borderRadius: '12px',
                padding: '25px',
                boxShadow: '0 10px 40px #000000e6',
                transition: 'all 0.4s ease-out'
            };
        }

        // Hide if target requires an element but none found (width=0)
        if (!pos.width) return { display: 'none' };

        const space = 15;
        let style = {
            position: 'absolute',
            zIndex: 6001,
            width: '280px',
            backgroundColor: '#1c140ca6',
            backdropFilter: 'blur(10px)',
            border: '1px solid #d9bc94',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 10px 30px #000000cc',
            transition: 'all 0.4s ease-out'
        };

        if (currentStepData.position === 'bottom') {
            style.top = pos.top + pos.height + space + 'px';
            style.left = pos.left + (pos.width / 2) - 140 + 'px';
        } else if (currentStepData.position === 'top') {
            style.top = pos.top - space - 200 + 'px'; // Estimated height
            style.left = pos.left + (pos.width / 2) - 140 + 'px';
        } else if (currentStepData.position === 'left') {
            style.top = pos.top + (pos.height / 2) - 100 + 'px';
            style.left = pos.left - 280 - space + 'px';
        } else if (currentStepData.position === 'right') {
            style.top = pos.top + (pos.height / 2) - 100 + 'px';
            style.left = pos.left + pos.width + space + 'px';
        }

        return style;
    };

    const spotlightStyle = {
        position: 'absolute',
        top: pos.top - 6 + 'px',
        left: pos.left - 6 + 'px',
        width: pos.width + 12 + 'px',
        height: pos.height + 12 + 'px',
        borderRadius: '8px',
        backgroundColor: '#d9bc941a', // Adds a slight tint over the target
        boxShadow: '0 0 20px #d9bc9480, 0 0 0 9999px #000000d9', // Bright gold glow + darker outer shadow
        border: '3px solid #d9bc94',
        zIndex: 6000,
        pointerEvents: 'none',
        transition: 'all 0.4s ease-out',
        display: pos.centered ? 'none' : 'block'
    };

    return (
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
            <div style={{ ...getTooltipStyle(), pointerEvents: 'auto' }} className="animate-up">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', columnGap: '8px', color: '#d9bc94' }}>
                        <HelpCircle size={18} />
                        <span style={{ fontSize: '14px', fontWeight: 'bold' }}>GUIDE</span>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#d9bc94', cursor: 'pointer', opacity: 0.6 }}>
                        <X size={18} />
                    </button>
                </div>

                <h3 style={{ fontFamily: 'Garamond, serif', color: '#e8d4b8', fontSize: '18px', marginBottom: '8px', textShadow: '0 0 15px #d9bc9466', fontWeight: 'bold' }}>
                    {currentStepData.title}
                </h3>
                <p style={{ color: '#e8d4b8', fontSize: '14px', lineHeight: '1.5', marginBottom: '20px', whiteSpace: 'pre-line' }}>
                    {currentStepData.description}
                </p>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ color: '#d9bc9433', fontSize: '11px' }}>
                        STEP {step + 1} / {activeSteps.length}
                    </div>
                    <div style={{ display: 'flex', columnGap: '10px' }}>
                        {step > 0 && (
                            <button onClick={prevStep} style={{ background: 'none', border: 'none', color: '#d9bc94', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' }}>
                                BACK
                            </button>
                        )}
                        <button
                            onClick={nextStep}
                            style={{
                                backgroundColor: '#d9bc94',
                                color: '#231814',
                                border: 'none',
                                padding: '6px 15px',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontWeight: 'bold',
                                fontSize: '12px',
                                display: 'flex',
                                alignItems: 'center',
                                columnGap: '4px'
                            }}
                        >
                            {step === activeSteps.length - 1 ? 'FINISH' : 'NEXT'}
                            <ChevronRight size={14} />
                        </button>
                    </div>
                </div>
            </div>

            <div style={spotlightStyle}></div>
        </div>
    );
};

export default InteractiveGuide;
