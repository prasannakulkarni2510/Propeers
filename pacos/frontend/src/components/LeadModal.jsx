import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useStore } from "../store";
import { isFollowUpDue, leadStage } from "../lib/pipeline";
import { followUpEvent } from "../lib/calendar";
import AssetViewer from "./AssetViewer.jsx";
import CalendarButtons from "./CalendarButtons.jsx";
import { DeleteLeadButton } from "./ChatLeadCards.jsx";
import StatusBadge from "./StatusBadge.jsx";
import Icon from "./Icon.jsx";

// A lead opens in a panel beside whatever page you are on. The open lead
// lives in the URL (?lead=<id>), so Back closes it and a link to it can be
// bookmarked.
// `asset` ("cold_email", "cold_dm", "cover_letter", "cv_notes") picks the message shown first.
export const leadSearch = (leadId, asset = "") =>
  `?lead=${encodeURIComponent(leadId)}${asset ? `&asset=${asset}` : ""}`;

const STATUSES = ["pending", "sent", "replied", "interested", "interview", "offer", "rejected"];

function Email({ lead }) {
  const email = lead.predicted_email || lead.email;
  const [copied, setCopied] = useState(false);
  if (!email) return null;
  const predicted = lead.email_status === "predicted";
  const copy = async () => {
    await navigator.clipboard.writeText(email);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <span className="email-cell">
      {/* A predicted address always reads as likely, never as confirmed. */}
      {predicted && <span className="muted">Likely</span>}
      <span className="email-addr">{email}</span>
      <button className="copy-chip" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
    </span>
  );
}

// The one thing to do with this lead now. Drafts that still need writing or
// sending are handled by the draft viewer below; this covers what comes after.
function NextStep({ lead }) {
  const markReply = useStore((s) => s.markReply);
  const stage = leadStage(lead);
  if (stage !== "awaiting") return null;
  const due = isFollowUpDue(lead);
  return (
    <div className={`next-step ${due ? "is-due" : ""}`}>
      <h3>{due ? "Follow-up is due" : "Waiting for a reply"}</h3>
      <p>
        Sent {lead.outreach_sent_date || "earlier"}
        {lead.channel ? ` by ${lead.channel === "dm" ? "LinkedIn DM" : lead.channel}` : ""}
        {lead.follow_up_due ? `. Follow up on ${lead.follow_up_due}.` : "."} Heard back?
      </p>
      <div className="btn-row">
        <button className="btn btn-accent btn-sm" onClick={() => markReply(lead.lead_id, "interested")}>They’re interested</button>
        <button className="btn btn-sm" onClick={() => markReply(lead.lead_id, "follow-up")}>Asked to follow up</button>
        <button className="btn btn-sm" onClick={() => markReply(lead.lead_id, "rejected")}>Rejected</button>
        <CalendarButtons event={followUpEvent(lead)} label="Remind me" />
      </div>
    </div>
  );
}

export default function LeadPanel() {
  const [params, setParams] = useSearchParams();
  const leadId = params.get("lead") || "";
  const leads = useStore((s) => s.leads);
  const loading = useStore((s) => s.loading);
  const markStatus = useStore((s) => s.markStatus);
  const closeRef = useRef(null);
  const lead = leads.find((l) => l.lead_id === leadId);

  const close = () => {
    const next = new URLSearchParams(params);
    next.delete("lead");
    next.delete("asset");
    setParams(next);
  };

  useEffect(() => {
    if (!leadId) return;
    // Focus moves into the panel, the page behind stops scrolling, and focus
    // returns to whatever opened it when it closes.
    const opener = document.activeElement;
    closeRef.current?.focus();
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";
    const onKey = (e) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      opener?.focus?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leadId]);

  if (!leadId) return null;
  const titleId = "lead-panel-title";

  return (
    <div className="drawer-scrim" onClick={(e) => e.target === e.currentTarget && close()}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <button ref={closeRef} type="button" className="icon-btn drawer-close" aria-label="Close" onClick={close}>
          <Icon name="close" size={18} />
        </button>
        {lead ? (
          <>
            <header className="lead-head">
              <h2 className="lead-head-name" id={titleId}>
                {lead.full_name || lead.company_name}
                {lead.status && <StatusBadge status={lead.status} />}
              </h2>
              <div className="lead-head-role">
                {[lead.job_title, lead.full_name && lead.company_name, lead.city].filter(Boolean).join(", ")}
              </div>
              <div className="lead-head-links">
                <Email lead={lead} />
                {lead.linkedin_url && (
                  <a className="link" href={lead.linkedin_url} target="_blank" rel="noopener noreferrer">
                    LinkedIn profile
                  </a>
                )}
              </div>
            </header>
            <NextStep lead={lead} />
            <AssetViewer leadId={leadId} lead={lead} />
            <footer className="drawer-foot">
              {lead.status && (
                <select
                  className="select"
                  aria-label="Status"
                  value={lead.status}
                  onChange={(e) => markStatus(lead.lead_id, e.target.value)}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>
                  ))}
                </select>
              )}
              <Link
                className="btn btn-ghost btn-sm"
                to={`/find?${new URLSearchParams({ company: lead.company_name || "", role: lead.job_title || "", city: lead.city || "" })}`}
              >
                Find people at {lead.company_name || "this company"}
              </Link>
              <span className="spacer">
                <DeleteLeadButton leadId={lead.lead_id} label="Delete" onDeleted={close} />
              </span>
            </footer>
          </>
        ) : (
          <div className="empty-state">
            <h2 className="lead-head-name" id={titleId}>
              {loading || leads.length === 0 ? "Loading…" : "Person not found"}
            </h2>
            {!loading && leads.length > 0 && <p className="muted">It may have been deleted.</p>}
          </div>
        )}
      </aside>
    </div>
  );
}
