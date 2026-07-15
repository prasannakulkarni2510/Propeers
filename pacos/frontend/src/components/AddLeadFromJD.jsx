import { useState } from "react";
import { api } from "../services/api";
import { useStore } from "../store";
import LeadFieldsEditor, { EMPTY_LEAD, canSubmitLead } from "./LeadFieldsEditor.jsx";

// Paste a JD → backend extracts a proposal (writes nothing) → operator reviews,
// edits, and explicitly confirms before anything lands in leads.csv.
export default function AddLeadFromJD() {
  const addLead = useStore((s) => s.addLead);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [fields, setFields] = useState(null); // null until parsed
  const [persona, setPersona] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const parse = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.parseJd(text);
      const { persona_tag, ...rest } = res.fields;
      setFields({ ...EMPTY_LEAD, ...rest });
      setPersona(persona_tag || "");
      setWarnings(res.warnings);
      setSource(res.llm_used ? res.model : "offline fallback");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      await addLead({ ...fields, persona_tag: persona });
      setText("");
      setFields(null);
      setWarnings([]);
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button className="btn btn-accent" onClick={() => setOpen(true)}>
        + Add lead from JD
      </button>
    );
  }

  return (
    <div className="panel">
      <h3>Add lead from a job description</h3>
      {fields === null ? (
        <>
          <textarea
            className="textarea"
            rows={8}
            placeholder="Paste the full JD text here (include any recruiter name, email, or LinkedIn URL it mentions)…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="btn-row">
            <button className="btn" disabled={busy || text.trim().length < 30} onClick={parse}>
              {busy ? "Parsing…" : "Parse JD"}
            </button>
            <button className="btn btn-ghost" onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="muted">
            Extracted via {source}. Review and edit — nothing is saved until you confirm.
          </p>
          {warnings.length > 0 && (
            <ul className="jd-warnings">
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          <LeadFieldsEditor
            fields={fields}
            setFields={setFields}
            persona={persona}
            setPersona={setPersona}
          />
          <div className="btn-row">
            <button
              className="btn btn-accent"
              disabled={busy || !canSubmitLead(fields, persona)}
              onClick={confirm}
            >
              {busy ? "Adding…" : "Add to leads.csv"}
            </button>
            <button className="btn btn-ghost" disabled={busy} onClick={() => setFields(null)}>
              Back to JD text
            </button>
            <button className="btn btn-ghost" disabled={busy} onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </>
      )}
      {error && <p className="jd-error">{error}</p>}
    </div>
  );
}
