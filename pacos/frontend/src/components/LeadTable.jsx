import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge.jsx";

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
            <th>Company</th>
            <th>Role</th>
            <th>City</th>
            <th>Persona</th>
            <th>Domain</th>
            <th>Channel</th>
            <th>Assets</th>
            <th>Status</th>
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
              <td>{l.company_name}</td>
              <td>{l.job_title}</td>
              <td>{l.city}</td>
              <td>{l.persona_tag}</td>
              <td><span className="tag">{l.domain_tag}</span></td>
              <td>{l.has_email ? "email + dm" : "dm-only"}</td>
              <td>{l.assets_generated === "true" ? "✓" : "—"}</td>
              <td><StatusBadge status={l.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
