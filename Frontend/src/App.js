import { useState, useEffect, useCallback, useRef } from "react";
import "./css/App.css";
import Home from "./components/Home";
import Login from "./components/Login";
import Count from "./components/Count";
import About from "./components/About";
import Notifications from "./components/Notifications";
import Timetable from "./components/Timetable";
import ClassAlerts from "./components/ClassAlerts";
import InteractiveGuide from "./components/InteractiveGuide";
import MergeRequestModal from "./components/MergeRequestModal";
import MergeRequestsSection from "./components/MergeRequestsSection";

// This is the main root component of the Adjustle application that handles navigation and globally shared data
function App() {

  // State management for current view, user details, and login status
  const [currentPage, setCurrentPage] = useState(sessionStorage.getItem("adjustle_currentPage") || "home");
  const [username, setUsername] = useState(sessionStorage.getItem("adjustle_username") || "");
  const [role, setRole] = useState(sessionStorage.getItem("adjustle_role") || "student");
  const [selectedDayClasses, setSelectedDayClasses] = useState(null);
  const [loggedIn, setLoggedIn] = useState(sessionStorage.getItem("adjustle_loggedIn") === "true");
  const [branch, setBranch] = useState(sessionStorage.getItem("adjustle_branch") || "BCA");
  const [timetableMode, setTimetableMode] = useState(role === "student" ? "revised" : "original");
  const [showGuide, setShowGuide] = useState(false);
  const [showTourInvite, setShowTourInvite] = useState(false);
  const transitionTimerRef = useRef(null);
  const transitionTimeoutRef = useRef(null);

  // Automatically update the timetable view mode when the user's role changes between student and teacher
  useEffect(function () {
    setTimetableMode(role === "student" ? "revised" : "original");
  }, [role]);

  // Keeps the browser's session storage in sync with the current app state for session persistence
  useEffect(function () {
    if (loggedIn) {
      sessionStorage.setItem("adjustle_username", username);
      sessionStorage.setItem("adjustle_role", role);
      sessionStorage.setItem("adjustle_branch", branch);
      sessionStorage.setItem("adjustle_loggedIn", "true");

      // Show guide invite only once per session if not opted out
      const hasSeenGuide = sessionStorage.getItem("adjustle_hasSeenGuide");
      const neverShow = localStorage.getItem("adjustle_neverShowTour");

      // Trigger guide invite when landing on timetable after login
      if (!hasSeenGuide && !neverShow && currentPage === "timetable" && !showGuide && !showTourInvite) {
        setShowTourInvite(true);
      }
    } else {
      // If logged out, clear storage
      if (username === "" && role === "student") {
        sessionStorage.removeItem("adjustle_username");
        sessionStorage.removeItem("adjustle_role");
        sessionStorage.setItem("adjustle_loggedIn", "false");
      }
    }
    sessionStorage.setItem("adjustle_currentPage", currentPage);
  }, [username, role, branch, loggedIn, currentPage, showGuide, showTourInvite]);


  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const [showTransition, setShowTransition] = useState(false);
  const [transitionText, setTransitionText] = useState("");

  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  // Handler for when a user clicks on a particular day in the timetable to see its classes
  const handleDaySelect = useCallback(function (dayName, classes) {
    if (!dayName) {
      setSelectedDayClasses(null);
    } else {
      setSelectedDayClasses({
        day: dayName,
        classes: classes
      });
    }
  }, []);

  // Main function to handle switching between different sections of the app with a smooth transition
  const navigateTo = useCallback(function (page) {
    if (page === currentPage) {
      return;
    }

    // Clear any existing timers
    if (transitionTimerRef.current) clearInterval(transitionTimerRef.current);
    if (transitionTimeoutRef.current) clearTimeout(transitionTimeoutRef.current);

    if (page === "timetable") {
      setCurrentPage(page);
      setShowTransition(false);
      return;
    }

    setShowTransition(true);
    setTransitionText("");

    const text = page.toUpperCase() + "...";
    let index = 0;

    transitionTimerRef.current = setInterval(function () {
      if (index <= text.length) {
        setTransitionText(text.substring(0, index));
        index = index + 1;
      } else {
        clearInterval(transitionTimerRef.current);
        transitionTimerRef.current = null;

        setCurrentPage(page);
        transitionTimeoutRef.current = setTimeout(function () {
          setShowTransition(false);
          transitionTimeoutRef.current = null;
        }, 600);
      }
    }, 40); // Faster typing
  }, [currentPage]);

  // Function that logs out the current user and resets the application state to default
  const logout = function () {
    sessionStorage.removeItem("adjustle_username");
    sessionStorage.removeItem("adjustle_role");
    sessionStorage.removeItem("adjustle_branch");
    sessionStorage.removeItem("adjustle_loggedIn");
    sessionStorage.removeItem("adjustle_currentPage");
    sessionStorage.removeItem("adjustle_hasSeenGuide");
    setShowLogoutConfirm(false);
    setLoggedIn(false);
    setRole("student");
    setBranch("BCA");
    setUsername("");
    navigateTo("home");
  };

  const closeLogoutModal = function () {
    setShowLogoutConfirm(false);
  };

  const openLogoutModal = function () {
    setShowLogoutConfirm(true);
  };

  function renderPage() {
    if (currentPage === "home") {
      return (
        <Home
          onNavigate={navigateTo}
          role={role}
          loggedIn={loggedIn}
        />
      );
    }

    if (currentPage === "login") {
      return (
        <Login
          loggedIn={loggedIn}
          setLoggedIn={setLoggedIn}
          username={username}
          setUsername={setUsername}
          setRole={setRole}
          setBranch={setBranch}
          onNavigate={navigateTo}
          id="login-view"
        />
      );
    }

    if (currentPage === "timetable") {
      return (
        <div style={{ display: 'flex', flexDirection: 'row', gap: '2%', width: '100%', alignItems: 'flex-start', paddingBottom: '20px' }}>
          {/* Main Timetable taking up most of the space on the left */}
          <div style={{ flex: '0 0 73%', maxWidth: '73%' }}>
            <Timetable
              username={username}
              role={role}
              branch={branch}
              viewMode={timetableMode}
              setViewMode={setTimetableMode}
              onDaySelect={handleDaySelect}
              selectedDay={selectedDayClasses?.day}
              onNavigate={navigateTo}
              onScheduleChange={function () { setRefreshTrigger(function (prev) { return prev + 1; }); }}
              refreshTrigger={refreshTrigger}
            />
          </div>

          {/* Sidebar section on the right for Teacher merges and Class alerts */}
          <div style={{ flex: '0 0 25%', maxWidth: '25%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Show pending merges for teachers in the sidebar */}
            {role.toLowerCase() === 'teacher' && (
              <MergeRequestsSection
                branch={branch}
                onActionComplete={function () { setRefreshTrigger(function (prev) { return prev + 1; }); }}
              />
            )}

            {/* Always show the class status alerts for the selected day or overall */}
            <div className="animate-up" style={{ animationDelay: '0.2s' }}>
              <ClassAlerts
                selectedDay={selectedDayClasses}
                refreshTrigger={refreshTrigger}
                role={role}
                branch={branch}
                onScheduleChange={function () { setRefreshTrigger(function (prev) { return prev + 1; }); }}
              />
            </div>
          </div>
        </div>
      );
    }

    if (currentPage === "alerts") {
      return (
        <ClassAlerts
          refreshTrigger={refreshTrigger}
          role={role}
          onScheduleChange={function () { setRefreshTrigger(function (prev) { return prev + 1; }); }}
        />
      );
    }

    if (currentPage === "count") {
      return (
        <Count
          branch={branch}
          username={username}
          onNavigate={navigateTo}
          onScheduleChange={function () { setRefreshTrigger(function (prev) { return prev + 1; }); }}
        />
      );
    }

    if (currentPage === "about") {
      return (
        <About />
      );
    }

    if (currentPage === "notifications") {
      return (
        <Notifications role={role} branch={branch} loggedIn={loggedIn} />
      );
    }

    return null;
  }

  function navClass(name) {
    if (currentPage === name) {
      return "active";
    }
    return "";
  }

  /* ---- Conditional navigation links ---- */
  let loginLink = null;
  if (!loggedIn) {
    loginLink = (
      <span
        className={navClass("login")}
        onClick={function () { navigateTo("login"); }}
        id="nav-login"
      >
        LOGIN
      </span>
    );
  }

  let timetableLink = null;
  if (loggedIn) {
    timetableLink = (
      <span
        className={navClass("timetable")}
        onClick={function () { navigateTo("timetable"); }}
        id="nav-timetable"
      >
        TIMETABLE
      </span>
    );
  }

  let countLink = null;
  if (loggedIn && role === "teacher") {
    countLink = (
      <span
        className={navClass("count")}
        onClick={function () { navigateTo("count"); }}
        id="nav-count"
      >
        COUNT
      </span>
    );
  }

  return (
    <div className="app">
      {/* ---- Frame Top: Navigation Bar ---- */}
      <div className="frame-top">
        <div className="logo">{currentPage !== "home" && "ADJUSTLE"}</div>
        <div className="nav-links">
          <span
            className={navClass("home")}
            onClick={function () { navigateTo("home"); }}
            id="nav-home"
          >
            HOME
          </span>
          {loginLink}
          {timetableLink}
          {countLink}
          <span
            className={navClass("about")}
            onClick={function () { navigateTo("about"); }}
            id="nav-about"
          >
            ABOUT
          </span>
          {loggedIn && (
            <span
              onClick={openLogoutModal}
              id="nav-logout"
            >
              LOGOUT
            </span>
          )}
        </div>
      </div>

      {/* ---- Interactive Guide Overlay ---- */}
      {(loggedIn && showGuide) && (
        <InteractiveGuide
          role={role}
          currentPage={currentPage}
          onNavigate={navigateTo}
          showTransition={showTransition}
          onClose={function () {
            setShowGuide(false);
            if (loggedIn) {
              sessionStorage.setItem("adjustle_hasSeenGuide", "true");
            }
          }}
        />
      )}

      {/* ---- Merge Request Modal ---- */}
      {(loggedIn && branch && role.toLowerCase() === 'teacher') && (
        <MergeRequestModal branch={branch} username={username} />
      )}

      {/* ---- Tour Invite Modal ---- */}
      {(loggedIn && showTourInvite) && (
        <div style={{
          position: 'fixed',
          bottom: '30px',
          right: '30px',
          backgroundColor: '#19140e',
          border: '1px solid #d9bc94',
          borderRadius: '12px',
          padding: '25px',
          zIndex: 5000,
          width: '320px',
          boxShadow: '0 10px 40px #000000e6',
        }} className="animate-up">
          <h3 style={{ margin: '0 0 10px 0', color: '#d9bc94', fontFamily: 'Garamond, serif' }}>Wanna take a tour?</h3>
          <p style={{ margin: '0 0 20px 0', fontSize: '14px', opacity: 0.8, lineHeight: '1.4' }}>
            Quickly learn how to navigate Adjustle and manage your department's schedule.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              className="button primary"
              style={{ width: '100%', padding: '10px' }}
              onClick={function () {
                setShowTourInvite(false);
                setShowGuide(true);
              }}
            >
              YES, START TOUR
            </button>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <button
                style={{ background: 'none', border: 'none', color: '#d9bc94', opacity: 0.6, cursor: 'pointer', fontSize: '12px' }}
                onClick={function () {
                  setShowTourInvite(false);
                  sessionStorage.setItem("adjustle_hasSeenGuide", "true");
                }}
              >
                Later
              </button>
              <button
                style={{ background: 'none', border: 'none', color: '#ef4444', opacity: 0.6, cursor: 'pointer', fontSize: '12px' }}
                onClick={function () {
                  setShowTourInvite(false);
                  localStorage.setItem("adjustle_neverShowTour", "true");
                  sessionStorage.setItem("adjustle_hasSeenGuide", "true");
                }}
              >
                Never show again
              </button>
            </div>
          </div>
        </div>
      )}


      {/* ---- Main Page Content ---- */}
      {currentPage === "login" ? (
        renderPage()
      ) : (
        <div className="main-content" style={{ display: 'flex', justifyContent: 'center' }}>
          <div className="container">
            {renderPage()}
          </div>
        </div>
      )}

      <div className="frame-bottom">
        Adjustle|2026
      </div>


      {/* ---- Transition Screen ---- */}
      {showTransition && (
        <div className="transition-overlay">
          <div className="transition-content">
            <div className="transition-text">
              {transitionText}
              <span className="cursor">|</span>
            </div>
          </div>
        </div>
      )}

      {/* ---- Logout Confirmation Modal ---- */}
      {showLogoutConfirm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Confirm Logout</h3>
            <p>Are you sure you want to logout?</p>
            <div className="modal-actions">
              <button
                className="button primary"
                onClick={logout}
              >
                YES
              </button>
              <button
                className="button secondary"
                onClick={closeLogoutModal}
              >
                NO
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
