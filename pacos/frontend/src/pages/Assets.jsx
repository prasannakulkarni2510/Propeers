import { useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useLeads } from "../hooks/useLeads";
import AssetViewer from "../components/AssetViewer.jsx";

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

  return (
    <div>
      <h1 className="page-title">Assets</h1>
      <p className="page-sub">The four generated files per lead · copy-paste to send</p>
      <div className="panel">
        <div className="toolbar">
          <input
            className="input"
            style={{ maxWidth: 300 }}
            placeholder="Search leads…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select
            className="select"
            value={selected}
            onChange={(e) => navigate(`/assets/${e.target.value}`)}
          >
            <option value="">— select a lead ({shown.length}) —</option>
            {shown.map((l) => (
              <option key={l.lead_id} value={l.lead_id}>
                {l.company_name} — {l.job_title} ({l.full_name})
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="panel">
        <AssetViewer leadId={selected} />
      </div>
    </div>
  );
}
