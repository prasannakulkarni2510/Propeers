import { useLeads } from "../hooks/useLeads";
import LeadTable from "../components/LeadTable.jsx";

export default function Leads() {
  const { leads, loading } = useLeads();
  return (
    <div>
      <h1 className="page-title">Leads</h1>
      <p className="page-sub">
        {leads.length} lead(s) from data/leads.csv · click a row for its assets
      </p>
      {loading ? <p className="muted">Loading…</p> : <LeadTable leads={leads} />}
    </div>
  );
}
