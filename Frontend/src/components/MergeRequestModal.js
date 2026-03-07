import React, { useState, useEffect, useRef } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

// This modal pops up to notify teachers about new merge requests while they are using the app
function MergeRequestModal(props) {
    const { branch, username } = props;
    const [request, setRequest] = useState(null);
    const [show, setShow] = useState(false);
    const dismissedIdsRef = useRef(new Set());

    // Logic to check for pending merges that the teacher hasn't seen yet
    useEffect(function () {
        if (!branch) return;

        function checkMerges() {
            // console.log("Checking merges for branch:", branch);
            const url = API_BASE + '/pending_merges?branch=' + branch;

            fetch(url)
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.requests) {
                        // console.log(`Found ${data.requests.length} total pending requests for ${branch}`);
                        const newReq = data.requests.find(r => !dismissedIdsRef.current.has(r.id));
                        if (newReq) {
                            // console.log("Showing new merge request popup for:", newReq.subject);
                            setShow(prevShow => {
                                if (!prevShow) {
                                    setRequest(newReq);
                                    return true;
                                }
                                return prevShow;
                            });
                        }
                    }
                })
                .catch(function (err) {
                    console.error("Popup check failed:", err);
                });
        }

        checkMerges();
        const interval = setInterval(checkMerges, 15000); // 15s poll for faster feedback
        return function () { clearInterval(interval); };
    }, [branch, username]); // eslint-disable-line react-hooks/exhaustive-deps

    // Function to handle the teacher's decision from the modal
    function handleDecision(action) {
        if (!request) return;

        const url = API_BASE + '/negotiate_merge';
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_id: request.id,
                action: action,
                branch: branch
            })
        })
            .then(function (res) { return res.json(); })
            .then(function () {
                setShow(false);
                setRequest(null);
            })
            .catch(function (err) {
                console.error("Action error:", err);
                setShow(false);
            });
    }

    function handleDecideLater() {
        if (request) {
            dismissedIdsRef.current.add(request.id);
        }
        setShow(false);
    }

    if (!show || !request) return null;

    const requestor = request.requestor_username || request.requestor_branch || "A teacher";

    return (
        <div className="modal-overlay" style={{ zIndex: 9999 }}>
            <div className="modal-content animate-up" style={{ width: '450px' }}>
                <h2 style={{ fontFamily: 'Garamond, serif', color: '#d9bc94', marginBottom: '15px' }}>
                    Merge Request
                </h2>
                <p style={{ fontSize: '15px', lineHeight: '1.6', marginBottom: '20px' }}>
                    Hello <strong>{username}</strong>, <strong>{requestor}</strong> wants to merge <strong>{request.subject}</strong> at <strong>{request.time_slot}</strong>
                </p>

                {request.has_conflict && (
                    <div style={{
                        color: '#ef4444',
                        backgroundColor: '#ef44441a',
                        padding: '10px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        marginBottom: '20px'
                    }}>
                        Note: You already have a class scheduled at this time.
                    </div>
                )}

                <div className="modal-actions">
                    <button className="button primary" onClick={function () { handleDecision('accept'); }}>
                        ACCEPT
                    </button>
                    <button className="button secondary" onClick={handleDecideLater}>
                        DECIDE LATER
                    </button>
                    <button className="button secondary" style={{ color: '#ef4444' }} onClick={function () { handleDecision('reject'); }}>
                        DENY
                    </button>
                </div>
            </div>
        </div>
    );
}

export default MergeRequestModal;
