// Shared lead-sheet field editor — used by the JD parser panel, the manual
// add-lead form, and the chat proposal card, so the CSV columns live in one place.

export const PERSONAS = ["hr", "engineer", "manager", "cto", "ceo"];

export const LEAD_FIELDS = [
  { key: "full_name", label: "Full name *" },
  { key: "job_title", label: "Job title *" },
  { key: "company_name", label: "Company *" },
  { key: "city", label: "City" },
  { key: "linkedin_url", label: "LinkedIn URL" },
  { key: "email", label: "Email" },
  { key: "company_size", label: "Company size" },
  { key: "industry", label: "Industry" },
  { key: "company_website", label: "Website" },
  { key: "funding_stage", label: "Funding stage" },
];

export const EMPTY_LEAD = Object.fromEntries(LEAD_FIELDS.map((f) => [f.key, ""]));

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
          <input
            className="input"
            value={fields[f.key] || ""}
            onChange={(e) => setFields({ ...fields, [f.key]: e.target.value })}
          />
        </label>
      ))}
      <label className="field">
        <span className="field-label">Persona *</span>
        <select
          className="select"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
        >
          <option value="">— choose —</option>
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
