import { useState } from "react";

// "Know more about the project" — the PACOS story as a single scrollable page
// (the interview deck, rendered as HTML). Static content; no API calls.
// The author photo is served from /prasanna-photo.png, which is gitignored — so
// it shows locally but is absent (and gracefully hidden) on the public deploy.

const TECH = ["React", "FastAPI", "LangGraph", "SQLite", "Nemotron"];

const LAYERS = [
  {
    n: "01",
    title: "Asset Generator",
    body: "One lead in, four outreach drafts out: a cold email, a short LinkedIn DM, a cover letter, and notes on how to tweak a CV for that role.",
  },
  {
    n: "02",
    title: "Inbox Monitor",
    body: "Reads Gmail for LinkedIn and Naukri job alerts and recruiter replies and folds them into the tracker. Read-only, always: only the gmail.readonly scope.",
  },
  {
    n: "03",
    title: "Tracker",
    body: "One source of truth for where every lead stands: follow-up logic, a status flow, and a daily digest that says who to chase today.",
  },
];

const GUARDRAILS = [
  ["Never auto-sends", "Every draft is copy-pasted by the operator after they read it. There is no send path in the code at all."],
  ["Inbox is strictly read-only", "The monitor requests only gmail.readonly. It never sends, labels, deletes, or modifies mail."],
  ["The model proposes, it never writes", "The JD parser and chat turn pasted text into a lead proposal. Nothing lands in the tracker until the operator confirms it."],
  ["Discovery is deterministic", "Boolean people-searches with LinkedIn and Google X-Ray links, built from what PACOS already knows — no scraping, no model call."],
];

const STATUS_FLOW = ["pending", "sent", "replied", "interested", "interview", "offer"];

// Social + contact (from the interview deck).
const SOCIAL = [
  { label: "Email", href: "mailto:kulkarniprasanna25@gmail.com", text: "kulkarniprasanna25@gmail.com" },
  { label: "GitHub", href: "https://github.com/prasannakulkarni2510", text: "github.com/prasannakulkarni2510" },
  { label: "LinkedIn", href: "https://www.linkedin.com/in/prasanna-kulkarni", text: "linkedin.com/in/prasanna-kulkarni" },
];

function Section({ kicker, title, children }) {
  return (
    <section className="about-section">
      {kicker && <p className="about-kicker">{kicker}</p>}
      {title && <h2 className="about-h2">{title}</h2>}
      {children}
    </section>
  );
}

export default function About() {
  const [photoOk, setPhotoOk] = useState(true);
  const [projImgOk, setProjImgOk] = useState(true);

  return (
    <div className="about">
      {/* ── hero ─────────────────────────────────────────── */}
      <header className="about-hero panel">
        <img className="about-logo" src="/pacos-logo.png" alt="PACOS logo" />
        <h1 className="about-title">Personal AI Career Operating System</h1>
        <p className="about-lede">
          A local-first pipeline that drafts job-search outreach and tracks it.
          The model writes; a human approves every send.
        </p>
        <div className="about-chips">
          {TECH.map((t) => (
            <span key={t} className="tag">{t}</span>
          ))}
        </div>
      </header>

      {/* ── the problem ──────────────────────────────────── */}
      <Section kicker="The problem" title="Why I built it">
        <p>
          A serious job search is a lot of small, repeated work. For each person
          worth reaching, you research them, write a tailored email, cut it to a
          LinkedIn DM, draft a cover letter, note how to adjust your CV, then
          remember to follow up a week later. Doing that by hand, it's easy to
          lose the thread of who you contacted and where things stand.
        </p>
        <p className="about-quote">
          The line I would not cross: automate the drafting and the bookkeeping,
          but never let a model email strangers on my behalf. The model drafts;
          I decide what actually gets sent.
        </p>
      </Section>

      {/* ── what it does ─────────────────────────────────── */}
      <Section kicker="What it does" title="Three light layers, plain files underneath">
        <div className="about-grid-3">
          {LAYERS.map((l) => (
            <div key={l.n} className="panel about-card">
              <span className="about-num">{l.n}</span>
              <h3>{l.title}</h3>
              <p>{l.body}</p>
            </div>
          ))}
        </div>
        <p className="muted">
          No orchestration for storage, no separate CRM. State lives in SQLite;
          the CSVs you can open in Excel are exports of it.
        </p>
      </Section>

      {/* ── discovery + enrichment (shipped) ─────────────── */}
      <Section kicker="Finding people" title="Discovery — deterministic, now with one-click enrichment">
        <p>
          Discovery builds targeted Boolean searches for the humans behind a
          job (hiring managers, engineering leads, recruiters) as LinkedIn and
          Google X-Ray links. It's deterministic: a template, not a model call.
        </p>
        <p>
          A newer <em>Find People</em> step collects the LinkedIn profiles from
          those X-Ray results, predicts a likely work email, and creates leads,
          so there is no manual copy-paste. Predicted emails are tagged by
          confidence and never marked verified.
        </p>
      </Section>

      {/* ── generation pipeline ──────────────────────────── */}
      <Section kicker="The generation pipeline" title="Per lead it's a small graph, not one call">
        <p>
          A supervisor runs one <strong>Personalization agent</strong> that
          produces a single shared hook, the sharpest sentence tying the
          candidate to this person or company, then fans out to four asset
          agents in parallel off that hook (about five model calls per lead).
        </p>
        <div className="about-pipeline">
          <span className="about-pill about-pill-dark">Personalization</span>
          <span className="about-arrow">→</span>
          <span className="about-pill">cold_email</span>
          <span className="about-pill">cold_dm</span>
          <span className="about-pill">cover_letter</span>
          <span className="about-pill">cv_notes</span>
        </div>
        <ul className="about-list">
          <li><strong>Shared hook</strong> keeps all four drafts coherent instead of four separate takes.</li>
          <li><strong>Conditional edge</strong> skips the email agent when a lead has no address.</li>
          <li><strong>Streaming status</strong> drives a real per-agent board in the UI.</li>
          <li><strong>Checkpoint / resume</strong> — a big batch that fails partway resumes without re-spending tokens.</li>
        </ul>
      </Section>

      {/* ── engineering judgment ─────────────────────────── */}
      <Section kicker="Engineering judgment" title="A decision I reversed, on purpose">
        <div className="about-grid-2">
          <div className="panel about-card">
            <h3>The first design doc said</h3>
            <p>One model call per lead. Four files out. No orchestration framework at all. Simpler, cheaper, fewer dependencies.</p>
          </div>
          <div className="panel about-card about-card-accent">
            <h3>What I shipped instead</h3>
            <p>A LangGraph graph — ~5× the calls per lead and one real dependency — for coherent drafts from the shared hook, a real per-agent status board, checkpoint/resume, and first-class human-in-the-loop interrupts. The reversal is written down as an ADR.</p>
          </div>
        </div>
      </Section>

      {/* ── constraints ──────────────────────────────────── */}
      <Section kicker="Constraints by design" title="The guardrails came first, not last">
        <div className="about-grid-2">
          {GUARDRAILS.map(([t, b]) => (
            <div key={t} className="panel about-card">
              <h3>{t}</h3>
              <p>{b}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ── workflow ─────────────────────────────────────── */}
      <Section kicker="Workflow" title="One tracker, a status flow, a daily digest">
        <div className="about-flow">
          {STATUS_FLOW.map((s, i) => (
            <span key={s} className="about-flow-step">
              {s}{i < STATUS_FLOW.length - 1 && <span className="about-arrow">→</span>}
            </span>
          ))}
          <span className="about-flow-branch">↳ any stage can branch to <em>rejected</em></span>
        </div>
        <p className="muted">
          SQLite holds the real state — every lead, every status change.
          tracker.csv is an export, never authoritative. A daily digest lists
          who replied and who is due for a follow-up.
        </p>
      </Section>

      {/* ── how it runs ──────────────────────────────────── */}
      <Section kicker="How it runs" title="Same core, two ways to run it">
        <div className="about-grid-2">
          <div className="panel about-card">
            <h3>Local-first</h3>
            <p>Runs from one folder as a single frozen exe (PyInstaller). No install, no server to stand up; SQLite locally. Everything works with no network except the model call.</p>
          </div>
          <div className="panel about-card">
            <h3>Cloud</h3>
            <p>A private, token-gated web app — one Docker service on Render, Postgres on Neon. Deployment is a config choice, not a rewrite: the same tested core underneath.</p>
          </div>
        </div>
      </Section>

      {/* ── author card ──────────────────────────────────── */}
      <Section kicker="About the author" title="Built by Prasanna Kulkarni">
        <div className="panel about-author">
          <div className="about-author-photo">
            {photoOk ? (
              <img src="/prasanna-photo.png" alt="Prasanna Kulkarni" onError={() => setPhotoOk(false)} />
            ) : (
              <div className="about-avatar-fallback">PK</div>
            )}
          </div>
          <div className="about-author-body">
            <h3>Prasanna Kulkarni</h3>
            <p className="muted">AI Engineer · builder of PACOS</p>
            <ul className="about-social">
              {SOCIAL.map((s) => (
                <li key={s.label}>
                  <span className="about-social-label">{s.label}</span>
                  <a className="link" href={s.href} target="_blank" rel="noopener noreferrer">{s.text}</a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Slot for a project image you provide — drop it at
            frontend/public/project-image.png (or .jpg). Hidden until present. */}
        {projImgOk && (
          <div className="about-project-image">
            <img
              src="/project-image.png"
              alt="PACOS"
              onError={() => setProjImgOk(false)}
            />
          </div>
        )}
      </Section>

      <p className="about-foot muted">
        PACOS · Personal AI Career Operating System · human-in-the-loop, always.
      </p>
    </div>
  );
}
