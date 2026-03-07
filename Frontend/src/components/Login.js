import React, { useState, useEffect } from "react";
import { Check, Eye, EyeOff } from "lucide-react";
import Timetable from "./Timetable";
import "../css/Login.css";

function PasswordRequirement({ isValid, successText, failText }) {
  let containerClass = "requirement";
  if (isValid) {
    containerClass = "requirement valid";
  }

  let icon = <div className="req-icon-circle" />;
  if (isValid) {
    icon = <Check size={14} color="#4ade80" />;
  }

  let text = failText;
  if (isValid) {
    text = successText;
  }

  return (
    <div className={containerClass}>
      {icon} {text}
    </div>
  );
}

function Login({ loggedIn, setLoggedIn, setRole, setBranch, onNavigate, setUsername: setGlobalUsername }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [reschedule, setReschedule] = useState([]);
  const [selectedRole, setSelectedRole] = useState("student");

  const [showPassword, setShowPassword] = useState(false);

  // Binary Rain Effect
  useEffect(() => {
    if (loggedIn) return;

    const canvas = document.getElementById("binary-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const chars = "01".split("");
    const fontSize = 16;
    const columns = canvas.width / fontSize;
    const drops = [];

    for (let x = 0; x < columns; x++) {
      drops[x] = 1;
    }

    function draw() {
      ctx.fillStyle = "#0000000d";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.fillStyle = "#d9bc944c"; // subtle gold
      ctx.font = fontSize + "px monospace";

      for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);

        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }
    }

    const intervalId = setInterval(draw, 40);

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", handleResize);

    return () => {
      clearInterval(intervalId);
      window.removeEventListener("resize", handleResize);
    };
  }, [loggedIn]);

  useEffect(() => {
    if (loggedIn) {
      // Fetch reschedule data
      fetch("http://127.0.0.1:8000/reschedule")
        .then(res => res.json())
        .then(data => setReschedule(data.classes));

    }
  }, [loggedIn]);

  function validatePassword(pass) {
    // 1 uppercase, 1 lowercase, 1 number, 1 special char, min 5 chars
    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{5,}$/;
    return regex.test(pass);
  }

  function handleLogin() {
    if (!validatePassword(password)) {
      setError("Password must contain 1 uppercase, 1 lowercase, 1 number, 1 special char, and be at least 5 chars long.");
      return;
    }

    fetch("http://127.0.0.1:8000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, role: selectedRole })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setLoggedIn(true);
          // Set role and branch based on backend response, not hardcoded selection mapping
          if (data.role && setRole) setRole(data.role);
          if (data.branch && setBranch) setBranch(data.branch);
          if (setGlobalUsername) setGlobalUsername(username);

          setError("");
          if (onNavigate) {
            onNavigate("timetable");
          }
        } else {
          setError(data.message || "Invalid username or password");
        }
      })
      .catch(err => {
        console.error("Login request failed:", err);
        setError("Failed to connect to authentication server.");
      });
  }

  if (loggedIn) {
    return (
      <div className="page-container wide">

        <div className="dashboard-grid layout-fix">
          <div className="dashboard-section timetable-section">
            <h2>{username ? username.toUpperCase() + "'S " : ""}TIMETABLE</h2>
            <Timetable rescheduleData={reschedule} />
          </div>

          <div className="dashboard-section reschedule-section">
            <h2>UPDATES</h2>
            <div className="list">
              {reschedule.map((r, i) => (
                <div className="list-item" key={i}>
                  <span className="subject">{r.subject}</span>
                  <span className={r.status === "Rescheduled" ? "status alert" : "status"}>{r.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <canvas id="binary-canvas" className="matrix-canvas"></canvas>
      <div className="scan-layer"></div>
      <div className="levitation-wrapper">
        <div className="login-card">
          <h2>LOGIN</h2>

          <div className="role-toggle" style={{ marginBottom: '15px' }}>
            <button className={(() => { if (selectedRole === "teacher") return "active"; return ""; })()} type="button" onClick={() => setSelectedRole("teacher")}>Teacher</button>
            <button className={(() => { if (selectedRole === "student") return "active"; return ""; })()} type="button" onClick={() => setSelectedRole("student")}>Student</button>
          </div>

          <div className="login-section">
            <label>USERNAME</label>
            <input
              value={username}
              onChange={e => setUsername(e.target.value)}
            />
          </div>

          <div className="login-section">
            <label>PASSWORD</label>
            <div className="password-box">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
              <span onClick={() => setShowPassword(!showPassword)}>
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </span>
            </div>
          </div>

          {/* Password Requirements Checklist */}
          <div className="password-requirements">
            <PasswordRequirement
              isValid={/[A-Z]/.test(password)}
              successText="1 Uppercase entered"
              failText="Please enter 1 uppercase"
            />
            <PasswordRequirement
              isValid={/[a-z]/.test(password)}
              successText="1 Lowercase entered"
              failText="Please enter 1 lowercase"
            />
            <PasswordRequirement
              isValid={/\d/.test(password)}
              successText="1 Number entered"
              failText="Please enter 1 number"
            />
            <PasswordRequirement
              isValid={password.length >= 5}
              successText="5 Characters entered"
              failText="Please enter 5 characters"
            />
            <PasswordRequirement
              isValid={/[@$!%*?&]/.test(password)}
              successText="1 Special Character entered"
              failText="Please enter 1 special character"
            />
          </div>

          {error && <p className="login-error">{error}</p>}
          <button className="login-btn" onClick={handleLogin}>✓ LOGIN</button>
        </div>
      </div>
    </div>
  );
}

export default Login;
