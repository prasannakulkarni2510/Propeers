import { useMemo, useState } from "react";
import LeadTable from "./LeadTable.jsx";

const PAGE_SIZE = 25;

// Search + filter + paginate the lead list so the table stays usable at any
// size (the dataset can run to hundreds of rows). All client-side: the full
// list is already in the store, we just slice what we render.
export default function LeadBrowser({ leads }) {
  const [q, setQ] = useState("");
  const [domain, setDomain] = useState("");
  const [assets, setAssets] = useState(""); // "", "yes", "no"
  const [page, setPage] = useState(1);

  const domains = useMemo(
    () => [...new Set(leads.map((l) => l.domain_tag).filter(Boolean))].sort(),
    [leads],
  );

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return leads.filter((l) => {
      if (domain && l.domain_tag !== domain) return false;
      if (assets === "yes" && l.assets_generated !== "true") return false;
      if (assets === "no" && l.assets_generated === "true") return false;
      if (!needle) return true;
      return [l.full_name, l.company_name, l.job_title, l.city].some((v) =>
        (v || "").toLowerCase().includes(needle),
      );
    });
  }, [leads, q, domain, assets]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const start = (current - 1) * PAGE_SIZE;
  const pageLeads = filtered.slice(start, start + PAGE_SIZE);

  // Any filter change starts over at page 1 so results aren't hidden off-page.
  const onFilter = (setter) => (e) => {
    setter(e.target.value);
    setPage(1);
  };

  return (
    <div>
      <div className="toolbar">
        <input
          className="input"
          style={{ maxWidth: 300 }}
          placeholder="Search name, company, role, or city…"
          value={q}
          onChange={onFilter(setQ)}
        />
        <select className="select" value={domain} onChange={onFilter(setDomain)}>
          <option value="">All domains</option>
          {domains.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select className="select" value={assets} onChange={onFilter(setAssets)}>
          <option value="">All leads</option>
          <option value="no">Needs assets</option>
          <option value="yes">Has assets</option>
        </select>
        <span className="muted">
          {filtered.length} match{filtered.length === 1 ? "" : "es"}
          {filtered.length !== leads.length ? ` of ${leads.length}` : ""}
        </span>
      </div>

      {filtered.length === 0 ? (
        <p className="muted">No leads match your search.</p>
      ) : (
        <>
          <LeadTable leads={pageLeads} />
          {pageCount > 1 && (
            <div className="pagination">
              <span className="muted">
                Showing {start + 1}–{start + pageLeads.length} of {filtered.length}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={current <= 1}
                onClick={() => setPage(current - 1)}
              >
                Prev
              </button>
              <span className="muted">Page {current} / {pageCount}</span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={current >= pageCount}
                onClick={() => setPage(current + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
