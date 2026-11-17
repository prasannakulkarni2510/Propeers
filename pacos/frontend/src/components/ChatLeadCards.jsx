import { leadSearch } from "./LeadModal.jsx";
import Icon from "./Icon.jsx";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useStore } from "../store";
import StatusBadge from "./StatusBadge.jsx";
import { LEAD_STAGES, leadStage } from "../lib/pipeline";
import { localToday } from "../lib/dates";
import { downloadIcs, followUpEvent, googleCalendarUrl, interviewEvent } from "../lib/calendar";
import CalendarButtons from "./CalendarButtons.jsx";

const STAGE = Object.fromEntries(LEAD_STAGES.map((s) => [s.id, s]));
const STATUSES = ["pending", "sent", "replied", "interested", "interview", "offer", "rejected"];
const REPLY_STATUS = { interested: "interested", rejected: "rejected", "follow-up": "replied" };
const ACTIONS = {
  sent: "Mark as sent",
  reply: "Record a reply",
  status: "Set status",
  note: "Add a note",
  delete: "Delete person",
};

// Two-click delete (no native dialogs), same as Remove on the Leads page.
// Removes the lead from the tracker, the lead sheet and its assets.
export function DeleteLeadButton({ leadId, label = "Delete", onDeleted, accent = false, outlined = false }) {
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
      className={`btn btn-sm ${confirming || accent ? "btn-accent" : outlined ? "btn-danger" : "btn-danger-quiet"}`}
      title="Remove this person and their messages for good"
      disabled={busy}
      onClick={click}
    >
      {outlined && !confirming && !busy && <Icon name="trash" size={14} />}
      {busy ? "Deleting…" : confirming ? "Click again to delete" : label}
    </button>
  );
}

function Links({ rec }) {
  return (
    <>
      <Link className="btn btn-ghost btn-sm" to={{ search: leadSearch(rec.lead_id) }}>Open messages</Link>
            {rec.linkedin_url && (
        <a className="btn btn-ghost btn-sm" href={rec.linkedin_url} target="_blank" rel="noopener noreferrer">
          LinkedIn ↗
        </a>
      )}
    </>
  );
}

const CHANNEL = { email: "Email", dm: "DM", both: "Email and DM" };
// The names the server gives a person's written messages, and which one each opens.
const ASSET_KEY = { "cold email": "cold_email", "LinkedIn DM": "cold_dm", "cover letter": "cover_letter", "CV notes": "cv_notes" };
const STAGE_ICON = { needs_assets: "pencil", ready: "arrow", awaiting: "clock", engaged: "message", closed: "check" };

const initials = (rec) => {
  const words = (rec.full_name || rec.company_name || "?").trim().split(/\s+/);
  return ((words[0]?.[0] || "") + (words.length > 1 ? words[words.length - 1][0] : "")).toUpperCase();
};

// "10 days ago", "today", "in 3 days" for an ISO date, from the operator's day.
function fromToday(iso) {
  const days = Math.round((new Date(`${localToday()}T00:00:00`) - new Date(`${iso}T00:00:00`)) / 86400000);
  if (Number.isNaN(days)) return "";
  if (days === 0) return "today";
  const n = Math.abs(days);
  return days > 0 ? `${n} day${n === 1 ? "" : "s"} ago` : `in ${n} day${n === 1 ? "" : "s"}`;
}

// What the operator should do next with this person, from where they stand.
function nextStep(rec) {
  if (rec.stage === "needs_assets") return "Write messages";
  if (rec.stage === "ready") return "Send it";
  if (rec.stage === "awaiting") return rec.follow_up_overdue ? "Chase now" : "Wait for a reply";
  if (rec.stage === "engaged") {
    if (rec.status === "interview") return "Prepare for the interview";
    if (rec.status === "offer") return "Answer the offer";
    return "Reply to them";
  }
  return "";
}

// The path so far. Only what has happened (or has come due) is ticked.
function timeline(rec) {
  if (!rec.outreach_sent_date) {
    return [
      {
        label: "Messages", done: rec.assets.length > 0,
        detail: rec.assets.length ? `${rec.assets.length} written` : "Not written yet",
      },
      { label: "Sent", done: false, detail: "Not yet" },
    ];
  }
  const steps = [{ label: "Sent", done: true, detail: rec.outreach_sent_date, note: CHANNEL[rec.channel] }];
  if (rec.last_reply_date) {
    steps.push({ label: "Reply", done: true, detail: rec.last_reply_date, note: rec.reply_intent });
  } else if (rec.follow_up_due) {
    steps.push({
      label: "Follow up", done: rec.follow_up_overdue, detail: rec.follow_up_due, note: fromToday(rec.follow_up_due),
    });
  }
  return steps;
}

// A lead the assistant's answer is about, with its live pipeline state, so
// the facts in the reply can be checked at a glance and acted on.
export function RecordCard({ rec, removed, onRemoved }) {
  const role = [rec.job_title, rec.company_name].filter(Boolean).join(", ");
  if (removed) {
    return (
      <div className="record-card record-removed">
        <span><b>{rec.full_name || rec.company_name}</b> was deleted.</span>
      </div>
    );
  }
  const steps = timeline(rec);
  const next = nextStep(rec);
  const reminder = followUpEvent(rec);
  const open = { search: leadSearch(rec.lead_id) };
  return (
    <div className={`record-card stage-${rec.stage}`}>
      <div className="record-head">
        <span className="record-avatar" aria-hidden="true">{initials(rec)}</span>
        <div className="record-who">
          <div className="record-name">{rec.full_name || rec.company_name || "(no contact yet)"}</div>
          {role && <div className="record-role">{role}</div>}
        </div>
        <span className={`record-stage ${rec.follow_up_overdue ? "is-due" : ""}`}>
          <Icon name={STAGE_ICON[rec.stage] || "clock"} size={13} />
          {STAGE[rec.stage]?.title || rec.stage}
        </span>
      </div>

      <div className="record-note">
        <span className="record-ico"><Icon name="message" size={15} /></span>
        <p>
          {rec.summary}
          {rec.follow_up_overdue && <span className="due-chip">Due</span>}
        </p>
      </div>

      <ol className="record-steps">
        {steps.map((st) => (
          <li key={st.label} className={st.done ? "is-done" : ""}>
            <span className="record-step-dot">{st.done && <Icon name="check" size={13} />}</span>
            <span className="record-step-label">{st.label}</span>
            <span className="record-step-detail">{st.detail}</span>
            {st.note && <span className="record-step-detail">({st.note})</span>}
          </li>
        ))}
        <li className="is-next">
          <span className="record-step-dot" />
          <span className="record-step-label">Next</span>
          {next ? (
            <Link className="record-next" to={open}>{next}</Link>
          ) : (
            <span className="record-step-detail">Nothing more to do</span>
          )}
        </li>
      </ol>

      <div className="record-info">
        <div>
          <span className="record-ico"><Icon name="mail" size={14} /></span>
          <div>
            <b>Email</b>
            {rec.email ? (
              <div>
                {rec.email_status === "predicted" && "Likely: "}
                <a className="email-addr record-link" href={`mailto:${rec.email}`} title="Write to them in your mail app">
                  {rec.email}
                </a>
              </div>
            ) : (
              <div className="muted">Not known yet</div>
            )}
          </div>
        </div>
        <div>
          <span className="record-ico"><Icon name="layers" size={14} /></span>
          <div>
            <b>Assets</b>
            <div>
              {rec.assets.length ? (
                rec.assets.map((name, i) => (
                  <span key={name}>
                    {i > 0 && ", "}
                    <Link className="record-link" to={{ search: leadSearch(rec.lead_id, ASSET_KEY[name]) }}>{name}</Link>
                  </span>
                ))
              ) : (
                <Link className="record-link" to={open}>None yet, write them</Link>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="record-actions">
        {rec.linkedin_url && (
          <a className="btn btn-ghost btn-sm" href={rec.linkedin_url} target="_blank" rel="noopener noreferrer">
            <Icon name="linkedin" size={15} /> LinkedIn <Icon name="external" size={13} />
          </a>
        )}
        {reminder?.date && (
          <>
            <a className="btn btn-ghost btn-sm" href={googleCalendarUrl(reminder)} target="_blank" rel="noopener noreferrer">
              <Icon name="calendar" size={15} /> Remind me
            </a>
            <button
              className="btn btn-ghost btn-sm"
              title="Download the reminder for Outlook or Apple Calendar"
              onClick={() => downloadIcs(reminder)}
            >
              <Icon name="download" size={15} /> .ics
            </button>
          </>
        )}
        <DeleteLeadButton leadId={rec.lead_id} label="Delete" onDeleted={onRemoved} outlined />
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
        {[rec.job_title, rec.company_name].filter(Boolean).join(", ")}
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
      <div className="cc-arrow" aria-hidden="true"><Icon name="arrow" size={20} /></div>
      <MiniColumn stage={after.stage} label="after">
        {after.stage === "deleted" ? (
          <div className="kb-empty">Removed, with their messages</div>
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
    eventDate: change.event_date || "", eventTime: change.event_time || "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setCh({ ...ch, [k]: e.target.value });
  // Editing the interview's date/time keeps the "Interview on … at …" note
  // in step with it.
  const setEvent = (k) => (e) => {
    const next = { ...ch, [k]: e.target.value };
    const when = next.eventDate
      ? `Interview on ${next.eventDate}${next.eventTime ? ` at ${next.eventTime}` : ""}` : "";
    const rest = ch.note.replace(/^Interview on \S+( at \d{2}:\d{2})?,?\s*/, "");
    next.note = [when, rest].filter(Boolean).join(", ");
    setCh(next);
  };
  const isInterview = ch.action === "status" && ch.status === "interview";
  const interview = isInterview && ch.eventDate
    ? interviewEvent(rec, ch.eventDate, ch.eventTime, ch.note) : null;

  if (state === "applied" && result) {
    return (
      <div className="change-card change-done">
        <div className="proposal-title">Saved</div>
        <div className="cc-board cc-board-single">
          <MiniColumn stage={result.stage} label="now">
            <MiniCard rec={result} status={result.status} />
          </MiniColumn>
        </div>
        <p className="record-summary">{result.summary}</p>
        <div className="btn-row">
          {result.event
            ? <CalendarButtons event={result.event} />
            : <CalendarButtons event={followUpEvent(result)} label="Remind me to follow up" />}
        </div>
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
    if (res) onDone("applied", { ...res, event: interview });
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
        {isInterview && (
          <>
            <label>
              <span>Interview date</span>
              <input className="input" type="date" value={ch.eventDate} onChange={setEvent("eventDate")} />
            </label>
            <label>
              <span>Time</span>
              <input className="input" type="time" value={ch.eventTime} onChange={setEvent("eventTime")} />
            </label>
          </>
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
          Deleting removes {rec.full_name || "this person"} and the messages written
          for them. This can’t be undone.
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
        <CalendarButtons event={interview} />
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
