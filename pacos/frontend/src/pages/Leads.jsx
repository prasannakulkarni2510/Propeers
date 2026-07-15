import { useLeads } from "../hooks/useLeads";
import LeadTable from "../components/LeadTable.jsx";
import AddLeadFromJD from "../components/AddLeadFromJD.jsx";
import AddLeadForm from "../components/AddLeadForm.jsx";

export default function Leads() {
  const { leads, loading } = useLeads();
  return (
    <div>
      <h1 className="page-title">Leads</h1>
      <p className="page-sub">
        {leads.length} lead(s) from data/leads.csv · click a row for its assets
      </p>
      <div className="jd-add">
        <AddLeadFromJD />
        <AddLeadForm />
      </div>
      {loading ? <p className="muted">Loading…</p> : <LeadTable leads={leads} />}
    </div>
  );
}
