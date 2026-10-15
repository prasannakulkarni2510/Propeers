import { useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useLeads } from "../hooks/useLeads";
import AssetViewer from "../components/AssetViewer.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

// Who this outreach is for, with the contact details needed to actually send it.
function LeadHeader({ lead }) {
  const email = lead.predicted_email || lead.email;
  return (
    <div className="lead-head">
      <div>
        <div className="lead-head-name">
          {lead.full_name || <span className="muted">(no contact yet)</span>}
          <StatusBadge status={lead.status} />
        </div>
        <div className="muted">
          {[lead.job_title, lead.company_name, lead.city].filter(Boolean).join(" · ")}
        </div>
      </div>
      <div className="lead-head-links">
        {email && (
          <span className="email-addr" title={lead.email_status === "predicted" ? "Predicted, not verified" : ""}>
            {lead.email_status === "predicted" && <span className="muted">Likely: </span>}
            {email}
          </span>
        )}
        {lead.linkedin_url && (
          <a className="link" href={lead.linkedin_url} target="_blank" rel="noopener noreferrer">
            LinkedIn ↗
          </a>
        )}
      </div>
    </div>
  );
}

export default function Assets() {
  const { leadId } = useParams();
  const navigate = useNavigate();
  const { leads } = useLeads();
  const selected = leadId || "";
  const [q, setQ] = useState("");

  // Filter the picker so it stays usable with hundreds of leads. Keep the
  // currently selected lead in the list even if it doesn't match the search.
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return leads;
    return leads.filter(
      (l) =>
        l.lead_id === selected ||
        [l.full_name, l.company_name, l.job_title, l.city].some((v) =>
          (v || "").toLowerCase().includes(needle),
        ),
    );
  }, [leads, q, selected]);

  const lead = leads.find((l) => l.lead_id === selected);
  // Step through the (filtered) list without going back to the picker.
  const idx = shown.findIndex((l) => l.lead_id === selected);
  const go = (i) => navigate(`/assets/${shown[i].lead_id}`);

  return (
    <div>
      <h1 className="page-title">Assets</h1>
      <p className="page-sub">The four generated files per lead · copy-paste to send</p>
      <div className="panel">
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <input
            className="input"
            style={{ maxWidth: 300 }}
            placeholder="Search leads…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select
            className="select"
            style={{ flex: "1 1 240px", minWidth: 0, maxWidth: 560 }}
            value={selected}
            onChange={(e) => navigate(`/assets/${e.target.value}`)}
          >
            <option value="">select a lead ({shown.length})</option>
            {shown.map((l) => (
              <option key={l.lead_id} value={l.lead_id}>
                {l.assets_generated === "true" ? "✓ " : ""}
                {l.company_name} · {l.job_title} ({l.full_name || "no contact"})
              </option>
            ))}
          </select>
          {selected && (
            <div className="btn-row" style={{ marginLeft: "auto" }}>
              <button className="btn btn-ghost btn-sm" disabled={idx <= 0} onClick={() => go(idx - 1)}>
                ← Prev
              </button>
              <button
                className="btn btn-ghost btn-sm"
                disabled={idx < 0 || idx >= shown.length - 1}
                onClick={() => go(idx + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="panel">
        {lead && <LeadHeader lead={lead} />}
        <AssetViewer leadId={selected} lead={lead} />
      </div>
    </div>
  );
}
