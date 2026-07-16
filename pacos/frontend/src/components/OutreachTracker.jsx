import { useMemo, useState } from "react";
import { useApprovals } from "../hooks/useApprovals";
import StatusBadge from "./StatusBadge.jsx";

const FLOW = ["pending", "sent", "replied", "interested", "interview", "offer", "rejected"];
const PAGE_SIZE = 25;

// CRM — sent/replied/follow-up (docx: OutreachTracker.jsx). Full pipeline table
// with an inline status selector per lead. Search + pagination keep it usable
// when the whole pipeline runs to hundreds of leads.
export default function OutreachTracker({ leads }) {
  const { markStatus } = useApprovals();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const inPipeline = useMemo(() => leads.filter((l) => l.status), [leads]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return inPipeline.filter((l) => {
      if (status && l.status !== status) return false;
      if (!needle) return true;
      return [l.full_name, l.company_name].some((v) =>
        (v || "").toLowerCase().includes(needle),
      );
    });
  }, [inPipeline, q, status]);

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
        <select className="select" value={status} onChange={onFilter(setStatus)}>
          <option value="">All statuses</option>
          {FLOW.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="muted">
          {filtered.length} of {inPipeline.length} in pipeline
        </span>
      </div>

      {filtered.length === 0 ? (
        <p className="muted">No leads match your search.</p>
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
      )}

      {pageCount > 1 && (
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
