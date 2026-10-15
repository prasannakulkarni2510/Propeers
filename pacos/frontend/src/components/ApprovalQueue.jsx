import { Link } from "react-router-dom";
import { useApprovals } from "../hooks/useApprovals";
import { isAwaitingReply, isFollowUpDue, isReadyToSend } from "../lib/pipeline";

// Manual approve/act queue (docx: ApprovalQueue.jsx). Leads with assets that are
// still pending are ready for you to send; sent leads await a reply.
export default function ApprovalQueue({ leads }) {
  const { markSent, markReply } = useApprovals();

  const ready = leads.filter(isReadyToSend);
  // Overdue follow-ups first: they're the ones to chase today.
  const awaiting = leads
    .filter(isAwaitingReply)
    .sort((a, b) => (a.follow_up_due || "9").localeCompare(b.follow_up_due || "9"));

  return (
    <>
      <div className="panel">
        <h3>Ready to send ({ready.length})</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Copy the assets from the Assets tab, send them by hand, then mark the
          channel here. PACOS never sends for you.
        </p>
        {ready.length === 0 ? (
          <p className="muted">Nothing pending. Generate assets first.</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Name</th><th>Company</th><th>Channel</th><th>Drafts</th><th>Mark sent as</th></tr>
            </thead>
            <tbody>
              {ready.map((l) => (
                <tr key={l.lead_id}>
                  <td>{l.full_name}</td>
                  <td>{l.company_name}</td>
                  <td>{l.has_email ? "email + dm" : "dm-only"}</td>
                  <td>
                    <Link className="link" to={`/assets/${l.lead_id}`}>Open drafts →</Link>
                  </td>
                  <td>
                    <div className="btn-row">
                      {l.has_email && (
                        <button className="btn btn-sm" onClick={() => markSent(l.lead_id, "email")}>
                          Email
                        </button>
                      )}
                      <button className="btn btn-sm" onClick={() => markSent(l.lead_id, "dm")}>
                        DM
                      </button>
                      {l.has_email && (
                        <button className="btn btn-sm btn-accent" onClick={() => markSent(l.lead_id, "both")}>
                          Both
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h3>Awaiting reply ({awaiting.length})</h3>
        {awaiting.length === 0 ? (
          <p className="muted">No sent leads waiting on a reply.</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Name</th><th>Company</th><th>Sent</th><th>Follow-up due</th><th>Record reply</th></tr>
            </thead>
            <tbody>
              {awaiting.map((l) => (
                <tr key={l.lead_id} className={isFollowUpDue(l) ? "row-due" : ""}>
                  <td>{l.full_name}</td>
                  <td>{l.company_name}</td>
                  <td>{l.outreach_sent_date}</td>
                  <td>
                    {l.follow_up_due}
                    {isFollowUpDue(l) && <span className="due-chip">due</span>}
                  </td>
                  <td>
                    <div className="btn-row">
                      <button className="btn btn-sm btn-ghost" onClick={() => markReply(l.lead_id, "interested")}>
                        Interested
                      </button>
                      <button className="btn btn-sm btn-ghost" onClick={() => markReply(l.lead_id, "follow-up")}>
                        Follow-up
                      </button>
                      <button className="btn btn-sm btn-ghost" onClick={() => markReply(l.lead_id, "rejected")}>
                        Rejected
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
