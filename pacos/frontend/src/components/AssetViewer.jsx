import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useStore } from "../store";
import { isReadyToSend } from "../lib/pipeline";

const LABELS = {
  "cold_email.txt": "Cold Email",
  "cold_dm.txt": "Cold DM",
  "cover_letter.txt": "Cover Letter",
  "cv_notes.txt": "CV Notes",
};

// LinkedIn caps connection-request notes at 300 characters (200 on free
// accounts), so the DM gets a visible budget.
const DM_LIMIT = 300;

// The pipeline writes a "(not generated — …)" placeholder for skipped assets.
const isSkipped = (content) => (content || "").startsWith("(not generated");

function Counter({ name, content }) {
  const chars = content.length;
  const words = content.trim() ? content.trim().split(/\s+/).length : 0;
  const over = name === "cold_dm.txt" && chars > DM_LIMIT;
  return (
    <span className={`asset-count ${over ? "over" : ""}`}>
      {words} words · {chars}
      {name === "cold_dm.txt" ? ` / ${DM_LIMIT}` : ""} chars
      {over && " · too long for a LinkedIn connection note"}
    </span>
  );
}

// Assets per lead (docx: AssetViewer.jsx). Read the four files; copy to clipboard.
export default function AssetViewer({ leadId, lead }) {
  const [data, setData] = useState(null);
  const [active, setActive] = useState("cold_email.txt");
  const [error, setError] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const setToast = useStore((s) => s.setToast);
  const generate = useStore((s) => s.generate);
  const generating = useStore((s) => s.generating);
  const markSent = useStore((s) => s.markSent);

  const load = () => {
    setData(null);
    setError("");
    return api
      .assets(leadId)
      .then((d) => {
        setData(d);
        // Open on the first asset that actually has content (DM-only leads
        // have a placeholder cold email).
        const first = d.files.find((f) => !isSkipped(f.content));
        if (first) setActive(first.name);
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    if (leadId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leadId]);

  if (!leadId) return <p className="muted">Pick a lead above to see its outreach drafts.</p>;
  if (error) return <div className="banner">{error}</div>;
  if (!data) return <p className="muted">Loading assets…</p>;

  if (!data.generated) {
    const isJob = lead?.lead_type === "job";
    const buildOne = async (dry_run) => {
      try {
        await generate({ lead_id: leadId, dry_run });
        await load();
      } catch (_) {}
    };
    return (
      <div className="empty-state">
        <p>No assets for this lead yet.</p>
        {isJob ? (
          <p className="muted">
            This is a job posting with no contact person. Find the hiring manager
            or recruiter from Discovery, add them as a person, then generate.
          </p>
        ) : (
          <div className="btn-row" style={{ justifyContent: "center" }}>
            <button className="btn btn-accent" disabled={generating} onClick={() => buildOne(false)}>
              {generating ? "Generating…" : "Generate for this lead"}
            </button>
            <button className="btn btn-ghost" disabled={generating} onClick={() => buildOne(true)}>
              Dry-run
            </button>
          </div>
        )}
      </div>
    );
  }

  const current = data.files.find((f) => f.name === active) || data.files[0];
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(current.content);
      setToast(`Copied ${LABELS[current.name]} to clipboard`);
    } catch (_) {
      setToast("Copy failed. Select and copy manually");
    }
  };

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const fresh = await api.regenerateAsset(leadId, current.name);
      setData(fresh);
      setToast(`Regenerated ${LABELS[current.name]}`);
    } catch (e) {
      setToast(`Regenerate failed: ${e.message}`);
    } finally {
      setRegenerating(false);
    }
  };

  const skipped = isSkipped(current.content);
  const canMark = lead && isReadyToSend(lead);

  return (
    <div className="asset-layout">
      <div className="asset-list" role="tablist" aria-label="Assets">
        {data.files.map((f) => (
          <button
            key={f.name}
            role="tab"
            aria-selected={f.name === active}
            className={`asset-item ${f.name === active ? "active" : ""} ${isSkipped(f.content) ? "skipped" : ""}`}
            onClick={() => setActive(f.name)}
          >
            {LABELS[f.name] || f.name}
            {isSkipped(f.content) && <span className="asset-item-note">skipped</span>}
          </button>
        ))}
      </div>
      <div>
        <div className="copy-bar">
          <div>
            <b>{LABELS[current.name]}</b>
            {!skipped && !regenerating && <Counter name={current.name} content={current.content} />}
          </div>
          <div className="copy-bar-actions">
            <button
              className="btn btn-sm btn-ghost"
              onClick={regenerate}
              disabled={regenerating || skipped}
              title="Rewrite this asset: reuses the same hook, different copy"
            >
              {regenerating ? "Regenerating…" : "Regenerate"}
            </button>
            <button className="btn btn-sm btn-accent" onClick={copy} disabled={skipped}>
              Copy
            </button>
          </div>
        </div>
        <div className={`asset-body ${skipped ? "muted" : ""}`}>
          {regenerating ? "Regenerating…" : current.content || "(empty)"}
        </div>
        {canMark && (
          <div className="mark-bar">
            <span className="muted">Sent it? Mark it so the follow-up clock starts:</span>
            <div className="btn-row">
              {lead.has_email && (
                <button className="btn btn-sm" onClick={() => markSent(leadId, "email")}>Email</button>
              )}
              <button className="btn btn-sm" onClick={() => markSent(leadId, "dm")}>DM</button>
              {lead.has_email && (
                <button className="btn btn-sm btn-accent" onClick={() => markSent(leadId, "both")}>Both</button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
