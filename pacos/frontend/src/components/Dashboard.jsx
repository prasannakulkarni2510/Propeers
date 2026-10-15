import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useStore } from "../store";
import { pipelineCounts } from "../lib/pipeline";
import AgentStatus from "./AgentStatus.jsx";

// The operator's loop, in order. Each step is "done" from live data, and the
// first unfinished one is highlighted as the thing to do next.
function NextSteps({ leads, counts, cvIsSample }) {
  const steps = [
    {
      label: "Add your real CV",
      done: cvIsSample === false,
      hint: "Upload it above. Assets are grounded in it.",
    },
    {
      label: "Add leads",
      done: leads.length > 0,
      hint: "Paste a JD, add manually, or auto-import from Discovery.",
      to: "/leads",
    },
    {
      label: "Generate outreach",
      done: leads.length > 0 && counts.needAssets === 0,
      hint: `${counts.needAssets} lead${counts.needAssets === 1 ? "" : "s"} still need assets.`,
    },
    {
      label: "Send and mark as sent",
      done: counts.ready === 0 && leads.some((l) => l.status && l.status !== "pending"),
      hint: `${counts.ready} ready to send. Copy from Assets, send by hand.`,
      to: "/approvals",
    },
    {
      label: "Chase follow-ups",
      done: counts.due === 0 && counts.awaiting > 0,
      hint: counts.due
        ? `${counts.due} follow-up${counts.due === 1 ? "" : "s"} due today.`
        : "Replies and follow-ups show up in the Tracker.",
      to: "/tracker",
    },
  ];
  // cvIsSample is null until the CV has loaded; don't flash a wrong "next".
  const next = cvIsSample === null ? -1 : steps.findIndex((s) => !s.done);

  return (
    <div className="panel">
      <h3>Your outreach loop</h3>
      <ol className="steps">
        {steps.map((s, i) => (
          <li key={s.label} className={`step ${s.done ? "done" : ""} ${i === next ? "next" : ""}`}>
            <span className="step-num">{s.done ? "✓" : i + 1}</span>
            <div className="step-body">
              <div className="step-label">
                {s.to && !s.done ? <Link to={s.to}>{s.label}</Link> : s.label}
              </div>
              {i === next && <div className="step-hint">{s.hint}</div>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

// Supervisor overview (docx: Dashboard.jsx): stat tiles + generate trigger.
export default function Dashboard() {
  const { stats, generate, leads, cvIsSample } = useStore();
  // Global so leaving and returning to this tab still shows the run in progress.
  const busy = useStore((s) => s.generating);
  const [reviewHooks, setReviewHooks] = useState(false);
  const counts = useMemo(() => pipelineCounts(leads), [leads]);

  const tiles = [
    { label: "Leads", value: stats?.total ?? "-", to: "/leads" },
    { label: "With assets", value: stats?.with_assets ?? "-", to: "/assets" },
    { label: "Ready to send", value: counts.ready, to: "/approvals", accent: counts.ready > 0 },
    { label: "Follow-ups due", value: stats?.followups_due ?? "-", to: "/tracker", warn: counts.due > 0 },
    { label: "Interested", value: stats?.status_counts?.interested ?? 0, to: "/tracker" },
    { label: "Interviews", value: stats?.status_counts?.interview ?? 0, to: "/tracker" },
  ];

  const run = async (dry_run) => {
    try {
      await generate({ dry_run, review_hooks: reviewHooks });
    } catch (_) {}
  };

  return (
    <div>
      <div className="stat-grid">
        {tiles.map((t) => (
          <Link
            className={`stat ${t.accent ? "stat-accent" : ""} ${t.warn ? "stat-warn" : ""}`}
            key={t.label}
            to={t.to}
          >
            <div className="stat-value">{t.value}</div>
            <div className="stat-label">{t.label}</div>
          </Link>
        ))}
      </div>

      <NextSteps leads={leads} counts={counts} cvIsSample={cvIsSample} />

      <div className="panel">
        <h3>Generate outreach (Layer 1)</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Builds assets only for leads that don't have them yet
          {counts.needAssets > 0 && <> (<b>{counts.needAssets}</b> right now)</>}.
          One Nemotron call per lead → four files each. To rebuild an existing
          lead, use Regenerate on the Assets page. Dry-run produces templates
          without an API key. Nothing is ever sent.
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
