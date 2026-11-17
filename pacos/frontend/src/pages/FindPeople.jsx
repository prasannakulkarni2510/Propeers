import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../services/api";
import { useStore } from "../store";
import SuggestInput from "../components/SuggestInput.jsx";

// Deterministic auto-import: run the same Google X-Ray search, collect the
// LinkedIn profiles it surfaces, predict work emails, and create leads. No new
// agent and no paid people-search API — the source stays the operator's own
// Google X-Ray query. Falls back to an operator paste when Google answers the
// automated fetch with a consent/CAPTCHA wall.
const STEPS = [
  "Searching…",
  "Collecting profiles…",
  "Extracting names…",
  "Predicting email formats…",
  "Saving leads…",
];

function ImportPeople({ company, role, city, keywords }) {
  const refresh = useStore((s) => s.refresh);
  const setToast = useStore((s) => s.setToast);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [pasted, setPasted] = useState("");
  const [showPaste, setShowPaste] = useState(false);
  const timer = useRef(null);

  const kw = () => keywords.split(",").map((s) => s.trim()).filter(Boolean);

  const run = async (pasted_html = "") => {
    setBusy(true);
    setError("");
    setResult(null);
    setStep(0);
    // Advance the progress labels while the request is in flight.
    timer.current = setInterval(
      () => setStep((s) => Math.min(s + 1, STEPS.length - 1)),
      650,
    );
    try {
      const res = await api.enrich({
        company_name: company,
        job_title: role,
        city,
        keywords: kw(),
        pasted_html,
      });
      setResult(res);
      if (res.leads_imported > 0) {
        setToast(`${res.leads_imported} lead(s) imported from discovery`);
        await refresh();
      }
      // Google blocked the automated fetch and nothing was pasted — offer paste.
      if (res.leads_imported === 0 && res.source !== "pasted") setShowPaste(true);
    } catch (e) {
      setError(e.message);
    } finally {
      clearInterval(timer.current);
      setBusy(false);
      setStep(-1);
    }
  };

  useEffect(() => () => clearInterval(timer.current), []);

  return (
    <div className="panel disc-enrich">
      <div className="disc-head">
        <span className="disc-group">Add them to My people</span>
      </div>
      <p className="muted">
        Collects the LinkedIn profiles a Google search finds and adds each to
        My people with a likely work email. Likely means guessed from the company’s
        pattern, not verified.
      </p>
      <div className="btn-row">
        <button className="btn btn-accent" disabled={busy || !company.trim()} onClick={() => run()}>
          {busy ? "Working…" : "Find and import"}
        </button>
        {!showPaste && (
          <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => setShowPaste(true)}>
            Paste results instead
          </button>
        )}
      </div>

      {busy && step >= 0 && (
        <ol className="disc-steps">
          {STEPS.map((label, i) => (
            <li key={i} className={i < step ? "done" : i === step ? "active" : ""}>
              {label}
            </li>
          ))}
        </ol>
      )}

      {showPaste && (
        <div className="disc-paste">
          <p className="muted">
            Google sometimes blocks the automatic search. Open
            a <strong>Google search</strong> link below, copy the whole results
            page (Ctrl+A, Ctrl+C) and paste it here.
          </p>
          <textarea
            className="input"
            rows={4}
            aria-label="Pasted search results"
            placeholder="Paste the Google results page here"
            value={pasted}
            onChange={(e) => setPasted(e.target.value)}
          />
          <div className="btn-row">
            <button className="btn btn-accent btn-sm" disabled={busy || !pasted.trim()} onClick={() => run(pasted)}>
              Import from this
            </button>
          </div>
        </div>
      )}

      {error && <p className="jd-error">{error}</p>}
      {result && (
        <p className={result.leads_imported > 0 ? "disc-imported" : "muted"}>
          {result.leads_imported > 0
            ? `${result.leads_imported} lead(s) imported${result.profiles_found > result.leads_imported ? ` from ${result.profiles_found} profiles` : ""}. They are in your pipeline.`
            : (result.warnings[0] || "No profiles found in the search results.")}
        </p>
      )}
    </div>
  );
}

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
          LinkedIn
        </a>
        <a className="btn btn-ghost btn-sm" href={v.xray_url} target="_blank" rel="noopener noreferrer">
          Google
        </a>
        <button className="btn btn-ghost btn-sm" onClick={copy}>
          {copied ? "Copied" : "Copy query"}
        </button>
      </div>
    </div>
  );
}

export default function FindPeople() {
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
      <h1 className="page-title">Find people</h1>
      <p className="page-sub">
        Name a company and PACOS builds the searches that surface its hiring
        managers and recruiters.
      </p>
      <div className="disc-form" style={{ marginBottom: 24 }}>
        <SuggestInput field="company_name" placeholder="Company" value={company}
                      onChange={(e) => setCompany(e.target.value)} />
        <SuggestInput field="job_title" placeholder="Role (optional)" value={role}
                      onChange={(e) => setRole(e.target.value)} />
        <SuggestInput field="city" placeholder="Location (optional)" value={city}
                      onChange={(e) => setCity(e.target.value)} />
        <input className="input" aria-label="Tech stack" placeholder="Tech stack, comma-separated" value={keywords}
               onChange={(e) => setKeywords(e.target.value)} />
        <button className="btn btn-accent" disabled={busy || !company.trim()} onClick={() => run()}>
          {busy ? "Building…" : "Build searches"}
        </button>
      </div>
      {error && <p className="jd-error">{error}</p>}
      {result && (
        <>
          <p className="muted" style={{ marginBottom: 16 }}>
            {result.variants.length} searches for {result.company_name}
            {result.city && `, ${result.city}`}. Open one, pick a person, add them as a lead.
          </p>
          <ImportPeople company={company} role={role} city={city} keywords={keywords} />
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
