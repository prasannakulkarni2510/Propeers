import { useEffect, useState } from "react";
import { useLeads } from "../hooks/useLeads";
import { api } from "../services/api";
import { useStore } from "../store";
import OutreachTracker from "../components/OutreachTracker.jsx";

export default function Tracker() {
  const { leads, loading, refresh } = useLeads();
  const setToast = useStore((s) => s.setToast);
  const [digest, setDigest] = useState("");
  const [jobs, setJobs] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");

  useEffect(() => {
    api.digest().then((d) => setDigest(d.text)).catch(() => {});
    api.jobs().then(setJobs).catch(() => {});
  }, [leads]);

  const scan = async () => {
    setScanning(true);
    setScanError("");
    try {
      const r = await api.scanInbox();
      setToast(
        `Inbox scan: ${r.scanned} mail(s) — ${r.matched} matched, ` +
        `${r.unmatched} unmatched, ${r.job_alerts} job alert(s)`
      );
      await refresh();
    } catch (e) {
      setScanError(e.message);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">Tracker</h1>
      <p className="page-sub">All pipeline state (tracker.csv) · today's digest</p>
      <div className="btn-row" style={{ marginBottom: 16 }}>
        <button className="btn" disabled={scanning} onClick={scan}>
          {scanning ? "Scanning inbox…" : "Scan inbox"}
        </button>
        {scanError && <span className="jd-error">{scanError}</span>}
      </div>
      {loading ? <p className="muted">Loading…</p> : <OutreachTracker leads={leads} />}
      <div className="panel">
        <h3>Job alerts from your inbox ({jobs.length})</h3>
        {jobs.length === 0 ? (
          <p className="muted">
            None yet — click “Scan inbox” to pull LinkedIn/Naukri alerts from Gmail.
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Source</th>
                <th>Posting</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.url}>
                  <td style={{ whiteSpace: "nowrap" }}>{j.date}</td>
                  <td><span className="tag">{j.source}</span></td>
                  <td>
                    <a href={j.url} target="_blank" rel="noreferrer">
                      {j.title}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="panel">
        <h3>Daily digest</h3>
        {digest ? <div className="digest">{digest}</div> : <p className="muted">—</p>}
      </div>
    </div>
  );
}
