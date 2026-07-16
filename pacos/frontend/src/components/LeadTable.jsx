import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../store";
import StatusBadge from "./StatusBadge.jsx";

// Per-row actions: discovery jump + delete with an inline two-click confirm
// (no native dialogs). Deleting removes the lead from the tracker, the lead
// sheet, and its generated assets.
function RowActions({ lead }) {
  const navigate = useNavigate();
  const deleteLead = useStore((s) => s.deleteLead);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const remove = async (e) => {
    e.stopPropagation();
    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 4000); // auto-cancel
      return;
    }
    setBusy(true);
    try {
      await deleteLead(lead.lead_id);
    } catch (_) {
      setBusy(false);
      setConfirming(false);
    }
  };

  return (
    <div className="btn-row" style={{ flexWrap: "nowrap" }}>
      <button
        className="btn btn-ghost btn-sm"
        title={`Boolean searches for hiring people at ${lead.company_name}`}
        onClick={(e) => {
          e.stopPropagation();
          const q = new URLSearchParams({
            company: lead.company_name, role: lead.job_title, city: lead.city,
          });
          navigate(`/discovery?${q}`);
        }}
      >
        Find people
      </button>
      <button
        className={`btn btn-sm ${confirming ? "btn-accent" : "btn-ghost"}`}
        title="Remove this lead from the tracker, lead sheet, and assets"
        disabled={busy}
        onClick={remove}
      >
        {busy ? "Removing…" : confirming ? "Confirm?" : "Remove"}
      </button>
    </div>
  );
}

// Predicted work email + a confidence chip. Falls back to a plain verified/typed
// email when the lead wasn't auto-enriched. Predicted emails are flagged so they
// read as "likely", never "confirmed".
function EmailCell({ lead }) {
  const email = lead.predicted_email || lead.email;
  if (!email) return <span className="muted">—</span>;
  const predicted = lead.email_status === "predicted";
  const conf = (lead.email_confidence || "").toLowerCase();
  return (
    <div className="email-cell">
      {predicted && <span className="muted email-likely">Likely:</span>}
      <span className="email-addr">{email}</span>
      {predicted && conf && (
        <span className={`conf conf-${conf}`}>{conf[0].toUpperCase() + conf.slice(1)}</span>
      )}
    </div>
  );
}

// CSV lead list view (docx: LeadTable.jsx). Click a row to view its assets.
export default function LeadTable({ leads }) {
  const navigate = useNavigate();
  if (!leads?.length) return <p className="muted">No leads. Add rows to data/leads.csv.</p>;
  return (
    <div className="panel" style={{ overflowX: "auto" }}>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Title</th>
            <th>Company</th>
            <th>LinkedIn</th>
            <th>Predicted Email</th>
            <th>Domain</th>
            <th>Assets</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((l) => (
            <tr
              key={l.lead_id}
              className="row-click"
              onClick={() => navigate(`/assets/${l.lead_id}`)}
            >
              <td>{l.full_name}</td>
              <td>{l.job_title}</td>
              <td>{l.company_name}</td>
              <td>
                {l.linkedin_url ? (
                  <a
                    className="link"
                    href={l.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    profile ↗
                  </a>
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td><EmailCell lead={l} /></td>
              <td><span className="tag">{l.domain_tag}</span></td>
              <td>{l.assets_generated === "true" ? "✓" : "—"}</td>
              <td><StatusBadge status={l.status} /></td>
              <td><RowActions lead={l} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
