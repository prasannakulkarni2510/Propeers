import { useEffect, useState } from "react";
import { useLeads } from "../hooks/useLeads";
import { api } from "../services/api";
import OutreachTracker from "../components/OutreachTracker.jsx";

export default function Tracker() {
  const { leads, loading } = useLeads();
  const [digest, setDigest] = useState("");

  useEffect(() => {
    api.digest().then((d) => setDigest(d.text)).catch(() => {});
  }, [leads]);

  return (
    <div>
      <h1 className="page-title">Tracker</h1>
      <p className="page-sub">All pipeline state (tracker.csv) · today's digest</p>
      {loading ? <p className="muted">Loading…</p> : <OutreachTracker leads={leads} />}
      <div className="panel">
        <h3>Daily digest</h3>
        {digest ? <div className="digest">{digest}</div> : <p className="muted">—</p>}
      </div>
    </div>
  );
}
