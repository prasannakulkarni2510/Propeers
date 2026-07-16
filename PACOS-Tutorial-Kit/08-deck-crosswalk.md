# PACOS — Kit ↔ Deck Crosswalk & Deck Corrections

How this tutorial kit lines up with **`PACOS_How_To_Use.pptx`** (the how-to script) and
**`PACOS_Interview_Deck.pptx`**, and — importantly — **what in those decks is now out of
date** relative to the shipped app.

## Terminology is aligned
The kit uses the decks' / `CONTEXT.md` vocabulary exactly: **Lead, Asset, Operator,
Tracker, Lead sheet, Search variant, Extractor, Personalization hook, Supervisor,
Agent** (a component is only an "agent" if it makes a model call — the inbox monitor is a
*process*, not an agent).

## Kit → How-To deck slide map

| Kit piece | How-To deck slide(s) |
|-----------|----------------------|
| Intro S1–S2 (hook, two-phase idea) | 1–3 (what it is, big picture) |
| Intro S3 (Build searches) | (new — see corrections) + Interview slide 7 (deterministic discovery) |
| Intro S4–S5 (Find People, enriched leads) | **not in decks — new feature** |
| Intro S6 (Generate, agent board) | 4, 8 (pipeline; Dashboard tab) |
| Intro S7 (four drafts, Copy) | 4, 9 (asset specs; Leads & Assets) |
| Intro S8 (Approve → Track) | 10, 11 (Approvals; Tracker) |
| `05-actions-and-implications.md` | 8–11, 17 (all six/seven tabs) |
| `05` golden rules block | 2, 15 (golden rules) |
| `06-demo-walkthrough.md` | 8–11 (the everyday rhythm, slide 15) |
| Chat proposal (`screenshots/11`) | 17 (Chat — propose → confirm) |

## ⚠ Deck corrections needed (decks lag the shipped app)

The decks were written before the **auto-enrichment ("Find People")** feature shipped.
Three concrete fixes:

1. **Interview Deck · slide 10 ("Honest limits and what's next")**
   Lists **"Lead enrichment — to fill thin rows before generation runs"** under *What
   I'd build next*. **It is now built.** Move it from "next" to a shipped capability (or
   to slide 7 "Constraints/Discovery" as: *"Discovery auto-imports people from the X-Ray
   results and predicts a work email — deterministic, no scraping, no paid API."*).

2. **How-To Deck · slide 7 ("Running the App")**
   Says **"The six tabs, left to right … Dashboard → Leads → Assets → Approvals →
   Tracker → Chat."** The app now has **seven**: add **Discovery** at the end.

3. **How-To Deck · slide 9 & the Leads screen**
   The Leads table now shows **LinkedIn · Predicted Email · Confidence** columns, and
   Discovery has an **"Auto-import people / Find People"** panel. Worth a bullet:
   *"Discovery → Find People collects LinkedIn profiles from your Google X-Ray results,
   predicts a likely work email (never marked verified), and creates leads."*

> These are text/factual updates, not redesigns. The kit already reflects the corrected,
> shipped behavior — it's the decks that need the one-line refreshes above.

## What is consistent and needs no change
- Golden rules, the pipeline (1 Personalization + 4 asset agents, ~5 calls/lead, shared
  hook, conditional email skip, review-hooks, resumable), the status flow
  (`pending → sent → replied → interested → interview → offer`, branch to `rejected`),
  `tracker.db` as source of truth, read-only Gmail, and Dry-run — all match the app and
  are carried into this kit as written in the decks.
