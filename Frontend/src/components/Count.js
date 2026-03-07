/* ---- Imports ---- */
import React, { useMemo } from "react";
import UploadImage from "./UploadImage";
import "../css/Count.css";

function Count(props) {
    const onNavigate = props.onNavigate;

    // Generate stable random numbers for background animation
    const animNumbers = useMemo(() => {
        return Array.from({ length: 40 }, (_, i) => ({
            id: i,
            val: Math.floor(Math.random() * 10),
            style: {
                top: Math.random() * 100 + "vh",
                left: Math.random() * -20 + "vw", // Start slightly offscreen or scattered
                fontSize: (Math.random() * 40 + 20) + "px",
                animationDuration: (Math.random() * 10 + 10) + "s", // 10-20s duration
                animationDelay: (Math.random() * 10) + "s",
            }
        }));
    }, []);

    return (
        <div className="page-container wide count-page-wrapper">
            <div className="count-bg-animation">
                {animNumbers.map((n) => (
                    <span key={n.id} style={n.style} className="floating-number">
                        {n.val}
                    </span>
                ))}
            </div>
            <UploadImage onNavigate={onNavigate} branch={props.branch} username={props.username} />
        </div>
    );
}

export default Count;
