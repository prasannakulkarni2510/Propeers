import { useState } from "react";
import { api } from "../services/api";
import { useStore } from "../store";
import LeadFieldsEditor, { EMPTY_LEAD, canSubmitLead } from "./LeadFieldsEditor.jsx";

// One way in for a new lead. Paste a job description and PACOS fills the
// fields (it writes nothing), or type them yourself. Either way the lead is
// only saved when you press Add.
export default function AddLead({ onClose }) {
  const addLead = useStore((s) => s.addLead);
  const [mode, setMode] = useState("jd"); // "jd" | "manual"
  const [text, setText] = useState("");
  const [fields, setFields] = useState(EMPTY_LEAD);
  const [persona, setPersona] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (fn) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const parse = () =>
    run(async () => {
      const res = await api.parseJd(text);
      const { persona_tag, ...rest } = res.fields;
      setFields({ ...EMPTY_LEAD, ...rest });
      setPersona(persona_tag || "");
      setWarnings(res.warnings || []);
      setMode("manual");
    });

  const add = () =>
    run(async () => {
      await addLead({ ...fields, persona_tag: persona });
      onClose();
    });

  return (
    <div className="panel add-lead">
      <div className="add-lead-head">
        <h3>Add a person</h3>
        <div className="seg" role="group" aria-label="How to add">
          <button aria-pressed={mode === "jd"} onClick={() => setMode("jd")}>Paste a job description</button>
          <button aria-pressed={mode === "manual"} onClick={() => setMode("manual")}>Type it in</button>
        </div>
      </div>
      {mode === "jd" ? (
        <>
          <textarea
            className="textarea"
            rows={7}
            aria-label="Job description"
            placeholder="Paste the whole job description, with any recruiter name, email or LinkedIn link it mentions"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="btn-row">
            <button className="btn btn-accent" disabled={busy || text.trim().length < 30} onClick={parse}>
              {busy ? "Reading…" : "Fill in the details"}
            </button>
            <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          </div>
        </>
      ) : (
        <>
          {warnings.length > 0 && (
            <ul className="jd-warnings">
              {warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
          <LeadFieldsEditor fields={fields} setFields={setFields} persona={persona} setPersona={setPersona} />
          <div className="btn-row">
            <button className="btn btn-accent" disabled={busy || !canSubmitLead(fields, persona)} onClick={add}>
              {busy ? "Adding…" : "Add person"}
            </button>
            <button className="btn btn-ghost" disabled={busy} onClick={onClose}>Cancel</button>
            <span className="muted">Name, job title, company and persona are required.</span>
          </div>
        </>
      )}
      {error && <p className="jd-error" role="alert">{error}</p>}
    </div>
  );
}
