import { Link } from "react-router-dom";
import { useApprovals } from "../hooks/useApprovals";
import KanbanBoard from "./KanbanBoard.jsx";
import { isAwaitingReply, isFollowUpDue, isReadyToSend } from "../lib/pipeline";

function ReadyCard({ lead, markSent }) {
  return (
    <div className="kb-lead">
      <div className="kb-card-title">{lead.full_name}</div>
      <div className="kb-card-sub">{lead.company_name}</div>
      <div className="kb-card-meta">
        <span className="tag">{lead.has_email ? "email + dm" : "dm-only"}</span>
        <Link className="link" to={`/assets/${lead.lead_id}`}>Open drafts →</Link>
      </div>
      <div className="kb-card-label">Mark sent as</div>
      <div className="btn-row">
        {lead.has_email && (
          <button className="btn btn-sm" onClick={() => markSent(lead.lead_id, "email")}>Email</button>
        )}
        <button className="btn btn-sm" onClick={() => markSent(lead.lead_id, "dm")}>DM</button>
        {lead.has_email && (
          <button className="btn btn-sm btn-accent" onClick={() => markSent(lead.lead_id, "both")}>Both</button>
        )}
      </div>
    </div>
  );
}

function AwaitingCard({ lead, markReply }) {
  const due = isFollowUpDue(lead);
  return (
    <div className={`kb-lead ${due ? "kb-due" : ""}`}>
      <div className="kb-card-title">
        <Link to={`/assets/${lead.lead_id}`}>{lead.full_name}</Link>
      </div>
      <div className="kb-card-sub">{lead.company_name}</div>
      <div className="kb-card-meta">
        {lead.outreach_sent_date && <span>Sent {lead.outreach_sent_date}</span>}
        {lead.follow_up_due && <span>Follow up {lead.follow_up_due}</span>}
        {due && <span className="due-chip">due</span>}
      </div>
      <div className="kb-card-label">Record reply</div>
      <div className="btn-row">
        <button className="btn btn-sm btn-ghost" onClick={() => markReply(lead.lead_id, "interested")}>
          Interested
        </button>
        <button className="btn btn-sm btn-ghost" onClick={() => markReply(lead.lead_id, "follow-up")}>
          Follow-up
        </button>
        <button className="btn btn-sm btn-ghost" onClick={() => markReply(lead.lead_id, "rejected")}>
          Rejected
        </button>
      </div>
    </div>
  );
}

// Manual approve/act queue (docx: ApprovalQueue.jsx) as a board: leads with
// assets wait to be sent, sent leads wait for a reply, and overdue ones get
// their own column so they're the first thing to chase. Cards move by their
// buttons (the channel/intent matters), not by dragging.
export default function ApprovalQueue({ leads }) {
  const { markSent, markReply } = useApprovals();

  const byDue = (a, b) => (a.follow_up_due || "9").localeCompare(b.follow_up_due || "9");
  const awaiting = leads.filter(isAwaitingReply).sort(byDue);

  const columns = [
    {
      id: "ready",
      title: "Ready to send",
      tone: "accent",
      hint: "Copy the drafts, send them by hand, then mark the channel. PACOS never sends for you.",
      empty: "Nothing pending. Generate assets first.",
      items: leads.filter(isReadyToSend),
    },
    {
      id: "due",
      title: "Follow-up due",
      tone: "warn",
      hint: "Sent, no reply, and the follow-up date has passed.",
      empty: "No follow-ups due.",
      items: awaiting.filter(isFollowUpDue),
    },
    {
      id: "awaiting",
      title: "Awaiting reply",
      hint: "Sent and still inside the follow-up window.",
      empty: "No sent leads waiting on a reply.",
      items: awaiting.filter((l) => !isFollowUpDue(l)),
    },
  ];

  return (
    <KanbanBoard
      columns={columns}
      getId={(l) => l.lead_id}
      renderCard={(l, col) =>
        col === "ready" ? (
          <ReadyCard lead={l} markSent={markSent} />
        ) : (
          <AwaitingCard lead={l} markReply={markReply} />
        )
      }
    />
  );
}
