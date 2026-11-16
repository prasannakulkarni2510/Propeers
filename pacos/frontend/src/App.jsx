import { Link, Navigate, NavLink, Route, Routes, useLocation, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useStore } from "./store";
import { useLeads } from "./hooks/useLeads";
import { pipelineCounts } from "./lib/pipeline";
import Chat from "./pages/Chat.jsx";
import Pipeline from "./pages/Pipeline.jsx";
import FindPeople from "./pages/FindPeople.jsx";
import About from "./pages/About.jsx";
import AuthGate from "./components/AuthGate.jsx";
import Icon from "./components/Icon.jsx";
import LeadPanel from "./components/LeadModal.jsx";
import { authToken } from "./services/api";

// Three places. `badge` picks a count from pipelineCounts.
const NAV = [
  { to: "/", label: "Chat", end: true },
  { to: "/pipeline", label: "Pipeline", badge: true },
  { to: "/find", label: "Find people" },
];

const TITLES = { "/": "Chat", "/pipeline": "Pipeline", "/find": "Find people", "/about": "About" };

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
    <div className={`toast ${error ? "toast-error" : ""}`} role={error ? "alert" : "status"}>
      <span>{error || toast}</span>
      <button className="toast-close" aria-label="Dismiss" onClick={() => (error ? clearError() : clearToast())}>
        <Icon name="close" size={14} />
      </button>
    </div>
  );
}

// Pages that were folded into the Pipeline keep working as addresses; an open
// lead (?lead=) or a search (?company=) carries over.
function Moved({ to }) {
  const { search } = useLocation();
  return <Navigate to={`${to}${search}`} replace />;
}
function AssetsRedirect() {
  const { leadId } = useParams();
  return <Navigate to={`/pipeline?lead=${encodeURIComponent(leadId)}`} replace />;
}

function NotFound() {
  return (
    <div className="empty-state">
      <h1 className="page-title">Page not found</h1>
      <p className="page-sub">That address isn’t part of PACOS.</p>
      <Link className="btn btn-accent" to="/">Back to chat</Link>
    </div>
  );
}

const MOBILE_QUERY = "(max-width: 900px)";

export default function App() {
  // Leads are loaded at the shell level so the nav badge is live everywhere.
  const { leads } = useLeads();
  const counts = useMemo(() => pipelineCounts(leads), [leads]);
  const generating = useStore((s) => s.generating);
  const { pathname } = useLocation();

  // Open by default on desktop, hidden on mobile until asked for. Picking a
  // page on mobile closes it again.
  const [navOpen, setNavOpen] = useState(() => !window.matchMedia(MOBILE_QUERY).matches);
  const onNavigate = () => {
    if (window.matchMedia(MOBILE_QUERY).matches) setNavOpen(false);
  };

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
    const page = TITLES["/" + (pathname.split("/")[1] || "")];
    document.title = page ? `${page} · PACOS` : "PACOS";
  }, [pathname]);

  // What needs the operator today: overdue follow-ups first, else drafts to send.
  const badge = counts.due > 0
    ? { n: counts.due, tone: "warn", hint: `${counts.due} follow-up${counts.due === 1 ? "" : "s"} due` }
    : counts.ready > 0
      ? { n: counts.ready, tone: "", hint: `${counts.ready} ready to send` }
      : null;

  return (
    <AuthGate>
      <div className={`app ${navOpen ? "" : "nav-closed"}`}>
        <a className="skip-link" href="#main">Skip to content</a>
        {!navOpen && (
          <button className="icon-btn nav-toggle" aria-label="Open menu" onClick={() => setNavOpen(true)}>
            <Icon name="menu" size={18} />
            {badge && <span className="nav-toggle-dot" />}
          </button>
        )}
        {navOpen && <div className="backdrop" onClick={() => setNavOpen(false)} />}
        <aside className={`sidebar ${navOpen ? "open" : ""}`}>
          <div className="sidebar-head">
            <div className="brand">PAC<span className="brand-accent">OS</span></div>
            <button className="icon-btn" aria-label="Close menu" onClick={() => setNavOpen(false)}>
              <Icon name="close" size={16} />
            </button>
          </div>
          <nav aria-label="Main">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                onClick={onNavigate}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                <span>{n.label}</span>
                {n.badge && badge && (
                  <span className={`nav-badge ${badge.tone ? `nav-badge-${badge.tone}` : ""}`} title={badge.hint} aria-label={badge.hint}>
                    {badge.n > 99 ? "99+" : badge.n}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-foot">
            {generating && (
              <div className="sidebar-live" role="status">
                <span className="dot running" /> Writing drafts…
              </div>
            )}
            <NavLink to="/about" onClick={onNavigate} className={({ isActive }) => `nav-quiet ${isActive ? "active" : ""}`}>
              About
            </NavLink>
            {authToken.get() && (
              <button className="nav-quiet" onClick={() => { authToken.set(""); window.location.reload(); }}>
                Log out
              </button>
            )}
          </div>
        </aside>
        <main className="content" id="main">
          <Routes>
            <Route path="/" element={<Chat />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/find" element={<FindPeople />} />
            <Route path="/about" element={<About />} />
            {/* Old addresses. */}
            <Route path="/chat" element={<Navigate to="/" replace />} />
            <Route path="/dashboard" element={<Moved to="/pipeline" />} />
            <Route path="/leads" element={<Moved to="/pipeline" />} />
            <Route path="/approvals" element={<Moved to="/pipeline" />} />
            <Route path="/tracker" element={<Moved to="/pipeline" />} />
            <Route path="/assets" element={<Moved to="/pipeline" />} />
            <Route path="/assets/:leadId" element={<AssetsRedirect />} />
            <Route path="/discovery" element={<Moved to="/find" />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <LeadPanel />
        <Toast />
      </div>
    </AuthGate>
  );
}
