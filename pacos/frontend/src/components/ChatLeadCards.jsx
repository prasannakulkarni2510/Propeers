import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useStore } from "../store";
import StatusBadge from "./StatusBadge.jsx";
import { LEAD_STAGES, leadStage } from "../lib/pipeline";
import { localToday } from "../lib/dates";

const STAGE = Object.fromEntries(LEAD_STAGES.map((s) => [s.id, s]));
const STATUSES = ["pending", "sent", "replied", "interested", "interview", "offer", "rejected"];
const REPLY_STATUS = { interested: "interested", rejected: "rejected", "follow-up": "replied" };
const ACTIONS = {
  sent: "Mark as sent",
  reply: "Record a reply",
  status: "Set status",
  note: "Add a note",
  delete: "Delete lead",
};

// Two-click delete (no native dialogs), same as Remove on the Leads page.
// Removes the lead from the tracker, the lead sheet and its assets.
export function DeleteLeadButton({ leadId, label = "Delete lead", onDeleted, accent = false }) {
  const deleteLead = useStore((s) => s.deleteLead);
  const [confirming, setConfirming] = useState(0); // when it was armed, or 0
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!confirming) return;
    const id = setTimeout(() => setConfirming(0), 4000); // auto-cancel
    return () => clearTimeout(id);
  }, [confirming]);

  const click = async (e) => {
    // A double-click must never delete: its second click arrives as
    // detail 2, or within a moment of arming. Only a deliberate second
    // click on "Click again to delete" confirms.
    if (!confirming) {
      if (e.detail <= 1) setConfirming(Date.now());
      return;
    }
    if (e.detail > 1 || Date.now() - confirming < 600) return;
    setBusy(true);
    try {
      await deleteLead(leadId);
      onDeleted?.();
    } catch {
      setBusy(false);
      setConfirming(0);
    }
  };
  return (
    <button
      className={`btn btn-sm ${confirming || accent ? "btn-accent" : "btn-ghost"}`}
      title="Remove this lead from the tracker, lead sheet, and assets"
      disabled={busy}
      onClick={click}
    >
      {busy ? "Deleting…" : confirming ? "Click again to delete" : label}
    </button>
  );
}

function Facts({ rec }) {
  return (
    <dl className="record-facts">
      {rec.outreach_sent_date && (<><dt>Sent</dt><dd>{rec.outreach_sent_date}{rec.channel && ` · ${rec.channel}`}</dd></>)}
      {rec.last_reply_date && (<><dt>Reply</dt><dd>{rec.last_reply_date}{rec.reply_intent && ` · ${rec.reply_intent}`}</dd></>)}
      {rec.follow_up_due && (<><dt>Follow up</dt><dd>{rec.follow_up_due}</dd></>)}
      {rec.email && (
        <>
          <dt>Email</dt>
          <dd className="email-addr">
            {rec.email_status === "predicted" && <span className="muted">Likely: </span>}
            {rec.email}
          </dd>
        </>
      )}
      <dt>Assets</dt>
      <dd>{rec.assets.length ? rec.assets.join(", ") : <span className="muted">none yet</span>}</dd>
    </dl>
  );
}

function Links({ rec }) {
  return (
    <>
      <Link className="btn btn-ghost btn-sm" to={`/assets/${rec.lead_id}`}>Open assets</Link>
      <Link className="btn btn-ghost btn-sm" to="/tracker">Tracker</Link>
      {rec.linkedin_url && (
        <a className="btn btn-ghost btn-sm" href={rec.linkedin_url} target="_blank" rel="noopener noreferrer">
          LinkedIn ↗
        </a>
      )}
    </>
  );
}

// A lead the assistant's answer is about, with its live pipeline state, so
// the facts in the reply can be checked at a glance and acted on.
export function RecordCard({ rec, removed, onRemoved }) {
  const role = [rec.job_title, rec.company_name].filter(Boolean).join(" · ");
  if (removed) {
    return (
      <div className="record-card record-removed">
        <span><b>{rec.full_name || rec.company_name}</b> was deleted.</span>
      </div>
    );
  }
  return (
    <div className={`record-card stage-${rec.stage}`}>
      <div className="record-head">
        <div>
          <div className="record-name">
            {rec.full_name || <span className="muted">(no contact yet)</span>}
            {rec.status && <StatusBadge status={rec.status} />}
          </div>
          {role && <div className="muted record-role">{role}</div>}
        </div>
        <span className="record-stage">{STAGE[rec.stage]?.title || rec.stage}</span>
      </div>
      <p className="record-summary">
        {rec.summary}
        {rec.follow_up_overdue && <span className="due-chip">due</span>}
      </p>
      <Facts rec={rec} />
      <div className="btn-row">
        <Links rec={rec} />
        <DeleteLeadButton leadId={rec.lead_id} label="Delete" onDeleted={onRemoved} />
      </div>
    </div>
  );
}

// Where the lead lands if the change is applied: same rules as the backend
// (store.mark_* + retrieval.lead_stage), so the preview matches the result.
function preview(rec, ch) {
  let status = rec.status;
  if (ch.action === "sent") status = "sent";
  if (ch.action === "reply" && ch.intent) status = REPLY_STATUS[ch.intent];
  if (ch.action === "status" && ch.status) status = ch.status;
  const assets_generated = rec.assets.length ? "true" : "";
  return {
    status,
    stage: ch.action === "delete" ? "deleted" : leadStage({ status, assets_generated }),
  };
}

// One lead drawn as a Kanban card.
function MiniCard({ rec, status, ghost }) {
  return (
    <div className={`kb-card cc-card ${ghost ? "cc-ghost" : ""}`}>
      <div className="kb-card-title">
        {rec.full_name || rec.company_name}
        {status && <StatusBadge status={status} />}
      </div>
      <div className="kb-card-sub">
        {[rec.job_title, rec.company_name].filter(Boolean).join(" · ")}
      </div>
    </div>
  );
}

function MiniColumn({ stage, label, children }) {
  const st = STAGE[stage];
  return (
    <div className={`kb-col cc-col ${st?.tone ? `kb-col-${st.tone}` : ""} ${stage === "deleted" ? "cc-col-deleted" : ""}`}>
      <div className="kb-col-head">
        <span className="kb-col-title">{st?.title || "Deleted"}</span>
        <span className="cc-col-label">{label}</span>
      </div>
      {children}
    </div>
  );
}

// The before -> after board for one change.
function MoveBoard({ rec, ch, after }) {
  if (after.stage === rec.stage) {
    return (
      <div className="cc-board cc-board-single">
        <MiniColumn stage={rec.stage} label="stays here">
          <MiniCard rec={rec} status={after.status} />
        </MiniColumn>
      </div>
    );
  }
  return (
    <div className="cc-board">
      <MiniColumn stage={rec.stage} label="now">
        <MiniCard rec={rec} status={rec.status} ghost />
      </MiniColumn>
      <div className="cc-arrow" aria-hidden="true">→</div>
      <MiniColumn stage={after.stage} label="after">
        {after.stage === "deleted" ? (
          <div className="kb-empty">Removed from leads, tracker and assets</div>
        ) : (
          <MiniCard rec={rec} status={after.status} />
        )}
      </MiniColumn>
    </div>
  );
}

// An update the assistant proposed from what the operator said. Every field
// is editable; nothing is saved until Apply (or the two-click Delete).
export function ChangeCard({ change, state, result, onDone }) {
  const applyChatChange = useStore((s) => s.applyChatChange);
  const rec = change.lead;
  const [ch, setCh] = useState({
    action: change.action, channel: change.channel || "email", intent: change.intent || "rejected",
    status: change.status || "interested", date: change.date || "", note: change.note || "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setCh({ ...ch, [k]: e.target.value });

  if (state === "applied" && result) {
    return (
      <div className="change-card change-done">
        <div className="proposal-title">Saved ✓</div>
        <div className="cc-board cc-board-single">
          <MiniColumn stage={result.stage} label="now">
            <MiniCard rec={result} status={result.status} />
          </MiniColumn>
        </div>
        <p className="record-summary">{result.summary}</p>
      </div>
    );
  }
  if (state === "deleted") {
    return <div className="change-card change-done"><b>{rec.full_name || rec.company_name}</b> was deleted.</div>;
  }
  if (state === "dismissed") {
    return <div className="change-card change-done muted">Update dismissed. Nothing was changed.</div>;
  }

  const after = preview(rec, ch);
  const apply = async () => {
    setBusy(true);
    // Blank date = the operator's today, not the server's (it runs on UTC).
    const body = { lead_id: rec.lead_id, action: ch.action, date: ch.date || localToday(), note: ch.note,
      channel: ch.action === "sent" ? ch.channel : "",
      intent: ch.action === "reply" ? ch.intent : "",
      status: ch.action === "status" ? ch.status : "" };
    const res = await applyChatChange(body);
    setBusy(false);
    if (res) onDone("applied", res);
  };
  const canApply = ch.action !== "note" || ch.note.trim();

  return (
    <div className="change-card">
      <div className="change-head">
        <span className="proposal-title">Proposed update</span>
        <span className="muted">Nothing is saved until you apply it</span>
      </div>
      <MoveBoard rec={rec} ch={ch} after={after} />
      <div className="change-fields">
        <label>
          <span>Change</span>
          <select className="select" value={ch.action} onChange={set("action")}>
            {Object.entries(ACTIONS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        {ch.action === "sent" && (
          <label>
            <span>Channel</span>
            <select className="select" value={ch.channel} onChange={set("channel")}>
              <option value="email">Email</option>
              <option value="dm">LinkedIn DM</option>
              <option value="both">Both</option>
            </select>
          </label>
        )}
        {ch.action === "reply" && (
          <label>
            <span>Reply</span>
            <select className="select" value={ch.intent} onChange={set("intent")}>
              <option value="rejected">Rejected</option>
              <option value="interested">Interested</option>
              <option value="follow-up">Asked to follow up</option>
            </select>
          </label>
        )}
        {ch.action === "status" && (
          <label>
            <span>Status</span>
            <select className="select" value={ch.status} onChange={set("status")}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
        )}
        {(ch.action === "sent" || ch.action === "reply") && (
          <label>
            <span>Date</span>
            <input className="input" type="date" max={localToday()} value={ch.date} onChange={set("date")} />
          </label>
        )}
        {ch.action !== "delete" && (
          <label className="change-note">
            <span>Note {ch.action === "note" ? "" : "(optional)"}</span>
            <input className="input" value={ch.note} maxLength={500} placeholder="e.g. AI Engineer role"
              onChange={set("note")} />
          </label>
        )}
      </div>
      {ch.action === "delete" && (
        <p className="change-warn">
          Deleting removes {rec.full_name || "this lead"} from the tracker, the lead sheet and
          its generated assets. This can't be undone.
        </p>
      )}
      <div className="btn-row">
        {ch.action === "delete" ? (
          <DeleteLeadButton leadId={rec.lead_id} accent onDeleted={() => onDone("deleted")} />
        ) : (
          <button className="btn btn-accent btn-sm" disabled={busy || !canApply} onClick={apply}>
            {busy ? "Saving…" : "Apply"}
          </button>
        )}
        <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onDone("dismissed")}>
          Dismiss
        </button>
        <Links rec={rec} />
        {/* Kept apart from Apply so a slip can't delete instead of save. */}
        {ch.action !== "delete" && (
          <span className="change-danger">
            <DeleteLeadButton leadId={rec.lead_id} onDeleted={() => onDone("deleted")} />
          </span>
        )}
      </div>
    </div>
  );
}
