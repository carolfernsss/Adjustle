import React, { useState, useEffect } from "react";
import { Bell, Calendar, TrendingUp } from "lucide-react";
import "../css/Home.css";
import { API_BASE } from "../api_config";

const fullText = "ADJUSTLE";
const fullText2 = "THE SCHEDULE THAT FITS YOU";
/* ---- Home Page Component ---- */
const Home = function (props) {
    const onNavigate = props.onNavigate;
    const role = props.role;
    const loggedIn = props.loggedIn;
    const [notifications, setNotifications] = useState([]);
    const [displayText, setDisplayText] = useState("");
    const [displayTagline, setDisplayTagline] = useState("");
    const [showNotifications, setShowNotifications] = useState(false);

    useEffect(function () {
        let heroInterval = null;
        let taglineTimeout = null;
        let taglineInterval = null;

        // Hero Animation
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

        // Tagline Animation
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
        fetch(API_BASE + "/notifications")
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
                            type: 'schedule_change',
                            title: 'Power BI Rescheduled',
                            message: 'Power BI class has been moved earlier on Friday.',
                            created_at: new Date().toISOString()
                        },
                        {
                            id: 2,
                            type: 'schedule_change',
                            title: 'Software Engineering Update',
                            message: 'Software Engineering class timing has been adjusted.',
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
    }, []);

    const getIcon = function (type) {
        if (type === 'schedule_change') {
            return <Calendar size={18} />;
        }
        return <TrendingUp size={18} />;
    };

    /* ---- Carousel Logic ---- */
    const carouselItems = notifications.length > 0
        ? [...notifications, ...notifications, ...notifications, ...notifications, ...notifications, ...notifications, 
            ...notifications, ...notifications]
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
                    opacity: 0.2 // subtle background
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
                        <div className="carousel-wrapper" style={{
                            display: 'flex',
                            animationName: 'carousel-scroll',
                            animationDuration: '60s',
                            animationTimingFunction: 'linear',
                            animationIterationCount: 'infinite',
                            width: 'max-content',
                        }}>
                            {carouselItems.map(function (notif, i) {
                                if (role !== 'teacher' && (!notif.message || notif.message.trim() === "")) {
                                    return null;
                                }
                                let displayMessage = notif.message;
                                if (role === 'teacher' && notif.teacher_message) {
                                    displayMessage = notif.teacher_message;
                                }
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
                                        <div className="notif-header" style={{ display: 'flex', justifyContent: 
                                            'space-between', marginBottom: '10px' }}>
                                            <span className="notif-type" style={{ display: 'flex', alignItems: 
                                                'center', gap: '5px', fontSize: '0.8rem', color: '#d9bc94' }}>
                                                {getIcon(notif.type)}
                                                {typeLabel}
                                            </span>
                                            <span className="notif-time" style={{ fontSize: '0.8rem', opacity: 0.6 }}>{timeString}</span>
                                        </div>
                                        <h3 className="notif-title" style={{ fontSize: '1.1rem', color: '#e8d4b8', marginBottom: '8px' }}>{notif.title}</h3>
                                        <p className="notif-msg" style={{ fontSize: '0.9rem', opacity: 0.8, lineHeight: '1.5' }}>{displayMessage}</p>
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
