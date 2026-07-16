# PACOS — Tutorial & Launch Video Kit

Everything needed to produce a polished **intro tutorial** (screen recording + voiceover)
and an **outro** (AI-generated video via Kling or Google Omni/Veo) for PACOS
— the Personal AI Career Operating System.

This kit is built so onboarding feels effortless, the way Notion or Linear feel on
first open: the app is walked one action at a time, each with a clear reason.

## Contents

| File | What it is |
|------|-----------|
| `README.md` | This file — the master plan. |
| `01-intro-script.md` | The full intro tutorial: shot list, on-screen animation cues, and voiceover, in 10-second segments. |
| `02-outro-prompts.md` | Copy-paste prompts for Kling and Google Omni/Veo, each a self-contained 10-second segment. |
| `03-shot-list.md` | Exact capture recipe for every screenshot/clip (URL + state + what to record). Drop the recordings into `screenshots/`. |
| `04-claude-design-notes.md` | Motion, color, and typography spec so titles/lower-thirds match the app's own design language. |
| `05-actions-and-implications.md` | **What every click opens and does** — the interaction map + a legend for writes / tokens / deletes / never-sends. The onboarding reference. |
| `06-demo-walkthrough.md` | **Demo-data processing** — a reproducible click-path (Acme Robotics demo) with verified inputs/outputs, end to end. |
| `07-screenshot-gallery.md` | Index of every captured PNG — the 7 page screens **and** 8 click-interaction states (add-lead forms, chat proposal, import result). |
| `08-deck-crosswalk.md` | Maps this kit to `PACOS_How_To_Use.pptx` slides, and lists the 3 slides where the decks now lag the shipped app. |
| `screenshots/` | **15 real PNGs** of the app: page states + button-click interaction states. Captured live. |

---

## Do you need a video to use PACOS? — Short answer: **No, but a 75-second intro pays for itself.**

PACOS is genuinely usable without any video. The left nav is linear (Dashboard →
Leads → Assets → Approvals → Tracker → Chat → Discovery), every screen has a
one-line subtitle explaining itself, and nothing is ever auto-sent, so a new
operator cannot break anything. In Notion terms: the empty states already teach.

**Where a video *does* earn its place** is the one non-obvious idea at the heart of
PACOS — the **two-phase split**:

1. **Discovery is deterministic** (Boolean + Google X-Ray + auto-enrichment builds leads).
2. **Generation is AI** (a lead → four outreach assets), and **you approve every send.**

That "the machine finds and drafts, the human decides and sends" model is the thing
worth *showing* rather than reading. So: **make the intro, skip a mandatory tutorial.**
Ship the intro as an optional "Watch the 75-sec tour" link on the Dashboard empty
state — present, not blocking. (See "Notion-style onboarding" at the bottom.)

---

## Source of truth: the PACOS decks

This kit is written to match your existing **`PACOS_How_To_Use.pptx`** (the how-to
script) and **`PACOS_Interview_Deck.pptx`**. Terminology, golden rules, and the workflow
loop below are taken verbatim-in-spirit from those decks so the video, the app, and the
decks all say the same thing.

**One place the kit is deliberately *ahead* of the decks:** the decks predate the
**auto-enrichment ("Find People")** feature — the Interview Deck still lists "Lead
enrichment" under *What's next* (slide 10), and the How-To deck describes Discovery as
manual Boolean/X-Ray copy-paste (slide 7, "six tabs"). The app now ships enrichment as a
7th tab. This kit documents the shipped behavior; see `08-deck-crosswalk.md` for the exact
slides to refresh.

## Golden rules (from How-To deck, slides 2 & 15 — narrate these, they build trust)

- **PACOS never sends** — you review, copy, and send every message yourself. There is no send path in the code.
- **Extractors only propose** — the JD parser and Chat turn text into a *lead proposal*; nothing is saved until you confirm.
- **Always read an asset before sending it** — you are the last check.
- **The inbox monitor is read-only** — scope is `gmail.readonly`; it never sends, labels, or deletes.
- **`tracker.db` is the source of truth**; `tracker.csv` is an export.
- **Dry-run first** when trying anything new — template placeholders, no tokens.

## The story the video tells (why this order)

The decks' canonical loop (How-To slide 16):

> **Generate → review → send by hand → log → track. Repeat.**

The video widens it by one step at the front — the new enrichment capability that fills
the roster before generation runs:

> **Find the right people → let AI draft the outreach → you approve → track the replies.**

- **Intro (screen recording, ~75s):** the real app doing the real loop. Trust comes
  from seeing actual clicks, not motion graphics.
- **Outro (AI video, ~30s):** aspirational, not literal — the *feeling* of a landed
  interview. This is where Kling/Omni shine and where a screen recording would be flat.

---

## Production checklist

1. Record the intro clips per `03-shot-list.md` (app already running at `http://127.0.0.1:8000`).
2. Lay the voiceover from `01-intro-script.md` over them; use the animation cues for titles/zooms.
3. Generate the outro segments from `02-outro-prompts.md` (Omni = 10s each, stitch 3; Kling = one 30s if available).
4. Apply the motion/type spec in `04-claude-design-notes.md` so both halves feel like one product.
5. Music: one calm, forward-moving track under the whole thing; duck under voiceover.

---

## Notion-style onboarding (in-app, no video required)

To make PACOS teach itself the way you asked:

- **Dashboard empty state** (0 leads): replace the stat row with a 3-step checklist —
  "① Add or import leads → ② Generate assets → ③ Approve & track." Each step links to
  the page. Add a small "▶ 75-sec tour" text link (opens the intro video in a modal).
- **First-run tooltips**: a one-time coach-mark on "Generate with Nemotron" and on
  Discovery's "Find People" button — the two actions a newcomer hesitates on.
- **Never-auto-sends reassurance**: keep the sidebar footer line visible; it's the
  single most trust-building sentence in the app.

None of these require a video; the video is the optional deep-dive.
