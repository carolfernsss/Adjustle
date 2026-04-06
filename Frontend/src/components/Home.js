import React, { useState, useEffect } from "react";
import { Bell, Calendar, TrendingUp } from "lucide-react";
import "../css/Home.css";
import { API_BASE } from "../api_config";

const fullText = "ADJUSTLE";
const fullText2 = "THE SCHEDULE THAT FITS YOU";

const Home = function (props) {
    const onNavigate = props.onNavigate;
    const role = props.role;
    const loggedIn = props.loggedIn;
    const branch = props.branch || sessionStorage.getItem("adjustle_branch") || "BCA";
    const [notifications, setNotifications] = useState([]);
    const [displayText, setDisplayText] = useState("");
    const [displayTagline, setDisplayTagline] = useState("");
    const [showNotifications, setShowNotifications] = useState(false);

    useEffect(function () {
        let heroInterval = null;
        let taglineTimeout = null;
        let taglineInterval = null;

        let heroIdx = 0;
        setDisplayText("");
        heroInterval = setInterval(function () {
            if (heroIdx <= fullText.length) {
                setDisplayText(fullText.slice(0, heroIdx));
                heroIdx = heroIdx + 1;
            } else {
                clearInterval(heroInterval);
            }
        }, 150);

        taglineTimeout = setTimeout(function () {
            let tagIdx = 0;
            setDisplayTagline("");
            taglineInterval = setInterval(function () {
                if (tagIdx <= fullText2.length) {
                    setDisplayTagline(fullText2.slice(0, tagIdx));
                    tagIdx = tagIdx + 1;
                } else {
                    clearInterval(taglineInterval);
                    setTimeout(function () {
                        setShowNotifications(true);
                    }, 800);
                }
            }, 60);
        }, 2000);

        return function () {
            if (heroInterval) clearInterval(heroInterval);
            if (taglineTimeout) clearTimeout(taglineTimeout);
            if (taglineInterval) clearInterval(taglineInterval);
        };
    }, []);

    useEffect(function () {
        fetch(API_BASE + "/notifications?branch=" + branch)
            .then(function (res) {
                return res.json();
            })
            .then(function (data) {
                let notifs = [];
                if (Array.isArray(data)) {
                    notifs = data;
                } else {
                    notifs = data.notifications || [];
                }
                if (notifs.length > 0) {
                    setNotifications(notifs);
                } else {
                    setNotifications([
                        {
                            id: 1,
                            type: 'system',
                            title: 'Inbox Empty',
                            message: 'No recent schedule changes or updates to display.',
                            created_at: new Date().toISOString()
                        }
                    ]);
                }
            })
            .catch(function (err) {
                setNotifications([
                    {
                        id: 1,
                        type: 'system',
                        title: 'Welcome to Adjustle',
                        message: 'Notifications will appear here.',
                        created_at: new Date().toISOString()
                    }
                ]);
            });
    }, [branch]);

    const getIcon = function (type) {
        if (type === 'schedule_change') {
            return <Calendar size={18} />;
        }
        return <TrendingUp size={18} />;
    };

    const processedNotifs = notifications.map(function(notif) {
        let displayMessage = "";
        if (role === 'teacher') {
            if ((!notif.teacher_message || notif.teacher_message.trim() === "") && notif.type !== 'merge_request' && notif.type !== 'merge_proposal' && notif.type !== 'test_period') {
                if (!notif.message && notif.type !== 'system') return null;
                displayMessage = notif.message || "";
            } else {
                displayMessage = notif.teacher_message || notif.message || "";
            }
        } else {
            if (!notif.message || notif.message.trim() === "" || notif.type === 'merge_request' || notif.type === 'merge_proposal' || notif.type === 'test_period') {
                return null;
            }
            // Prevents students from seeing any "Merge Declined" and "Merge Request" alerts 
            if (notif.title && (notif.title.toLowerCase().includes("declined") || notif.title.toLowerCase().includes("awaiting"))) {
                return null;
            }
            if (notif.message && notif.message.toLowerCase().includes("awaiting teacher")) {
                return null;
            }
            displayMessage = notif.message;
        }
        if (!displayMessage) return null;
        return { ...notif, displayMessage };
    }).filter(Boolean);

    const carouselItems = processedNotifs.length > 0
        ? [...processedNotifs, ...processedNotifs, ...processedNotifs, ...processedNotifs, ...processedNotifs, ...processedNotifs,
        ...processedNotifs, ...processedNotifs]
        : [];

    return (
        <section className="home-page">
            <video
                autoPlay
                loop={true}
                muted
                playsInline
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    zIndex: -1,
                    opacity: 0.2
                }}
            >
                <source src="/Website_Screenshots_to_Professional_Video.mp4" type="video/mp4" />
            </video>
            <div
                className={`home-bell ${showNotifications ? 'visible' : ''}`}
                onClick={function () {
                    if (loggedIn) {
                        onNavigate('notifications');
                    } else {
                        onNavigate('login');
                    }
                }}
            >
                <Bell size={24} color="#d9bc94" />
                {notifications.length > 0 && <span className="bell-badge"></span>}
            </div>

            <div
                className="hero-text"
                style={{
                    opacity: displayText ? 1 : 0,
                    transform: displayText ? 'translateY(0)' : 'translateY(20px)',
                    transition: 'all 0.6s ease-out'
                }}
            >
                <h1>
                    {displayText}
                    <span className="cursor">|</span>
                </h1>
                <p className="tagline">{displayTagline}</p>
            </div>

            <div
                className={`notifications-container ${showNotifications ? 'visible' : ''}`}
                style={{
                    opacity: showNotifications ? 1 : 0,
                    transform: showNotifications ? 'translateY(0)' : 'translateY(20px)',
                    transition: 'all 0.6s ease-out',
                    marginTop: '60px'
                }}
            >
                <div className="section-divider" onClick={function () { onNavigate('notifications'); }}>
                    <span className="divider-line"></span>
                    <h2 className="section-title">LATEST UPDATES</h2>
                    <span className="divider-line"></span>
                </div>

                <div className="carousel-container" style={{ overflowX: 'hidden', width: '100%', padding: '20px 0' }}>
                    {loggedIn ? (
                        carouselItems.length > 0 ? (
                            <div className="carousel-wrapper" style={{
                                display: 'flex',
                                animationName: 'carousel-scroll',
                                animationDuration: '180s',
                                animationTimingFunction: 'linear',
                                animationIterationCount: 'infinite',
                                width: 'max-content',
                            }}>
                                {carouselItems.map(function (notif, i) {
                                    const typeLabel = notif.type.replace('_', ' ');
                                    const timeString = new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                                    return (
                                        <div
                                            key={i}
                                            className="notification-card"
                                            style={{ minWidth: '350px', maxWidth: '350px', marginRight: '20px' }}
                                            onClick={function (e) {
                                                e.stopPropagation();
                                                onNavigate('notifications');
                                            }}
                                        >
                                            <div className="notif-header" style={{
                                                display: 'flex', justifyContent:
                                                    'space-between', marginBottom: '10px'
                                            }}>
                                                <span className="notif-type" style={{
                                                    display: 'flex', alignItems:
                                                        'center', gap: '5px', fontSize: '0.8rem', color: '#d9bc94'
                                                }}>
                                                    {getIcon(notif.type)}
                                                    {typeLabel}
                                                </span>
                                                <span className="notif-time" style={{ fontSize: '0.8rem', opacity: 0.6 }}>{timeString}</span>
                                            </div>
                                            <h3 className="notif-title" style={{ fontSize: '1.1rem', color: '#e8d4b8', marginBottom: '8px' }}>{notif.title}</h3>
                                            <p className="notif-msg" style={{ fontSize: '0.9rem', opacity: 0.8, lineHeight: '1.5' }}>{notif.displayMessage}</p>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div
                                className="restricted-notifs-placeholder"
                                style={{
                                    color: '#d9bc94', opacity: 0.6, textAlign: 'center', padding: '40px', cursor: 'pointer',
                                    letterSpacing: '4px', textTransform: 'uppercase', fontSize: '0.85rem',
                                    border: '1px solid #d9bc941a', borderRadius: '24px',
                                    background: '#1d140d66', width: '100%', maxWidth: '800px', margin: '0 auto',
                                    fontFamily: 'Garamond, serif'
                                }}
                            >
                                No new notifications
                            </div>
                        )
                    ) : (
                        <div
                            className="restricted-notifs-placeholder"
                            style={{
                                color: '#d9bc94', opacity: 0.6, textAlign: 'center', padding: '40px', cursor: 'pointer',
                                letterSpacing: '4px', textTransform: 'uppercase', fontSize: '0.85rem',
                                border: '1px solid #d9bc941a', borderRadius: '24px',
                                background: '#1d140d66', width: '100%', maxWidth: '800px', margin: '0 auto',
                                fontFamily: 'Garamond, serif'
                            }}
                            onClick={function () { onNavigate('login'); }}
                        >
                            Notifications will be displayed once logged in
                        </div>
                    )}
                </div>
            </div>
        </section>
    );
};

export default Home;
