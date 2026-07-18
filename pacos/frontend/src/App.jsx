import { NavLink, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import { useStore } from "./store";
import { useAgentPolling } from "./hooks/useAgentStatus";
import Home from "./pages/Home.jsx";
import Leads from "./pages/Leads.jsx";
import Assets from "./pages/Assets.jsx";
import Approvals from "./pages/Approvals.jsx";
import Tracker from "./pages/Tracker.jsx";
import Chat from "./pages/Chat.jsx";
import Discovery from "./pages/Discovery.jsx";
import About from "./pages/About.jsx";
import AuthGate from "./components/AuthGate.jsx";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/leads", label: "Leads" },
  { to: "/assets", label: "Assets" },
  { to: "/approvals", label: "Approvals" },
  { to: "/tracker", label: "Tracker" },
  { to: "/chat", label: "Chat" },
  { to: "/discovery", label: "Discovery" },
];

function Toast() {
  const { toast, error, clearToast } = useStore();
  useEffect(() => {
    if (toast) {
      const id = setTimeout(clearToast, 3500);
      return () => clearTimeout(id);
    }
  }, [toast, clearToast]);
  if (!toast && !error) return null;
  return (
    <div className={`toast ${error ? "toast-error" : ""}`}>
      {error || toast}
    </div>
  );
}

const MOBILE_QUERY = "(max-width: 900px)";

export default function App() {
  // Poll agent status app-wide so generation progress keeps updating even when
  // the user navigates away from the Dashboard.
  useAgentPolling();
  // Chatbot-style nav: open by default on desktop, hidden on mobile until the
  // operator asks for it. Picking a page on mobile closes it again.
  const [navOpen, setNavOpen] = useState(
    () => !window.matchMedia(MOBILE_QUERY).matches,
  );
  const onNavigate = () => {
    if (window.matchMedia(MOBILE_QUERY).matches) setNavOpen(false);
  };
  return (
    <AuthGate>
    <div className={`app ${navOpen ? "" : "nav-closed"}`}>
      {!navOpen && (
        <button className="nav-toggle" aria-label="Open menu" onClick={() => setNavOpen(true)}>
          ☰
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
        <nav>
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              onClick={onNavigate}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
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
      <main className="content">
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
        </Routes>
      </main>
      <Toast />
    </div>
    </AuthGate>
  );
}
