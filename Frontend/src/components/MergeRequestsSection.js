import React, { useState, useEffect, useCallback } from 'react';

// This component displays any pending merge requests for the teacher's branch
function MergeRequestsSection(props) {
    const { branch, onActionComplete } = props;
    const [requests, setRequests] = useState([]);

    //Wrapped in useCallback to fix ESLint dependency warnings
    const fetchRequests = useCallback(function () {
        const base = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';
        const cleanBase = base.endsWith('/') ? base.slice(0, -1) : base;
        const url = cleanBase + '/pending_merges?branch=' + branch;

        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                setRequests(data.requests || []);
            })
            .catch(function (err) {
                console.error("Error fetching merges:", err);
            });
    }, [branch]);

    // Load requests when the branch changes, component mounts, or on a timer
    useEffect(function () {
        if (!branch) return;
        fetchRequests();
        const interval = setInterval(fetchRequests, 30000);
        return function () {
            clearInterval(interval);
        };
    }, [branch, fetchRequests]);

    // Function to handle accepting or rejecting a merge
    function handleAction(requestId, action) {
        const url = (process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000') + '/negotiate_merge';

        const body = {
            request_id: requestId,
            action: action,
            branch: branch
        };

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    fetchRequests();
                    if (onActionComplete) onActionComplete();
                } else {
                    alert("Action failed: " + data.message);
                }
            })
            .catch(function (err) {
                console.error("Error performing action:", err);
            });
    }

    return (
        <div className="dashboard-section animate-up" id="merge-requests-sidebar">
            <h3 className="class-alerts-title">
                MERGE REQUESTS
            </h3>

            <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                <button
                    onClick={fetchRequests}
                    style={{
                        background: 'none',
                        border: '1px solid #d9bc9444',
                        color: '#d9bc94',
                        fontSize: '9px',
                        cursor: 'pointer',
                        padding: '2px 10px',
                        borderRadius: '10px'
                    }}
                >
                    REFRESH LIST
                </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '40px' }}>
                {requests.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', opacity: 0.6, fontSize: '0.9rem', color: '#e8d4b8' }}>
                        No pending merge requests at the moment.
                    </div>
                ) : (
                    requests.map(function (req, index) {
                        return (
                            <div key={req.id} className="merge-request-item">
                                <div style={{ display: 'flex', flexDirection: 'column', marginBottom: '10px', gap: '15px', width: '100%' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span className="merge-value">{req.subject}</span>
                                        <span className="merge-label">Subject</span>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left' }}>
                                        <span className="merge-value">{req.time_slot}</span>
                                        <span className="merge-label">Time</span>
                                    </div>
                                </div>

                                {/* Action Row */}
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

export default MergeRequestsSection;
