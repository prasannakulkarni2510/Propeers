import { useState } from "react";
import { useStore } from "../store";
import LeadFieldsEditor, { EMPTY_LEAD, canSubmitLead } from "./LeadFieldsEditor.jsx";

// Manual entry: fill the fields, submit, and the lead goes straight into
// leads.csv + the tracker via POST /api/leads.
export default function AddLeadForm() {
  const addLead = useStore((s) => s.addLead);
  const [open, setOpen] = useState(false);
  const [fields, setFields] = useState(EMPTY_LEAD);
  const [persona, setPersona] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await addLead({ ...fields, persona_tag: persona });
      setFields(EMPTY_LEAD);
      setPersona("");
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button className="btn" onClick={() => setOpen(true)}>
        + Add lead manually
      </button>
    );
  }

  return (
    <div className="panel">
      <h3>Add a lead</h3>
      <p className="muted">Saved to data/leads.csv and the tracker on submit.</p>
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
          onClick={submit}
        >
          {busy ? "Adding…" : "Add to leads.csv"}
        </button>
        <button className="btn btn-ghost" disabled={busy} onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
      {error && <p className="jd-error">{error}</p>}
    </div>
  );
}
