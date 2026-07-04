import { useState } from "react";
import { useStore } from "../store";
import AgentStatus from "./AgentStatus.jsx";

// Supervisor overview (docx: Dashboard.jsx): stat tiles + generate trigger.
export default function Dashboard() {
  const { stats, generate } = useStore();
  const [busy, setBusy] = useState(false);
  const [reviewHooks, setReviewHooks] = useState(false);

  const tiles = [
    { label: "Leads", value: stats?.total ?? "—" },
    { label: "With assets", value: stats?.with_assets ?? "—" },
    { label: "Follow-ups due", value: stats?.followups_due ?? "—" },
    {
      label: "Interested",
      value: stats?.status_counts?.interested ?? 0,
    },
    { label: "Interviews", value: stats?.status_counts?.interview ?? 0 },
  ];

  const run = async (dry_run) => {
    setBusy(true);
    try {
      await generate({ dry_run, review_hooks: reviewHooks });
    } catch (_) {
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="stat-grid">
        {tiles.map((t) => (
          <div className="stat" key={t.label}>
            <div className="stat-value">{t.value}</div>
            <div className="stat-label">{t.label}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        <h3>Generate outreach (Layer 1)</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Runs one Nemotron call per lead → four files each. Use dry-run to
          produce templates without an API key. Nothing is ever sent.
        </p>
        <div className="btn-row">
          <button className="btn btn-accent" disabled={busy} onClick={() => run(false)}>
            {busy ? "Generating…" : "Generate with Nemotron"}
          </button>
          <button className="btn btn-ghost" disabled={busy} onClick={() => run(true)}>
            Dry-run (templates)
          </button>
          <label className="muted" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="checkbox"
              checked={reviewHooks}
              onChange={(e) => setReviewHooks(e.target.checked)}
            />
            Review hooks
          </label>
        </div>
        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          Pipeline: personalization agent → 4 asset agents (cold email skipped when
          a lead has no email). Watch the agent board below light up as it runs.
        </p>
      </div>

      <AgentStatus />
    </div>
  );
}
