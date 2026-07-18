// Shared lead-sheet field editor — used by the JD parser panel, the manual
// add-lead form, and the chat proposal card, so the CSV columns live in one place.
import SuggestInput from "./SuggestInput.jsx";

export const PERSONAS = ["hr", "engineer", "manager", "cto", "ceo"];

// suggest: true renders a datalist of values already in the lead sheet.
export const LEAD_FIELDS = [
  { key: "full_name", label: "Full name *" },
  { key: "job_title", label: "Job title *", suggest: true },
  { key: "company_name", label: "Company *", suggest: true },
  { key: "city", label: "City", suggest: true },
  { key: "linkedin_url", label: "LinkedIn URL" },
  { key: "email", label: "Email" },
  { key: "company_size", label: "Company size" },
  { key: "industry", label: "Industry", suggest: true },
  { key: "company_website", label: "Website" },
];

// The domain classifier only understands these stages, so offer them as a
// fixed dropdown rather than free text (see leads.classify_domain).
export const FUNDING_STAGES = [
  "pre-seed", "seed", "series a", "series b", "series c", "series d", "public",
];

export const EMPTY_LEAD = Object.fromEntries(
  [...LEAD_FIELDS.map((f) => f.key), "funding_stage"].map((k) => [k, ""]),
);

export function canSubmitLead(fields, persona) {
  return Boolean(
    fields && persona && fields.full_name && fields.job_title && fields.company_name
  );
}

export default function LeadFieldsEditor({ fields, setFields, persona, setPersona }) {
  return (
    <div className="field-grid">
      {LEAD_FIELDS.map((f) => (
        <label key={f.key} className="field">
          <span className="field-label">{f.label}</span>
          {f.suggest ? (
            <SuggestInput
              field={f.key}
              value={fields[f.key] || ""}
              onChange={(e) => setFields({ ...fields, [f.key]: e.target.value })}
            />
          ) : (
            <input
              className="input"
              value={fields[f.key] || ""}
              onChange={(e) => setFields({ ...fields, [f.key]: e.target.value })}
            />
          )}
        </label>
      ))}
      <label className="field">
        <span className="field-label">Funding stage</span>
        <select
          className="select"
          value={fields.funding_stage || ""}
          onChange={(e) => setFields({ ...fields, funding_stage: e.target.value })}
        >
          <option value="">(unknown)</option>
          {FUNDING_STAGES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span className="field-label">Persona *</span>
        <select
          className="select"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
        >
          <option value="">(choose)</option>
          {PERSONAS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
