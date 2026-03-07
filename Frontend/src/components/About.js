//https://chatgpt.com/g/g-tayJ50BT0-ai-code-humanizer
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Cpu,
    Network,
    Shield,
    Activity,
    Globe,
    Layers,
    Brain,
    Lock,
    Radio,
    Clock,
    Zap
} from "lucide-react";
import "../css/About.css";

// Multi-line terminal typing effect
const TypingText = function (props) {
    const text = props.text;
    const [displayedText, setDisplayedText] = useState("");
    useEffect(function () {
        let i = 0;
        const timer = setInterval(function () {
            setDisplayedText(text.slice(0, i));
            i++;
            if (i > text.length) clearInterval(timer);
        }, 20);
        return function () {
            clearInterval(timer);
        };
    }, [text]);
    return <p>{displayedText}<span className="terminal-cursor">_</span></p>;
};

const About = function () {
    const [activeNode, setActiveNode] = useState(null);

    const treeNodes = [
        { id: "root", label: "ADJUSTLE SYSTEM", icon: <Globe />, x: 52, y: 10, desc: "Smart classroom management for attendance, scheduling, and communication.", color: "#d9bc94", type: "ROOT" },

        // Level 1: 4 Pillars (Mathematically centered)
        { id: "privacy", label: "PRIVACY & SECURITY", icon: <Shield />, x: 16, y: 40, parent: "root", desc: "Ensuring student anonymity and institutional data integrity.", color: "#d9bc94", type: "SEC" },
        { id: "attendance", label: "ATTENDANCE INT.", icon: <Brain />, x: 40, y: 40, parent: "root", desc: "Intelligent real-time tracking and classroom strength monitoring.", color: "#d9bc94", type: "AI" },
        { id: "scheduling", label: "SMART SCHEDULING", icon: <Clock />, x: 64, y: 40, parent: "root", desc: "Dynamic adjustments and optimized resource allocation.", color: "#d9bc94", type: "SYNC" },
        { id: "comms", label: "COMM SYSTEM", icon: <Radio />, x: 88, y: 40, parent: "root", desc: "Instant synchronization bridge for faculty and students.", color: "#d9bc94", type: "NET" },

        // Level 2: Perfect 16-unit even spacing (8, 24, 40, 56, 72, 88)
        // 1. Privacy: 2 branches (Centered around 16)
        { id: "priv_prot", label: "PRIVACY PROTECTION", icon: <Lock />, x: 8, y: 82, parent: "privacy", desc: "Counts students without facial recognition, ensuring identity is not stored.", color: "#e8d4b8", type: "PROT" },
        { id: "priv_stor", label: "SECURE STORAGE", icon: <Cpu />, x: 24, y: 82, parent: "privacy", desc: "Academic data is encrypted and accessible only to authorized users.", color: "#e8d4b8", type: "DATA" },

        // 2. Attendance: 1 branch (Aligned at 40)
        { id: "att_live", label: "LIVE MONITORING", icon: <Activity />, x: 40, y: 82, parent: "attendance", desc: "Automatically tracks live classroom strength and provides accurate insights.", color: "#e8d4b8", type: "LIVE" },

        // 3. Scheduling: 2 branches (Centered around 64)
        { id: "sch_dynamic", label: "DYNAMIC ADJUSTS", icon: <Layers />, x: 56, y: 82, parent: "scheduling", desc: "Suggests merging or rescheduling classes based on attendance data.", color: "#e8d4b8", type: "GRID" },
        { id: "sch_resource", label: "RESOURCE OPTIM.", icon: <Zap />, x: 72, y: 82, parent: "scheduling", desc: "Helps use classrooms and faculty time efficiently for the institution.", color: "#e8d4b8", type: "OPT" },

        // 4. Comms: 1 branch (Aligned at 88)
        { id: "com_sync", label: "REAL-TIME SYNC", icon: <Network />, x: 88, y: 82, parent: "comms", desc: "Ensures everyone stays informed through instant alerts and sub-100ms synchronization.", color: "#e8d4b8", type: "SYNC" }
    ];

    const getPath = function (p1, p2) {
        const midY = (p1.y + p2.y) / 2;
        return "M " + p1.x + "," + p1.y + " C " + p1.x + "," + midY + " " + p2.x + "," + midY + " " + p2.x + "," + p2.y;
    };

    return (
        <div className="cyber-about-container">
            {/* Subtle Miniscule Floating Dust Animation */}
            <div className="dust-layer">
                {[...Array(150)].map(function (_, i) {
                    const randomX = Math.random() * 100;
                    const randomY = Math.random() * 100;
                    const randomSize = Math.random() * 1 + 0.8; // Tiny but visible: 0.8px to 1.8px
                    const randomDur = Math.random() * 20 + 10;
                    const randomDelay = Math.random() * -30;

                    return (
                        <motion.div
                            key={"micro-dust-" + i}
                            className="tiny-dust"
                            style={{
                                left: randomX + "%",
                                top: randomY + "%",
                                width: randomSize + "px",
                                height: randomSize + "px"
                            }}
                            animate={{
                                y: [0, -80, 0],
                                x: [0, 40, 0],
                                opacity: [0, 0.8, 0] // Brighter peak for visibility
                            }}
                            transition={{
                                duration: randomDur,
                                repeat: Infinity,
                                delay: randomDelay,
                                ease: "linear"
                            }}
                        />
                    );
                })}
            </div>

            <div className="cyber-stage">
                <svg className="cyber-svg-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
                    <defs>
                        <filter id="glow">
                            <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
                            <feMerge>
                                <feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>
                    {treeNodes.map(function (node) {
                        if (node.parent) {
                            const p = treeNodes.find(function (n) { return n.id === node.parent; });
                            const active = activeNode === node.id || activeNode === p.id;
                            return (
                                <g key={"path-" + node.id}>
                                    <path d={getPath(p, node)} className={"path-base " + (active ? 'active' : '')} />
                                    {active && (
                                        <motion.circle r="0.6" fill="#d9bc94">
                                            <animateMotion path={getPath(p, node)} dur="1.5s" repeatCount="indefinite" />
                                        </motion.circle>
                                    )}
                                </g>
                            );
                        }
                        return null;
                    })}
                </svg>

                {treeNodes.map(function (node) {
                    return (
                        <motion.div
                            key={node.id}
                            className={"cyber-node " + (activeNode === node.id ? 'active' : '')}
                            style={{ left: node.x + "%", top: node.y + "%" }}
                            onMouseEnter={function () { setActiveNode(node.id); }}
                            onMouseLeave={function () { setActiveNode(null); }}
                        >
                            <div className="node-glitch-border"></div>
                            <div className="node-content">
                                <div className="node-icon-bin">{node.icon}</div>
                                <div className="node-label-stack">
                                    <span className="node-tag">{node.type}</span>
                                    <span className="node-name">{node.label}</span>
                                </div>
                            </div>

                            <AnimatePresence>
                                {activeNode === node.id && (
                                    <motion.div
                                        className={`terminal-popover 
                                            ${node.y > 60 ? "top-position" : "bottom-position"}
                                            ${node.x > 80 ? "right-align" : node.x < 20 ? "left-align" : "center-align"}
                                        `}
                                        initial={{ opacity: 0, scale: 0.9, y: 10 }}
                                        animate={{ opacity: 1, scale: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.9, y: 10 }}
                                    >
                                        <div className="terminal-header">
                                            <span>TERMINAL_OUTPUT // {node.id.toUpperCase()}</span>
                                            <div className="terminal-dots"><span></span><span></span><span></span></div>
                                        </div>
                                        <TypingText text={node.desc} />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    );
                })}
            </div>


        </div>
    );
};


export default About;
