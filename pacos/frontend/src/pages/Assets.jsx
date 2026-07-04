import { useParams, useNavigate } from "react-router-dom";
import { useLeads } from "../hooks/useLeads";
import AssetViewer from "../components/AssetViewer.jsx";

export default function Assets() {
  const { leadId } = useParams();
  const navigate = useNavigate();
  const { leads } = useLeads();
  const selected = leadId || "";

  return (
    <div>
      <h1 className="page-title">Assets</h1>
      <p className="page-sub">The four generated files per lead · copy-paste to send</p>
      <div className="panel">
        <label className="muted" style={{ marginRight: 8 }}>Lead:</label>
        <select
          className="select"
          value={selected}
          onChange={(e) => navigate(`/assets/${e.target.value}`)}
        >
          <option value="">— select a lead —</option>
          {leads.map((l) => (
            <option key={l.lead_id} value={l.lead_id}>
              {l.full_name} — {l.company_name}
            </option>
          ))}
        </select>
      </div>
      <div className="panel">
        <AssetViewer leadId={selected} />
      </div>
    </div>
  );
}
