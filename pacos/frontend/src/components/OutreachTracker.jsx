import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useApprovals } from "../hooks/useApprovals";
import StatusBadge from "./StatusBadge.jsx";
import KanbanBoard, { ViewToggle, useViewMode } from "./KanbanBoard.jsx";
import { isFollowUpDue } from "../lib/pipeline";

const FLOW = ["pending", "sent", "replied", "interested", "interview", "offer", "rejected"];
const PAGE_SIZE = 25;

const STATUS_TONE = { interested: "ok", interview: "accent", offer: "ok" };

function StatusPicker({ lead, onChange }) {
  return (
    <select
      className="select"
      aria-label={`Status for ${lead.full_name}`}
      value={lead.status}
      onChange={(e) => onChange(lead, e.target.value)}
    >
      {FLOW.map((s) => (
        <option key={s} value={s}>{s}</option>
      ))}
    </select>
  );
}

function TrackerCard({ lead, onChange }) {
  const due = isFollowUpDue(lead);
  return (
    <div className={`kb-lead ${due ? "kb-due" : ""}`}>
      <div className="kb-card-title">
        <Link to={`/assets/${lead.lead_id}`}>{lead.full_name || lead.company_name}</Link>
      </div>
      <div className="kb-card-sub">{lead.company_name}</div>
      <div className="kb-card-meta">
        {lead.channel && <span className="tag">{lead.channel}</span>}
        {lead.outreach_sent_date && <span>Sent {lead.outreach_sent_date}</span>}
        {lead.reply_intent && <span>Reply: {lead.reply_intent}</span>}
      </div>
      {lead.follow_up_due && (
        <div className="kb-card-meta">
          Follow up {lead.follow_up_due}
          {due && <span className="due-chip">due</span>}
        </div>
      )}
      <StatusPicker lead={lead} onChange={onChange} />
    </div>
  );
}

// CRM — sent/replied/follow-up (docx: OutreachTracker.jsx). Full pipeline table
// with an inline status selector per lead. Search + pagination keep it usable
// when the whole pipeline runs to hundreds of leads.
export default function OutreachTracker({ leads }) {
  const { markStatus } = useApprovals();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [view, setView] = useViewMode("tracker");
  // Optimistic moves: show the card in its new column right away, then let the
  // refreshed lead list take over once the backend has saved it.
  const [moved, setMoved] = useState({});
  useEffect(() => setMoved({}), [leads]);

  const change = async (lead, next) => {
    if (next === lead.status) return;
    setMoved((m) => ({ ...m, [lead.lead_id]: next }));
    // The store reports failures in the toast and returns nothing; put the
    // card back where it was.
    if (!(await markStatus(lead.lead_id, next))) {
      setMoved(({ [lead.lead_id]: _, ...rest }) => rest);
    }
  };

  const inPipeline = useMemo(
    () =>
      leads
        .filter((l) => l.status)
        .map((l) => (moved[l.lead_id] ? { ...l, status: moved[l.lead_id] } : l)),
    [leads, moved],
  );

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return inPipeline.filter((l) => {
      if (view === "list" && status && l.status !== status) return false;
      if (!needle) return true;
      return [l.full_name, l.company_name].some((v) =>
        (v || "").toLowerCase().includes(needle),
      );
    });
  }, [inPipeline, q, status, view]);

  const columns = useMemo(
    () =>
      FLOW.map((s) => ({
        id: s,
        title: s[0].toUpperCase() + s.slice(1),
        tone: STATUS_TONE[s],
        items: filtered
          .filter((l) => l.status === s)
          // Overdue follow-ups float to the top of their column.
          .sort((a, b) => isFollowUpDue(b) - isFollowUpDue(a)),
      })),
    [filtered],
  );

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const start = (current - 1) * PAGE_SIZE;
  const rows = filtered.slice(start, start + PAGE_SIZE);

  const onFilter = (setter) => (e) => {
    setter(e.target.value);
    setPage(1);
  };

  if (!inPipeline.length) return <p className="muted">No leads in the pipeline yet.</p>;

  return (
    <>
      <div className="toolbar">
        <input
          className="input"
          style={{ maxWidth: 260 }}
          placeholder="Search name or company…"
          value={q}
          onChange={onFilter(setQ)}
        />
        {view === "list" && (
          <select className="select" value={status} onChange={onFilter(setStatus)}>
            <option value="">All statuses</option>
            {FLOW.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        )}
        <ViewToggle mode={view} setMode={setView} />
        <span className="muted">
          {filtered.length} of {inPipeline.length} in pipeline
        </span>
      </div>

      {view === "board" && filtered.length > 0 && (
        <p className="muted kb-tip">Drag a card to another column to change its status.</p>
      )}
      {filtered.length === 0 ? (
        <p className="muted">No leads match your search.</p>
      ) : view === "board" ? (
        <KanbanBoard
          columns={columns}
          getId={(l) => l.lead_id}
          renderCard={(l) => <TrackerCard lead={l} onChange={change} />}
          onMove={(l, _from, to) => change(l, to)}
        />
      ) : (
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
            <tr key={l.lead_id} className={isFollowUpDue(l) ? "row-due" : ""}>
              <td>{l.full_name}</td>
              <td>{l.company_name}</td>
              <td><StatusBadge status={l.status} /></td>
              <td>{l.outreach_sent_date || "-"}</td>
              <td>{l.channel || "-"}</td>
              <td>{l.last_reply_date || "-"}</td>
              <td>{l.reply_intent || "-"}</td>
              <td>
                {l.follow_up_due || "-"}
                {isFollowUpDue(l) && <span className="due-chip">due</span>}
              </td>
              <td>
                <StatusPicker lead={l} onChange={change} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
        </div>
      )}

      {view === "list" && pageCount > 1 && (
        <div className="pagination">
          <span className="muted">
            Showing {start + 1}–{start + rows.length} of {filtered.length}
          </span>
          <button
            className="btn btn-ghost btn-sm"
            disabled={current <= 1}
            onClick={() => setPage(current - 1)}
          >
            Prev
          </button>
          <span className="muted">Page {current} / {pageCount}</span>
          <button
            className="btn btn-ghost btn-sm"
            disabled={current >= pageCount}
            onClick={() => setPage(current + 1)}
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}
