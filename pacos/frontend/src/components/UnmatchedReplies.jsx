import { useState } from "react";
import { useStore } from "../store";

// Unmatched recruiter replies: the inbox monitor couldn't map these to a lead by
// exact email, so the operator associates them by hand (ADR: no fuzzy matching).
export default function UnmatchedReplies() {
  const { unmatched, leads, associate } = useStore();
  const [picks, setPicks] = useState({});

  if (!unmatched?.length) {
    return (
      <div className="panel">
        <h3>Unmatched replies (0)</h3>
        <p className="muted">
          Nothing to associate. The inbox monitor auto-matches replies whose sender
          email equals a lead's; anything else lands here.
        </p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3>Unmatched replies ({unmatched.length})</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        The monitor classified an intent but couldn't match the sender to a lead.
        Pick the right lead to record the reply.
      </p>
      <table className="table">
        <thead>
          <tr><th>From</th><th>Subject</th><th>Intent</th><th>Associate with lead</th></tr>
        </thead>
        <tbody>
          {unmatched.map((r) => (
            <tr key={r.id}>
              <td>{r.sender}</td>
              <td>{r.subject}</td>
              <td><span className="tag">{r.intent}</span></td>
              <td>
                <div className="btn-row">
                  <select
                    className="select"
                    value={picks[r.id] || ""}
                    onChange={(e) => setPicks({ ...picks, [r.id]: e.target.value })}
                  >
                    <option value="">— pick lead —</option>
                    {leads.map((l) => (
                      <option key={l.lead_id} value={l.lead_id}>
                        {l.full_name} — {l.company_name}
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn btn-sm btn-accent"
                    disabled={!picks[r.id]}
                    onClick={() => associate(r.id, picks[r.id])}
                  >
                    Link
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
