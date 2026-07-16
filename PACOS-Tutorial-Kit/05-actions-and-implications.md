# PACOS — Actions, What They Open, and What They Do

The onboarding reference. For every clickable thing: **what it opens or triggers**,
and its **implication** — does it write, cost tokens, hit the network, delete, or send?
This is what the tutorial narrates as it clicks, and what the in-app tooltips should say.

## Implication legend

| Tag | Meaning |
|-----|---------|
| 🟢 | Read-only / navigation — safe, changes nothing |
| 🟡 | Writes local state — reversible (edit/regenerate/delete later) |
| 🔵 | Makes a model call — costs tokens / needs an API key (Dry-run avoids this) |
| ↗ | Opens a third-party site in a new tab (LinkedIn, Google, Gmail) |
| 🔴 | Destructive — removes data |
| 🔒 | **Never auto-sends** — a human does the actual sending, always |

The golden rule, stated once and true everywhere: **PACOS drafts and tracks; you send.**

The deck's full golden rules (How-To slides 2 & 15) — the promises every 🔒/🟡 action keeps:
1. **PACOS never sends** — no send path exists in the code.
2. **Extractors only propose** — JD parser & Chat write nothing until you confirm.
3. **Always read an asset before sending it.**
4. **The inbox monitor is read-only** (`gmail.readonly`).
5. **`tracker.db` is the source of truth**; `tracker.csv` is an export.
6. **Dry-run first** — no tokens.

---

## Sidebar (always visible)
The nav is a linear pipeline, left to right in intended order.

| Click | Opens | Implication |
|-------|-------|-------------|
| Dashboard / Leads / Assets / Approvals / Tracker / Chat / Discovery | That page | 🟢 |
| Footer "never auto-sends" | (label only) | 🟢 — the trust anchor; keep it on screen |

---

## Dashboard — the control room
| Action | What happens | Implication |
|--------|--------------|-------------|
| Stat cards (Leads, With assets, Follow-ups due, Interested, Interviews) | Live counts of your pipeline | 🟢 |
| **Generate with Nemotron** | Runs the generation pipeline for every lead **missing** assets: one personalization pass + four asset agents per lead | 🔵🟡🔒 — real model calls; writes four assets per lead; nothing is sent |
| **Dry-run (templates)** | Same pipeline, but produces placeholder templates with **no API key and no tokens** | 🟡 — safe way to see the flow / demo it |
| **Review hooks** (checkbox) | Auto-approves the personalization "hook" per lead during generation | 🟡 |
| Agent status board | Live per-agent state (queued → done) as a run progresses | 🟢 |

> Implication to narrate: "Generate only builds leads that don't have assets yet — so
> adding one lead and clicking here builds *that* lead, not all 429."

---

## Leads — the roster
| Action | What happens | Implication |
|--------|--------------|-------------|
| **+ Add lead from JD** | Opens a paste box; an *extractor* reads the job description and **proposes** fields | 🔵 — proposal only; nothing is written until you confirm |
| **+ Add lead manually** | Opens a form for one lead | 🟡 on submit — writes to lead sheet + tracker |
| Search / Domain / All-leads filters | Filters the visible rows | 🟢 — client-side only |
| **Row click** | Opens that lead's **Assets** page (`/assets/:id`) | 🟢 |
| **profile ↗** | Opens the lead's LinkedIn profile in a new tab | ↗ |
| **Find people** (row) | Jumps to **Discovery**, pre-filled with that lead's company/role/city | 🟢 |
| **Remove** (two-click confirm) | Deletes the lead from the tracker, the lead sheet, and its generated assets | 🔴 — scoped to one lead; two clicks required on purpose |
| Predicted Email + confidence chip | Shows the guessed email and how sure PACOS is | 🟢 — *predicted, never verified* |

---

## Discovery — find the humans behind a job
| Action | What happens | Implication |
|--------|--------------|-------------|
| Company / Role / City / Keywords | Inputs that seed the search | 🟢 |
| **Build searches** | Generates 7 Boolean **search variants** (hiring managers, leads, recruiters, TA, HRBPs, broad) | 🟢 — deterministic; writes nothing |
| **LinkedIn search** (per card) | Opens LinkedIn people-search pre-filled with the query | ↗ |
| **Google X-Ray** (per card) | Opens a Google `site:linkedin.com/in` search | ↗ |
| **Copy query** | Copies the Boolean string to your clipboard | 🟢 |
| **Find People** ⭐ | Runs the X-Ray, extracts profiles, predicts emails, and **creates leads** | 🟡🔒 — writes leads with predicted emails; still human-reviewed, nothing sent |
| **Paste results instead** → **Import from pasted results** | Same import, from a Google results page you paste (used when Google blocks the auto-fetch) | 🟡 — the source stays your own Google query, no paid API |

> "Find People" is the one genuinely new capability — it replaces manual copy-paste
> from search results. Everything it makes is a normal lead you can edit or remove.

---

## Assets — the four drafts per lead
| Action | What happens | Implication |
|--------|--------------|-------------|
| Search leads / dropdown | Picks which lead's assets to view | 🟢 |
| Cold Email / Cold DM / Cover Letter / CV Notes tabs | Switches the shown draft | 🟢 |
| **Regenerate** | Rewrites **that one** asset via a fresh model call | 🔵🟡 |
| **Copy** | Copies the draft to your clipboard (to paste into email/LinkedIn yourself) | 🟢🔒 |
| "(not generated — lead has no email…)" | The conditional skip: no email on file ⇒ no cold email, DM only | 🟢 — expected behavior, not an error |

---

## Approvals — human-in-the-loop
| Action | What happens | Implication |
|--------|--------------|-------------|
| **Ready to send → Mark sent as (DM / Email / Both)** | Records that **you** sent it; sets status = sent and a follow-up date | 🟡🔒 — you send by hand first, then log it here |
| **Awaiting reply → intent (interested / rejected / follow-up)** | Records the reply outcome | 🟡 |
| **Unmatched replies → pick lead → Link** | Attaches an inbox reply the monitor couldn't match to the right lead | 🟡 |

---

## Tracker — the whole pipeline
| Action | What happens | Implication |
|--------|--------------|-------------|
| **Scan inbox** | One-shot Gmail read: classifies replies, collects job alerts (needs one-time OAuth) | ↗🟡 — reads mail; writes classifications; never sends |
| Search / status filter | Filters rows | 🟢 |
| **Set status** dropdown (per row) | Moves a lead's pipeline status | 🟡 |

---

## Chat — describe a person or paste a JD
| Action | What happens | Implication |
|--------|--------------|-------------|
| Message box + **Send** | The assistant answers and may **propose** a lead from what you describe | 🔵 — proposal only; you confirm before it's written |

---

## The one-glance interaction map (for a diagram card in the video)

```
Discovery ──Build searches──▶ 7 variants ──Find People──▶ Leads(+predicted email)
                                                              │ row click
                                                              ▼
Dashboard ──Generate──▶ 4 Assets/lead ◀──────────────── Assets (Regenerate / Copy)
                                                              │ Copy → you send by hand
                                                              ▼
                                        Approvals ──Mark sent──▶ Tracker (status, replies)
                                                              ▲
                                        Scan inbox ───replies──┘
```
Every arrow that changes data is 🟡; the only 🔴 is **Remove**; there is **no arrow that sends** — that step is always you.
