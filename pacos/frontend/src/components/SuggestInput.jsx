import { useId, useMemo } from "react";
import { useStore } from "../store";

// Text input + native <datalist>: values already in the lead sheet (companies,
// roles, cities...) appear as a dropdown while free text keeps working. Zero
// dependencies, and the suggestion list always mirrors the current store.
export default function SuggestInput({
  field,
  value,
  onChange,
  placeholder = "",
  className = "input",
}) {
  const leads = useStore((s) => s.leads);
  const listId = useId();
  const options = useMemo(
    () =>
      [...new Set(leads.map((l) => (l[field] || "").trim()).filter(Boolean))].sort(
        (a, b) => a.localeCompare(b),
      ),
    [leads, field],
  );
  return (
    <>
      <input
        className={className}
        list={listId}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
      />
      <datalist id={listId}>
        {options.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
    </>
  );
}
