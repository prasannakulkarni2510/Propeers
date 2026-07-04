import { useApprovals } from "../hooks/useApprovals";
import StatusBadge from "./StatusBadge.jsx";

const FLOW = ["pending", "sent", "replied", "interested", "interview", "offer", "rejected"];

// CRM — sent/replied/follow-up (docx: OutreachTracker.jsx). Full pipeline table
// with an inline status selector per lead.
export default function OutreachTracker({ leads }) {
  const { markStatus } = useApprovals();
  const rows = leads.filter((l) => l.status);
  if (!rows.length) return <p className="muted">No leads in the pipeline yet.</p>;

  return (
    <div className="panel" style={{ overflowX: "auto" }}>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th><th>Company</th><th>Status</th><th>Sent</th>
            <th>Channel</th><th>Last reply</th><th>Intent</th>
            <th>Follow-up due</th><th>Set status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((l) => (
            <tr key={l.lead_id}>
              <td>{l.full_name}</td>
              <td>{l.company_name}</td>
              <td><StatusBadge status={l.status} /></td>
              <td>{l.outreach_sent_date || "—"}</td>
              <td>{l.channel || "—"}</td>
              <td>{l.last_reply_date || "—"}</td>
              <td>{l.reply_intent || "—"}</td>
              <td>{l.follow_up_due || "—"}</td>
              <td>
                <select
                  className="select"
                  value={l.status}
                  onChange={(e) => markStatus(l.lead_id, e.target.value)}
                >
                  {FLOW.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
