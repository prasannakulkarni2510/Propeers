import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useStore } from "./store";
import { useAgentPolling } from "./hooks/useAgentStatus";
import { useLeads } from "./hooks/useLeads";
import { pipelineCounts } from "./lib/pipeline";
import Home from "./pages/Home.jsx";
import Leads from "./pages/Leads.jsx";
import Assets from "./pages/Assets.jsx";
import Approvals from "./pages/Approvals.jsx";
import Tracker from "./pages/Tracker.jsx";
import Chat from "./pages/Chat.jsx";
import Discovery from "./pages/Discovery.jsx";
import About from "./pages/About.jsx";
import AuthGate from "./components/AuthGate.jsx";
import IntroVideo from "./components/IntroVideo.jsx";

// `badge` picks a count from pipelineCounts; `badgeTone` colours it.
const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/leads", label: "Leads" },
  { to: "/assets", label: "Assets" },
  { to: "/approvals", label: "Approvals", badge: "ready", hint: "ready to send" },
  { to: "/tracker", label: "Tracker", badge: "due", badgeTone: "warn", hint: "follow-ups due" },
  { to: "/chat", label: "Chat" },
  { to: "/discovery", label: "Discovery" },
];

const TITLES = {
  "/": "Dashboard", "/leads": "Leads", "/assets": "Assets", "/approvals": "Approvals",
  "/tracker": "Tracker", "/chat": "Chat", "/discovery": "Discovery", "/about": "About",
};

function Toast() {
  const { toast, error, clearToast, clearError } = useStore();
  useEffect(() => {
    if (toast && !error) {
      const id = setTimeout(clearToast, 3500);
      return () => clearTimeout(id);
    }
  }, [toast, error, clearToast]);
  if (!toast && !error) return null;
  // Errors stay until dismissed (they matter); plain toasts fade on their own.
  return (
    <div
      className={`toast ${error ? "toast-error" : ""}`}
      role={error ? "alert" : "status"}
    >
      <span>{error || toast}</span>
      <button
        className="toast-close"
        aria-label="Dismiss"
        onClick={() => (error ? clearError() : clearToast())}
      >
        ✕
      </button>
    </div>
  );
}

function NotFound() {
  return (
    <div className="empty-state">
      <h1 className="page-title">Page not found</h1>
      <p className="page-sub">That address isn't part of PACOS.</p>
      <Link className="btn btn-accent" to="/">Back to the dashboard</Link>
    </div>
  );
}

const MOBILE_QUERY = "(max-width: 900px)";

export default function App() {
  // Poll agent status app-wide so generation progress keeps updating even when
  // the user navigates away from the Dashboard.
  useAgentPolling();
  // Leads are loaded at the shell level so the nav badges are live everywhere.
  const { leads } = useLeads();
  const counts = useMemo(() => pipelineCounts(leads), [leads]);
  const generating = useStore((s) => s.generating);
  const { pathname } = useLocation();

  // Chatbot-style nav: open by default on desktop, hidden on mobile until the
  // operator asks for it. Picking a page on mobile closes it again.
  const [navOpen, setNavOpen] = useState(
    () => !window.matchMedia(MOBILE_QUERY).matches,
  );
  const onNavigate = () => {
    if (window.matchMedia(MOBILE_QUERY).matches) setNavOpen(false);
  };

  // Escape closes the overlay nav on mobile.
  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape" && window.matchMedia(MOBILE_QUERY).matches) setNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen]);

  // Tab title follows the page so several PACOS tabs stay distinguishable.
  useEffect(() => {
    const key = "/" + (pathname.split("/")[1] || "");
    const page = TITLES[key];
    document.title = page ? `${page} · PACOS` : "PACOS — Personal AI Career OS";
  }, [pathname]);

  return (
    <>
    <IntroVideo />
    <AuthGate>
    <div className={`app ${navOpen ? "" : "nav-closed"}`}>
      <a className="skip-link" href="#main">Skip to content</a>
      {!navOpen && (
        <button className="nav-toggle" aria-label="Open menu" onClick={() => setNavOpen(true)}>
          ☰
          {counts.ready + counts.due > 0 && <span className="nav-toggle-dot" />}
        </button>
      )}
      {navOpen && <div className="backdrop" onClick={() => setNavOpen(false)} />}
      <aside className={`sidebar ${navOpen ? "open" : ""}`}>
        <div className="sidebar-head">
          <div>
            <div className="brand">
              PAC<span className="brand-accent">OS</span>
            </div>
            <div className="brand-sub">Personal AI Career OS</div>
          </div>
          <button className="nav-close" aria-label="Close menu" onClick={() => setNavOpen(false)}>
            ✕
          </button>
        </div>
        <nav aria-label="Main">
          {NAV.map((n) => {
            const count = n.badge ? counts[n.badge] : 0;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                onClick={onNavigate}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                <span>{n.label}</span>
                {count > 0 && (
                  <span
                    className={`nav-badge ${n.badgeTone ? `nav-badge-${n.badgeTone}` : ""}`}
                    title={`${count} ${n.hint}`}
                    aria-label={`${count} ${n.hint}`}
                  >
                    {count > 99 ? "99+" : count}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          {generating && (
            <NavLink to="/" onClick={onNavigate} className="sidebar-live">
              <span className="dot running" /> Generating assets…
            </NavLink>
          )}
          <NavLink
            to="/about"
            onClick={onNavigate}
            className={({ isActive }) => `nav-about ${isActive ? "active" : ""}`}
          >
            Know more about the project →
          </NavLink>
          <span className="sidebar-tag">Nemotron-powered · never auto-sends</span>
        </div>
      </aside>
      <main className="content" id="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/assets/:leadId" element={<Assets />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/discovery" element={<Discovery />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Toast />
    </div>
    </AuthGate>
    </>
  );
}
