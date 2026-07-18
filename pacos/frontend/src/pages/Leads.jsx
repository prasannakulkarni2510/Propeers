import { useState } from "react";
import { useLeads } from "../hooks/useLeads";
import LeadBrowser from "../components/LeadBrowser.jsx";
import AddLeadFromJD from "../components/AddLeadFromJD.jsx";
import AddLeadForm from "../components/AddLeadForm.jsx";

// People and job dumps are different things: a person gets outreach assets,
// a job posting is a company/role waiting for a contact. Two tabs keep the
// job rows from polluting the people list.
export default function Leads() {
  const { leads, loading } = useLeads();
  const [tab, setTab] = useState("person");
  const people = leads.filter((l) => (l.lead_type || "person") !== "job");
  const jobs = leads.filter((l) => l.lead_type === "job");
  const shown = tab === "job" ? jobs : people;
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
      <div className="tabs">
        <button
          className={`tab ${tab === "person" ? "active" : ""}`}
          onClick={() => setTab("person")}
        >
          People ({people.length})
        </button>
        <button
          className={`tab ${tab === "job" ? "active" : ""}`}
          onClick={() => setTab("job")}
        >
          Jobs ({jobs.length})
        </button>
      </div>
      {tab === "job" && (
        <p className="muted">
          Job postings with no contact person yet. Use "Find people" on a row to
          hunt the hiring manager or recruiter, then add them as a person lead.
        </p>
      )}
      {loading ? <p className="muted">Loading…</p> : <LeadBrowser leads={shown} />}
    </div>
  );
}
