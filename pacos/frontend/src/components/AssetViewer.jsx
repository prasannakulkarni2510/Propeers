import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useStore } from "../store";
import { isReadyToSend } from "../lib/pipeline";

const LABELS = {
  "cold_email.txt": "Email",
  "cold_dm.txt": "LinkedIn DM",
  "cover_letter.txt": "Cover letter",
  "cv_notes.txt": "CV notes",
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
      {name === "cold_dm.txt" ? `${chars} of ${DM_LIMIT} characters` : `${words} words`}
      {over && ", too long for a LinkedIn connection note"}
    </span>
  );
}

// A lead's four drafts: read, copy, rewrite, and say when one was sent.
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

  if (error) return <div className="banner">{error}</div>;
  if (!data) return <p className="muted">Loading drafts…</p>;

  if (!data.generated) {
    const isJob = lead?.lead_type === "job";
    const buildOne = async () => {
      try {
        await generate({ lead_id: leadId });
        await load();
      } catch (_) {}
    };
    return (
      <div className="next-step">
        <h3>{isJob ? "No contact person yet" : "No messages yet"}</h3>
        {isJob ? (
          <p style={{ marginBottom: 0 }}>
            This is a job posting. Find the hiring manager or recruiter below, add them as a lead, and write to them.
          </p>
        ) : (
          <>
            <p>PACOS writes an email, a LinkedIn DM, a cover letter and CV notes from your CV. Nothing is sent.</p>
            <button className="btn btn-accent btn-sm" disabled={generating} onClick={buildOne}>
              {generating ? "Writing…" : "Write messages"}
            </button>
          </>
        )}
      </div>
    );
  }

  const current = data.files.find((f) => f.name === active) || data.files[0];
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(current.content);
      setToast(`${LABELS[current.name]} copied.`);
    } catch (_) {
      setToast("Couldn’t copy. Select the text and copy it.");
    }
  };

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const fresh = await api.regenerateAsset(leadId, current.name);
      setData(fresh);
      setToast(`${LABELS[current.name]} rewritten.`);
    } catch (e) {
      setToast(`Couldn’t rewrite it: ${e.message}`);
    } finally {
      setRegenerating(false);
    }
  };

  const skipped = isSkipped(current.content);
  const canMark = lead && isReadyToSend(lead);

  return (
    <div>
      {canMark && (
        <div className="next-step">
          <h3>Ready to send</h3>
          <p>Copy a message, send it yourself, then say how you sent it. That starts the follow-up clock.</p>
          <div className="btn-row">
            {lead.has_email && (
              <button className="btn btn-sm" onClick={() => markSent(leadId, "email")}>Sent by email</button>
            )}
            <button className="btn btn-sm" onClick={() => markSent(leadId, "dm")}>Sent by DM</button>
            {lead.has_email && (
              <button className="btn btn-sm" onClick={() => markSent(leadId, "both")}>Sent both</button>
            )}
          </div>
        </div>
      )}
      <div className="asset-list" role="tablist" aria-label="Drafts">
        {data.files.map((f) => (
          <button
            key={f.name}
            role="tab"
            aria-selected={f.name === active}
            className={`asset-item ${f.name === active ? "active" : ""}`}
            onClick={() => setActive(f.name)}
          >
            {LABELS[f.name] || f.name}
            {isSkipped(f.content) && <span className="asset-item-note">none</span>}
          </button>
        ))}
      </div>
      <div className={`asset-body ${skipped ? "muted" : ""}`}>
        {regenerating ? "Rewriting…" : current.content || "(empty)"}
      </div>
      <div className="copy-bar">
        {!skipped && !regenerating ? <Counter name={current.name} content={current.content} /> : <span />}
        <div className="copy-bar-actions">
          <button className="btn btn-sm btn-ghost" onClick={regenerate} disabled={regenerating || skipped}>
            {regenerating ? "Rewriting…" : "Rewrite"}
          </button>
          <button className="btn btn-sm btn-accent" onClick={copy} disabled={skipped}>
            Copy
          </button>
        </div>
      </div>
    </div>
  );
}
