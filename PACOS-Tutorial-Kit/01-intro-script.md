# PACOS — Intro Tutorial Script

**Format:** screen recording of the live app + voiceover.
**Length:** ~80 seconds, built as **eight 10-second segments** (S1–S8) so each clip
can be recorded, timed, and re-cut independently. Word counts are tuned to a calm
~155 wpm read (≈26 words / 10s) — leave a beat of silence at each cut.

**Voice direction:** warm, confident, unhurried. You're showing a friend a tool you
trust. Never salesy. Let the clicks breathe.

**Global animation language** (details in `04-claude-design-notes.md`):
- Titles/lower-thirds slide up 12px + fade in over 300ms, ease-out.
- Cursor is a soft-glow dot; every click emits one quick accent-orange ripple.
- "Ken Burns" push-in of 3–4% on static holds so nothing feels frozen.
- Section label chip (top-left) cross-fades between phases: **DISCOVER → GENERATE → APPROVE → TRACK.**

---

## S1 · 0:00–0:10 — Cold open
**Screen:** `screenshots/01-dashboard.png` (Dashboard, "429 leads" stat visible).
**Animation:** Start on the PACOS wordmark in the sidebar; the "O" in PAC**OS** pulses
once (accent orange). Title card slides up center: **"PACOS — your job search, run like a system."** Push-in 3%.
**Voiceover:**
> "Job hunting is a pipeline you're running by hand. PACOS runs it for you — finds the right people, drafts the outreach, and keeps you in control of every send."

## S2 · 0:10–0:20 — The one idea (two-phase split)
**Screen:** Dashboard, then a simple built-in overlay diagram (two panels: **Deterministic Discovery** ↔ **AI Generation**).
**Animation:** Two rounded cards fly in from left and right, meeting in the middle;
a thin dashed seam line draws between them. Label chip shows both phases.
**Voiceover:**
> "It works in two halves. Finding people is deterministic — no guessing. Writing outreach is AI. And nothing is ever sent without you. That line in the middle is the whole philosophy."

## S3 · 0:20–0:30 — Discovery: build the search
**Screen:** `screenshots/05-discovery-variants.png` (Discovery, Razorpay searches built).
**Animation:** Type "Razorpay" into the company field (typing cue), click **Build searches** (ripple); the seven variant cards stagger-fade in bottom-up, 60ms apart.
**Voiceover:**
> "Tell PACOS a company and a role. It builds targeted Boolean searches for the actual humans behind the job — hiring managers, engineering leads, recruiters — ready for LinkedIn or Google X-Ray."

## S4 · 0:30–0:40 — Discovery: auto-import people ⭐
**Screen:** `screenshots/06-find-people.png` → `screenshots/07-imported.png`.
**Animation:** Click **Find People**; the progress pills light one by one
(*Searching → Collecting profiles → Extracting names → Predicting email → Saving leads*),
each turning green with a check. End on the green **"3 leads imported."** with a soft confetti tick.
**Voiceover:**
> "Then the new part: one click. PACOS collects the profiles, pulls out names and titles, predicts a likely work email, and turns them into leads. The copy-paste busywork is gone."

## S5 · 0:40–0:50 — Leads: enriched, not "unknown-1"
**Screen:** `screenshots/03-leads-enriched.png` (Leads table: Name / Title / LinkedIn / Predicted Email + confidence chip).
**Animation:** Row-by-row highlight sweep down the table; zoom-punch on one
**Predicted Email** cell with its **MEDIUM** confidence chip. Callout: *"predicted — never marked verified."*
**Voiceover:**
> "Every lead arrives with a real name, a title, a LinkedIn, and a best-guess email — tagged by confidence, and never marked verified. You always know what's a fact and what's a smart guess."

## S6 · 0:50–1:00 — Generate the outreach
**Screen:** `screenshots/02-dashboard-generate.png` (Dashboard) → agent board.
**Animation:** Click **Generate with Nemotron** (ripple). The Agent Status board lights
in sequence — Personalization → Cold Email → Cold DM → Cover Letter → CV Notes — each
flipping *queued → done* with a green dot; the sixth tile, **Inbox Monitor**, stays idle
(it's a process, not a generation agent). Label chip: **GENERATE.**
**Voiceover:**
> "Now the AI half. One personalization pass finds a shared hook, then four agents draft in parallel — a cold email, a DM, a cover letter, and CV notes — all on the same angle, so they read like one person wrote them."
**Deck facts (How-To slides 4 & 8):** ~5 model calls/lead; one Personalization agent →
four asset agents; the board shows six tiles (the five agents + Inbox Monitor). Use
**Dry-run** on camera — identical board, no tokens.

## S7 · 1:00–1:10 — Review the drafts
**Screen:** `screenshots/04-assets.png` (Assets page, four tabs, Copy button).
**Animation:** Click through the four asset tabs (Cold Email → Cold DM → Cover Letter
→ CV Notes) with a smooth cross-fade; hover **Copy**, which flashes "Copied ✓".
Note the smart skip: *"no email? → DM only."*
**Voiceover:**
> "Read every draft, tweak or regenerate any one, and copy it when it's right. No email on file? PACOS skips the email and writes a DM instead. Nothing leaves this screen on its own."
**Deck facts (How-To slides 4 & 9):** the four files are `cold_email.txt` (5–7 lines),
`cold_dm.txt` (3–4 lines), `cover_letter.txt` (150–200 words), `cv_notes.txt` (5–8
bullets), also written to `output/{Company}_{First}/`. **You** copy and send — PACOS never sends.

## S8 · 1:10–1:20 — Approve & track → handoff to outro
**Screen:** `screenshots/08-approvals.png` + quick cut to `screenshots/09-tracker.png`.
**Animation:** Mark one lead **DM** sent (ripple); cut to the Tracker pipeline, a status
pill animating *pending → sent*. Pull back; sidebar footer glows: **"never auto-sends."**
Fade toward the outro's opening frame.
**Voiceover:**
> "You send by hand, then mark it here. PACOS tracks every reply and follow-up, so the whole search lives in one place. You run the pipeline. PACOS does the reps."

---

### Timing summary
| Seg | Time | Phase | Beat |
|-----|------|-------|------|
| S1 | 0:00 | — | Hook |
| S2 | 0:10 | — | Two-phase idea |
| S3 | 0:20 | DISCOVER | Build searches |
| S4 | 0:30 | DISCOVER | **Find People (enrichment)** |
| S5 | 0:40 | DISCOVER | Enriched leads |
| S6 | 0:50 | GENERATE | Generate assets |
| S7 | 1:00 | GENERATE | Review drafts |
| S8 | 1:10 | APPROVE/TRACK | Approve → track → outro |

Total intro: **80s**, then straight into the ~30s AI outro (`02-outro-prompts.md`).
