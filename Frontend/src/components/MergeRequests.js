import React, { useState, useEffect, useCallback, useRef } from 'react';

import { API_BASE } from "../api_config";

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
        const url = cleanBase + '/pending_merges?branch=' + branch + '&_t=' + Date.now();

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
                        Merge Request
                    </h2>
                    {currentModalRequest.status === 'fallback_pending' ? (
                        <>
                            <p style={{ fontSize: '15px', lineHeight: '1.6', marginBottom: '20px' }}>
                                Greetings <strong>{username}</strong>, your proposed merge for <strong>{currentModalRequest.subject}</strong> was declined. Would you prefer shifting it 1 hour later?
                            </p>
                            <div className="modal-actions">
                                <button className="button primary" onClick={function () { handleAction(currentModalRequest.id, 'fallback_delay'); }}>
                                    Shift to an hour later
                                </button>
                                <button className="button secondary" onClick={function () { handleAction(currentModalRequest.id, 'fallback_leave'); }}>
                                    Remain on schedule
                                </button>
                            </div>
                        </>
                    ) : (
                        <>
                            <p style={{ fontSize: '15px', lineHeight: '1.6', marginBottom: '20px' }}>
                                {(function () {
                                    const expanded = (currentModalRequest.subject === 'AI' || currentModalRequest.subject === 'Artificial Intelligence') ? 'Artificial Intelligence' : 
                                                     (currentModalRequest.subject === 'IoT' || currentModalRequest.subject === 'Internet of Things') ? 'Internet of Things' : 
                                                     currentModalRequest.subject;
                                    return (
                                        <>Greetings <strong>{username}</strong>, <strong>{sender}</strong> is requesting to merge <strong>{expanded}</strong> during the <strong>{currentModalRequest.time_slot}</strong> slot.</>
                                    );
                                })()}
                            </p>

                            {currentModalRequest.has_conflict && (
                                <div style={{
                                    color: '#ef4444',
                                    backgroundColor: '#ef44441a',
                                    padding: '10px',
                                    borderRadius: '6px',
                                    fontSize: '13px',
                                    marginBottom: '20px',
                                    border: '1px solid #ef444433'
                                }}>
                                    {(function() {
                                        const expanded = (currentModalRequest.conflict_details === 'AI' || currentModalRequest.conflict_details === 'Artificial Intelligence') ? 'Artificial Intelligence' : 
                                                         (currentModalRequest.conflict_details === 'IoT' || currentModalRequest.conflict_details === 'Internet of Things') ? 'Internet of Things' : 
                                                         currentModalRequest.conflict_details;
                                        return (
                                            <><strong>Conflict Alert:</strong> You already have <strong>{expanded}</strong> at {currentModalRequest.time_slot}. Please DENY this request.</>
                                        );
                                    })()}
                                </div>
                            )}

                            <div className="modal-actions">
                                <button 
                                    className="button primary" 
                                    onClick={function () { handleAction(currentModalRequest.id, 'accept'); }}
                                    disabled={currentModalRequest.has_conflict}
                                    style={{ opacity: currentModalRequest.has_conflict ? 0.5 : 1, cursor: currentModalRequest.has_conflict ? 'not-allowed' : 'pointer' }}
                                >
                                    {currentModalRequest.has_conflict ? 'UNAVAILABLE' : 'ACCEPT'}
                                </button>
                                <button className="button secondary" onClick={handleDismiss}>
                                    DECIDE LATER
                                </button>
                                <button className="button secondary" style={{ color: '#ef4444' }} onClick={function () { handleAction(currentModalRequest.id, 'reject'); }}>
                                    DENY
                                </button>
                            </div>
                        </>
                    )}
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
                        const displayName = (req.subject === 'AI' || req.subject === 'Artificial Intelligence') ? 'Artificial Intelligence' : 
                                            (req.subject === 'IoT' || req.subject === 'Internet of Things') ? 'Internet of Things' : 
                                            req.subject;
                        return (
                            <div key={req.id} className="merge-request-item">
                                <div style={{ display: 'flex', flexDirection: 'column', marginBottom: '10px', gap: '15px', width: '100%' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span className="merge-value">{displayName}</span>
                                        <span className="merge-label">Lecture</span>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
                                        <span className="merge-value">{req.time_slot}</span>
                                        <span className="merge-label">Schedule</span>
                                    </div>
                                </div>

                                {req.status === 'fallback_pending' ? (
                                    <>
                                        <div style={{ display: 'flex', gap: '12px' }}>
                                            <button
                                                onClick={function () { handleAction(req.id, 'fallback_delay'); }}
                                                className="buttonog"
                                                style={{ flex: 1, padding: '10px', fontSize: '0.7rem' }}
                                            >
                                                Shift to an hour later
                                            </button>
                                            <button
                                                onClick={function () { handleAction(req.id, 'fallback_leave'); }}
                                                className="buttonrev"
                                                style={{ flex: 1, padding: '10px', fontSize: '0.7rem', color: '#ef4444', borderColor: '#ef444444' }}
                                            >
                                                Remain on schedule
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        {req.has_conflict && (
                                            <div style={{
                                                color: '#ef4444',
                                                fontSize: '11px',
                                                marginBottom: '10px',
                                                textAlign: 'left'
                                            }}>
                                                {(function() {
                                                    const expanded = (req.conflict_details === 'AI' || req.conflict_details === 'Artificial Intelligence') ? 'Artificial Intelligence' : 
                                                                     (req.conflict_details === 'IoT' || req.conflict_details === 'Internet of Things') ? 'Internet of Things' : 
                                                                     req.conflict_details;
                                                    return <>Conflict with <strong>{expanded}</strong></>;
                                                })()}
                                            </div>
                                        )}
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
                                            <button
                                                onClick={function () { handleAction(req.id, 'accept'); }}
                                                className="buttonog"
                                                style={{ 
                                                    width: '100%', 
                                                    padding: '10px', 
                                                    fontSize: '0.7rem',
                                                    opacity: req.has_conflict ? 0.5 : 1,
                                                    cursor: req.has_conflict ? 'not-allowed' : 'pointer'
                                                }}
                                                disabled={req.has_conflict}
                                            >
                                                {req.has_conflict ? 'BLOCKED' : 'MERGE'}
                                            </button>
                                            <button
                                                onClick={function () { handleAction(req.id, 'reject'); }}
                                                className="buttonrev"
                                                style={{ width: '100%', padding: '10px', fontSize: '0.7rem', color: '#ef4444', borderColor: '#ef444444' }}
                                            >
                                                REJECT
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}

export default MergeRequests;
