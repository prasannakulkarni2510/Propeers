import { NavLink, Route, Routes } from "react-router-dom";
import { useEffect } from "react";
import { useStore } from "./store";
import Home from "./pages/Home.jsx";
import Leads from "./pages/Leads.jsx";
import Assets from "./pages/Assets.jsx";
import Approvals from "./pages/Approvals.jsx";
import Tracker from "./pages/Tracker.jsx";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/leads", label: "Leads" },
  { to: "/assets", label: "Assets" },
  { to: "/approvals", label: "Approvals" },
  { to: "/tracker", label: "Tracker" },
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

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          PAC<span className="brand-accent">OS</span>
        </div>
        <div className="brand-sub">Personal AI Career OS</div>
        <nav>
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          Nemotron-powered · never auto-sends
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
        </Routes>
      </main>
      <Toast />
    </div>
  );
}
