import React, { useState, useEffect } from "react";
import { Bell } from "lucide-react";

const API_BASE = process.env.REACT_APP_API_URL || "";

function Notifications(props) {
    const { role = "student", branch = "BCA" } = props;
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Fetch notifications for the specific branch
        fetch(API_BASE + "/notifications?branch=" + branch)
            .then(res => res.json())
            .then(data => {
                const fetchedNotifs = data.notifications || [];
                const filtered = fetchedNotifs.filter(n => role === 'teacher' || (n.message && n.message.trim() !== ""));
                setNotifications(filtered);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch notifications:", err);
                setLoading(false);
            });
    }, [branch, role]);

    const formatDate = (dateStr) => {
        try {
            const date = new Date(dateStr);
            return `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
        } catch (e) {
            return dateStr;
        }
    };

    return (
        <div className="page-container wide">
            <div className="notification-container">
                <div className="notification-header">
                    <Bell size={32} color="#d9bc94" className="notif-header-icon" />
                    <h2>NOTIFICATIONS</h2>
                </div>

                <div className="notification-list">
                    {loading ? (
                        <div className="no-notifications">Loading...</div>
                    ) : notifications.length > 0 ? (
                        notifications.map((n, i) => {
                            const displayMessage = (role === 'teacher' && n.teacher_message) ? n.teacher_message : n.message;
                            return (
                                <div className="list-notification-card" key={i} style={{ animationDelay: `${i * 0.1}s` }}>
                                    <div className="notification-content-header">
                                        <span className="notif-category-badge">
                                            {n.type.replace(/_/g, " ").toUpperCase()}
                                        </span>
                                        <span className="notif-date-stamp">
                                            {formatDate(n.created_at)}
                                        </span>
                                    </div>
                                    <h3 className="notification-title">{n.title}</h3>
                                    <p className="notification-message">{displayMessage}</p>
                                </div>
                            );
                        })
                    ) : (
                        <div className="no-notifications">
                            No notifications available for your branch
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default Notifications;
