import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../services/api";

// One boolean-search variant: the query itself (copyable) plus the LinkedIn
// and Google X-Ray links that run it. Read-only — the operator opens the
// search, picks a person, and adds them as a lead like any other.
function VariantCard({ v }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(v.query);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="panel disc-card">
      <div className="disc-head">
        <span className="disc-group">{v.group}</span>
        {v.persona_tag && <span className="tag">{v.persona_tag}</span>}
      </div>
      <code className="disc-query">{v.query}</code>
      <div className="btn-row">
        <a className="btn btn-accent btn-sm" href={v.linkedin_url} target="_blank" rel="noopener noreferrer">
          LinkedIn search
        </a>
        <a className="btn btn-ghost btn-sm" href={v.xray_url} target="_blank" rel="noopener noreferrer">
          Google X-Ray
        </a>
        <button className="btn btn-ghost btn-sm" onClick={copy}>
          {copied ? "Copied ✓" : "Copy query"}
        </button>
      </div>
    </div>
  );
}

export default function Discovery() {
  const [params] = useSearchParams();
  const [company, setCompany] = useState(params.get("company") || "");
  const [role, setRole] = useState(params.get("role") || "");
  const [city, setCity] = useState(params.get("city") || "");
  const [keywords, setKeywords] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (c = company, r = role, ci = city, kw = keywords) => {
    if (!c.trim()) return;
    setBusy(true);
    setError("");
    try {
      setResult(
        await api.discovery({
          company_name: c,
          job_title: r,
          city: ci,
          keywords: kw.split(",").map((s) => s.trim()).filter(Boolean),
        })
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  // Arriving from a lead row / chat proposal pre-fills the form — run at once.
  useEffect(() => {
    if (params.get("company")) run(params.get("company"), params.get("role") || "", params.get("city") || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h1 className="page-title">Recruiter Discovery</h1>
      <p className="page-sub">
        Boolean searches for the people behind a job — hiring managers, leads,
        directors, recruiters, TA, HRBPs. Open a search, pick a person, add
        them as a lead.
      </p>
      <div className="panel disc-form">
        <input className="input" placeholder="Company (required)" value={company}
               onChange={(e) => setCompany(e.target.value)} />
        <input className="input" placeholder="Role / job title (optional)" value={role}
               onChange={(e) => setRole(e.target.value)} />
        <input className="input" placeholder="Location (optional)" value={city}
               onChange={(e) => setCity(e.target.value)} />
        <input className="input" placeholder="Tech stack, comma-separated (optional)" value={keywords}
               onChange={(e) => setKeywords(e.target.value)} />
        <button className="btn btn-accent" disabled={busy || !company.trim()} onClick={() => run()}>
          {busy ? "Building…" : "Build searches"}
        </button>
      </div>
      {error && <p className="jd-error">{error}</p>}
      {result && (
        <>
          <p className="muted">
            {result.variants.length} search variants for {result.company_name}
            {result.city && ` · ${result.city}`} — LinkedIn keyword search
            understands AND/OR/quotes; X-Ray finds public profiles via Google.
          </p>
          <div className="disc-grid">
            {result.variants.map((v, i) => (
              <VariantCard key={i} v={v} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
