import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useLeads } from "../hooks/useLeads";
import { useStore } from "../store";
import { api } from "../services/api";
import { LEAD_STAGES, isFollowUpDue, isPerson, isReadyToSend, leadStage } from "../lib/pipeline";
import { leadSearch } from "../components/LeadModal.jsx";
import AddLead from "../components/AddLead.jsx";
import CvEditor from "../components/CvEditor.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

const PAGE = 20;
const BATCH = 10;

// The one line under a lead's name: what is true of it right now.
function stateLine(lead, stage) {
  if (stage === "needs_assets") return isPerson(lead) ? "" : "Job posting, no person yet";
  if (stage === "ready") return lead.has_email ? "Email and DM ready" : "DM ready";
  if (stage === "awaiting") {
    if (isFollowUpDue(lead)) return "Follow-up due";
    return lead.follow_up_due ? `Follow up ${lead.follow_up_due}` : `Sent ${lead.outreach_sent_date || ""}`;
  }
  return "";
}

function Column({ stage, items, openId, action }) {
  const [shown, setShown] = useState(PAGE);
  const navigate = useNavigate();
  const due = stage.id === "awaiting" && items.some(isFollowUpDue);
  return (
    <section className={`kb-col ${due ? "kb-col-warn" : ""}`} aria-label={`${stage.title}, ${items.length}`}>
      <header className="kb-col-head">
        <h2 className="kb-col-title">{stage.title}</h2>
        <span className="kb-count">{items.length}</span>
      </header>
      <div className="kb-cards">
        {action}
        {items.length === 0 && <div className="kb-empty">{stage.empty}</div>}
        {items.slice(0, shown).map((l) => {
          const line = stateLine(l, stage.id);
          return (
            <button
              key={l.lead_id}
              type="button"
              className={`kb-card ${openId === l.lead_id ? "is-open" : ""}`}
              onClick={() => navigate({ search: leadSearch(l.lead_id) })}
            >
              <div className="kb-card-title">
                {l.full_name || l.company_name}
                {stage.id === "engaged" && <StatusBadge status={l.status} />}
              </div>
              <div className="kb-card-sub">
                {[l.job_title, l.full_name && l.company_name].filter(Boolean).join(", ")}
              </div>
              {line && (
                <div className={`kb-card-state ${isFollowUpDue(l) ? "is-due" : ""}`}>{line}</div>
              )}
            </button>
          );
        })}
        {items.length > shown && (
          <button className="btn btn-ghost btn-sm kb-more" onClick={() => setShown(shown + PAGE)}>
            Show {Math.min(PAGE, items.length - shown)} more
          </button>
        )}
      </div>
    </section>
  );
}

const DAY = 86_400_000;
const TODAY_MAX = 6;

function dueLabel(lead) {
  const late = Math.round((Date.parse(new Date().toISOString().slice(0, 10)) - Date.parse(lead.follow_up_due)) / DAY);
  if (late <= 0) return "follow up today";
  return `follow-up ${late} day${late === 1 ? "" : "s"} late`;
}

// What to do today, above the board: late follow-ups first, then messages
// ready to send. Each opens that person.
function TodayStrip({ leads }) {
  const navigate = useNavigate();
  const due = leads.filter(isFollowUpDue).sort((a, b) => a.follow_up_due.localeCompare(b.follow_up_due));
  const ready = leads.filter(isReadyToSend);
  if (due.length + ready.length === 0) return null;
  const items = [
    ...due.map((l) => ({ l, label: dueLabel(l), due: true })),
    ...ready.map((l) => ({ l, label: "ready to send", due: false })),
  ];
  const more = items.length - TODAY_MAX;
  return (
    <section className="today" aria-label="Today">
      <h2 className="today-title">Today</h2>
      <div className="today-items">
        {items.slice(0, TODAY_MAX).map(({ l, label, due: late }) => (
          <button
            key={l.lead_id}
            type="button"
            className={`today-chip ${late ? "is-due" : ""}`}
            onClick={() => navigate({ search: leadSearch(l.lead_id) })}
          >
            <span className="today-name">{l.full_name || l.company_name}</span>
            <span className="today-what">{label}</span>
          </button>
        ))}
        {more > 0 && <span className="today-more">and {more} more on the board</span>}
      </div>
    </section>
  );
}

// Every lead, in the one stage it is in. Click a lead to open it beside the
// board: its drafts, and the one thing to do next.
export default function Pipeline() {
  const { leads, loading, error, refresh } = useLeads();
  const generate = useStore((s) => s.generate);
  const generating = useStore((s) => s.generating);
  const setToast = useStore((s) => s.setToast);
  const [params] = useSearchParams();
  const openId = params.get("lead") || "";
  const [q, setQ] = useState("");
  const [adding, setAdding] = useState(false);
  const [cvOpen, setCvOpen] = useState(false);
  const [scanning, setScanning] = useState(false);

  const columns = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const match = (l) =>
      !needle ||
      [l.full_name, l.company_name, l.job_title, l.city].some((v) => (v || "").toLowerCase().includes(needle));
    const by = Object.fromEntries(LEAD_STAGES.map((s) => [s.id, []]));
    for (const l of leads) if (match(l)) by[leadStage(l)].push(l);
    // Overdue follow-ups first, then the soonest.
    by.awaiting.sort(
      (a, b) => isFollowUpDue(b) - isFollowUpDue(a) || (a.follow_up_due || "9").localeCompare(b.follow_up_due || "9"),
    );
    return by;
  }, [leads, q]);

  const toWrite = leads.filter((l) => isPerson(l) && l.assets_generated !== "true").length;
  // Drafts are written a batch at a time, so one click never spends a run on hundreds of leads.
  const batch = Math.min(toWrite, BATCH);

  const scan = async () => {
    setScanning(true);
    try {
      const r = await api.scanInbox();
      setToast(`Inbox checked: ${r.matched} repl${r.matched === 1 ? "y" : "ies"} found from people you wrote to.`);
      await refresh();
    } catch (e) {
      setToast(`Couldn't check the inbox: ${e.message}`);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="wide">
      <div className="page-head">
        <h1 className="page-title">My people</h1>
        <div className="pipe-tools">
          <input
            className="input"
            type="search"
            aria-label="Search people"
            placeholder="Search by name or company"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <button className="btn btn-ghost" disabled={scanning} onClick={scan}>
            {scanning ? "Checking…" : "Check inbox"}
          </button>
          <button className="btn btn-accent" aria-expanded={adding} onClick={() => setAdding(!adding)}>
            Add a person
          </button>
        </div>
      </div>

      {error && <div className="banner">Couldn’t reach the server: {error}</div>}
      <CvEditor open={cvOpen} setOpen={setCvOpen} />
      {adding && <AddLead onClose={() => setAdding(false)} />}

      {loading && leads.length === 0 ? (
        <p className="muted">Loading leads…</p>
      ) : leads.length === 0 ? (
        <div className="empty-state">
          <h2 className="page-title">No one here yet</h2>
          <p className="page-sub">
            Everyone you want to write to about a job lives here. Add someone, or paste a job description into the chat.
          </p>
          <button className="btn btn-accent" onClick={() => setAdding(true)}>Add your first person</button>
        </div>
      ) : (
        <>
        {!q.trim() && <TodayStrip leads={leads} />}
        <div className="kb-board pipe-board">
          {LEAD_STAGES.map((st) => (
            <Column
              key={st.id}
              stage={st}
              items={columns[st.id]}
              openId={openId}
              action={
                st.id === "needs_assets" && toWrite > 0 ? (
                  <button
                    className="btn btn-accent btn-sm kb-more"
                    disabled={generating}
                    title={`Write messages for ${batch === toWrite ? "these" : `the next ${batch} of these`} people`}
                    onClick={() => generate({ limit: batch }).catch(() => {})}
                  >
                    {generating ? "Writing messages…" : batch === toWrite ? `Write messages for all ${batch}` : `Write messages for the next ${batch}`}
                  </button>
                ) : null
              }
            />
          ))}
        </div>
        </>
      )}
    </div>
  );
}
