import React, { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || "";

/**
 * Unified Merge Requests component handling both global popups and list view in the sidebar.
 * @param {Object} props - branch, username, onActionComplete, variant ('list' or 'popup')
 */
function MergeRequests(props) {
    const { branch, username, onActionComplete, variant = 'list' } = props;
    const [requests, setRequests] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [currentModalRequest, setCurrentModalRequest] = useState(null);
    const dismissedIdsRef = useRef(new Set());

    // Generalized fetch function to update the internal state
    const refreshData = useCallback(function () {
        if (!branch) return;

        const cleanBase = API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE;
        const url = cleanBase + '/pending_merges?branch=' + branch;

        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                const list = data.requests || [];
                setRequests(list);

                // If we are in popup mode, check for new requests to show as a modal
                if (variant === 'popup') {
                    const newReq = list.find(r => !dismissedIdsRef.current.has(r.id));
                    if (newReq) {
                        setShowModal(prev => {
                            if (!prev) {
                                setCurrentModalRequest(newReq);
                                return true;
                            }
                            return prev;
                        });
                    }
                }
            })
            .catch(function (err) {
                console.error("Monitoring error:", err);
            });
    }, [branch, variant]);

    // Setup polling interval for the component
    useEffect(function () {
        refreshData();
        const intervalTime = variant === 'popup' ? 15000 : 30000;
        const interval = setInterval(refreshData, intervalTime);
        return function () { clearInterval(interval); };
    }, [refreshData, variant]);

    // Perform an action (Accept/Reject) on a specific request
    function handleAction(requestId, action) {
        const url = (API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE) + '/negotiate_merge';

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_id: requestId,
                action: action,
                branch: branch
            })
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    if (variant === 'popup') {
                        setShowModal(false);
                        setCurrentModalRequest(null);
                    }
                    refreshData();
                    if (onActionComplete) onActionComplete();
                } else {
                    alert("Operation failed: " + data.message);
                }
            })
            .catch(function (err) {
                console.error("Action execution failed:", err);
            });
    }

    // Modal-specific dismissal logic
    function handleDismiss() {
        if (currentModalRequest) {
            dismissedIdsRef.current.add(currentModalRequest.id);
        }
        setShowModal(false);
    }

    // --- VARIANT 1: POPUP GLOBAL MODAL ---
    if (variant === 'popup') {
        if (!showModal || !currentModalRequest) return null;

        const sender = currentModalRequest.requestor_username || currentModalRequest.requestor_branch || "A faculty member";

        return (
            <div className="modal-overlay" style={{ zIndex: 9999 }}>
                <div className="modal-content animate-up" style={{ width: '450px' }}>
                    <h2 style={{ fontFamily: 'Garamond, serif', color: '#d9bc94', marginBottom: '15px' }}>
                        Merge Request Detected
                    </h2>
                    <p style={{ fontSize: '15px', lineHeight: '1.6', marginBottom: '20px' }}>
                        Greetings <strong>{username}</strong>, <strong>{sender}</strong> is requesting to merge <strong>{currentModalRequest.subject}</strong> during the <strong>{currentModalRequest.time_slot}</strong> slot.
                    </p>

                    {currentModalRequest.has_conflict && (
                        <div style={{
                            color: '#ef4444',
                            backgroundColor: '#ef44441a',
                            padding: '10px',
                            borderRadius: '6px',
                            fontSize: '13px',
                            marginBottom: '20px'
                        }}>
                            Scheduling conflict detected with your existing lectures.
                        </div>
                    )}

                    <div className="modal-actions">
                        <button className="button primary" onClick={function () { handleAction(currentModalRequest.id, 'accept'); }}>
                            ACCEPT
                        </button>
                        <button className="button secondary" onClick={handleDismiss}>
                            DECIDE LATER
                        </button>
                        <button className="button secondary" style={{ color: '#ef4444' }} onClick={function () { handleAction(currentModalRequest.id, 'reject'); }}>
                            DENY
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // --- VARIANT 2: SIDEBAR LIST VIEW ---
    return (
        <div className="dashboard-section animate-up" id="merge-requests-sidebar">
            <h3 className="class-alerts-title">
                MERGE REQUESTS
            </h3>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '30px' }}>
                <button
                    onClick={refreshData}
                    style={{
                        background: 'none',
                        border: '1px solid #d9bc9444',
                        color: '#d9bc94',
                        fontSize: '9px',
                        cursor: 'pointer',
                        padding: '4px 12px',
                        borderRadius: '10px'
                    }}
                >
                    REFRESH LIST
                </button>
                {requests.length > 0 && (
                    <button
                        onClick={function () {
                            if (!window.confirm("Confirm emptying all current merge requests?")) return;
                            const url = (API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE) + '/clear_merges?branch=' + branch;
                            fetch(url, { method: 'POST' })
                                .then(function (res) { return res.json(); })
                                .then(function (data) {
                                    if (data.success) {
                                        refreshData();
                                        if (onActionComplete) onActionComplete();
                                    }
                                })
                                .catch(err => console.error("Clear error:", err));
                        }}
                        style={{
                            background: 'none',
                            border: '1px solid #ef444444',
                            color: '#ef4444',
                            fontSize: '9px',
                            cursor: 'pointer',
                            padding: '4px 12px',
                            borderRadius: '10px'
                        }}
                    >
                        EMPTY LIST
                    </button>
                )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '40px' }}>
                {requests.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', opacity: 0.6, fontSize: '0.9rem', color: '#e8d4b8' }}>
                        No pending coordination requests found.
                    </div>
                ) : (
                    requests.map(function (req) {
                        return (
                            <div key={req.id} className="merge-request-item">
                                <div style={{ display: 'flex', flexDirection: 'column', marginBottom: '10px', gap: '15px', width: '100%' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span className="merge-value">{req.subject}</span>
                                        <span className="merge-label">Lecture</span>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
                                        <span className="merge-value">{req.time_slot}</span>
                                        <span className="merge-label">Schedule</span>
                                    </div>
                                </div>

                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <button
                                        onClick={function () { handleAction(req.id, 'accept'); }}
                                        className="buttonog"
                                        style={{ flex: 1, padding: '10px', fontSize: '0.7rem' }}
                                    >
                                        MERGE
                                    </button>
                                    <button
                                        onClick={function () { handleAction(req.id, 'reject'); }}
                                        className="buttonrev"
                                        style={{ flex: 1, padding: '10px', fontSize: '0.7rem', color: '#ef4444', borderColor: '#ef444444' }}
                                    >
                                        REJECT
                                    </button>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}

export default MergeRequests;
