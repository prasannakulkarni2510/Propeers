import { useState } from "react";
import Icon from "../components/Icon.jsx";
import ContactForm from "../components/ContactForm.jsx";
import AuthorCard from "../components/AuthorCard.jsx";

// "Know more about the project" — the PACOS story as a single scrollable page
// (the interview deck, rendered as HTML). Static content; no API calls.
// The author card (photo, open-to-work badge, links) is components/AuthorCard.jsx.

const TECH = ["React", "FastAPI", "LangGraph", "SQLite", "Nemotron"];

const PAGES = [
  {
    title: "Chat",
    body: "The home page. Ask who to follow up with, say what happened (“Priya replied, she wants an interview”), ask for a draft, or paste a job description or a screenshot. Every change comes back as a card you apply or dismiss.",
  },
  {
    title: "My people",
    body: "Every lead on one board: to write, ready to send, waiting for a reply, replied, finished. Open a person to read and copy their cold email, LinkedIn DM, cover letter and CV notes.",
  },
  {
    title: "Find people",
    body: "Name a company and PACOS builds the LinkedIn and Google searches that surface its hiring managers and recruiters, then adds the people you pick with a likely work email.",
  },
  {
    title: "My CV",
    body: "Keep a CV for each kind of role. Every draft is written from the one in use, so messages only claim experience you actually have.",
  },
];

const GUARDRAILS = [
  ["Never auto-sends", "Every draft is copy-pasted by the operator after they read it. There is no send path in the code at all."],
  ["Inbox is strictly read-only", "The monitor requests only gmail.readonly. It never sends, labels, deletes, or modifies mail."],
  ["The model proposes, it never writes", "The JD parser and chat turn pasted text into a lead proposal. Nothing lands in the tracker until the operator confirms it."],
  ["Discovery is deterministic", "Boolean people-searches with LinkedIn and Google X-Ray links, built from what PACOS already knows. No scraping, no model call."],
];

const STAGES = ["To write", "Ready to send", "Waiting for a reply", "Replied", "Finished"];

function Section({ kicker, title, children }) {
  return (
    <section className="about-section">
      {kicker && <h2 className="about-h2">{kicker}</h2>}
      {title && <p className="about-sub">{title}</p>}
      {children}
    </section>
  );
}

export default function About() {
  const [projImgOk, setProjImgOk] = useState(true);

  // The author card sits in a column on the right (above the story on narrow
  // screens), so who built it is visible the whole way down.
  return (
    <div className="about-layout">
      <div className="about">
        {/* ── hero ─────────────────────────────────────────── */}
        <header className="about-hero">
          <div className="about-wordmark" aria-label="PACOS">PAC<span className="brand-accent">OS</span></div>
          <h1 className="about-title">Personal AI Career Operating System</h1>
          <p className="about-lede">
            A job-search assistant that drafts outreach from your CV and keeps
            track of every person you write to. It drafts; you send.
          </p>
          <div className="about-chips">
            {TECH.map((t) => (
              <span key={t} className="tag">{t}</span>
            ))}
          </div>
          <video className="about-video" src="/pacos-intro.mp4" poster="/pacos-intro-poster.jpg" controls preload="none" playsInline aria-label="PACOS intro video, with narration" />
        </header>

        {/* ── the problem ──────────────────────────────────── */}
        <Section kicker="The problem" title="Why I built it">
          <p>
            A serious job search is a lot of small, repeated work. For each person
            worth reaching, you research them, write a tailored email, cut it to a
            LinkedIn DM, draft a cover letter, note how to adjust your CV, then
            remember to follow up a week later. Doing that by hand, it’s easy to
            lose the thread of who you contacted and where things stand.
          </p>
          <p className="about-quote">
            The line I would not cross: automate the drafting and the bookkeeping,
            but never let a model email strangers on my behalf. The model drafts;
            I decide what actually gets sent.
          </p>
        </Section>

        {/* ── what it does ─────────────────────────────────── */}
        <Section kicker="What it does" title="Four pages, one obvious next step per person">
          <div className="about-grid-2">
            {PAGES.map((l) => (
              <div key={l.title} className="panel about-card">
                <h3>{l.title}</h3>
                <p>{l.body}</p>
              </div>
            ))}
          </div>
          <p className="muted">
            Check inbox reads recruiter replies from Gmail (read-only) and moves
            people along the board. No separate CRM: state lives in one database,
            and the CSVs you can open in Excel are exports of it.
          </p>
        </Section>

        {/* ── discovery + enrichment (shipped) ─────────────── */}
        <Section kicker="Finding people" title="Discovery: deterministic, now with one-click enrichment">
          <p>
            Discovery builds targeted Boolean searches for the humans behind a
            job (hiring managers, engineering leads, recruiters) as LinkedIn and
            Google X-Ray links. It’s deterministic: a template, not a model call.
          </p>
          <p>
            <em>Find and import</em> then collects the LinkedIn profiles from
            those X-Ray results, predicts a likely work email, and adds each
            person to My people, so there is no manual copy-paste. Predicted emails are tagged by
            confidence and never marked verified.
          </p>
        </Section>

        {/* ── generation pipeline ──────────────────────────── */}
        <Section kicker="The generation pipeline" title="Per lead it’s a small graph, not one call">
          <p>
            A supervisor runs one <strong>Personalization agent</strong> that
            produces a single shared hook, the sharpest sentence tying the
            candidate to this person or company, then fans out to four asset
            agents in parallel off that hook (about five model calls per lead).
          </p>
          <div className="about-pipeline">
            <span className="about-pill about-pill-dark">Personalization</span>
            <span className="about-arrow"><Icon name="arrow" size={16} /></span>
            <span className="about-pill">cold_email</span>
            <span className="about-pill">cold_dm</span>
            <span className="about-pill">cover_letter</span>
            <span className="about-pill">cv_notes</span>
          </div>
          <ul className="about-list">
            <li><strong>Shared hook</strong> keeps all four drafts coherent instead of four separate takes.</li>
            <li><strong>Conditional edge</strong> skips the email agent when a lead has no address.</li>
            <li><strong>Streaming status</strong> reports each agent’s progress as it runs.</li>
            <li><strong>Checkpoint / resume</strong>: a big batch that fails partway resumes without re-spending tokens.</li>
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
              <p>A LangGraph graph (about 5× the calls per lead and one real dependency) for coherent drafts from the shared hook, per-agent status, checkpoint/resume, and first-class human-in-the-loop interrupts. The reversal is written down as an ADR.</p>
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
        <Section kicker="Workflow" title="Every person moves across one board">
          <div className="about-flow">
            {STAGES.map((s, i) => (
              <span key={s} className="about-flow-step">
                {s}{i < STAGES.length - 1 && <span className="about-arrow"><Icon name="arrow" size={14} /></span>}
              </span>
            ))}
          </div>
          <p className="muted">
            Marking a message sent starts a follow-up clock (five days by
            default); when it runs out the person is flagged “Follow-up due” and
            the chat lists them when you ask who to chase. Replied covers
            interested, interview and offer; Finished holds the people who said no.
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
              <p>A private, token-gated web app: one Docker service on Render, Postgres on Neon. Deployment is a config choice, not a rewrite, with the same tested core underneath.</p>
            </div>
          </div>
        </Section>

        {/* ── author card ──────────────────────────────────── */}
        <Section>
          <div className="about-contact">
            <ContactForm page="about" title="Get in touch" />
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
          PACOS, the Personal AI Career Operating System. Human-in-the-loop, always.
        </p>
      </div>
      <aside className="about-aside" aria-label="About the author">
        <AuthorCard />
      </aside>
    </div>
  );
}
