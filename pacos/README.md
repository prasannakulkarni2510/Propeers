# PACOS — Personal AI Career Operating System

A lightweight, human-in-the-loop pipeline that turns a manual job search into a
few small scripts. It generates personalised outreach from a lead spreadsheet,
reads your Gmail for job alerts and recruiter replies, and keeps a single live
tracker so nothing slips.

> **Hard constraints:** PACOS never auto-sends — every outreach is copy-pasted by
> a human after review. The inbox monitor is strictly **read-only**. And no
> model-proposed data is ever written without operator confirmation: extractors
> (the JD parser, the chat assistant) only *propose* leads; the operator confirms
> each one into the lead sheet.

**Generation runs on NVIDIA Nemotron** (via the OpenAI-compatible NVIDIA NIM API),
not Claude. Swap the model with one env var.

---

## Three light layers

| Layer | Component | What it does | In / Out |
|-------|-----------|--------------|----------|
| 1 | **Asset Generator** | One Nemotron call per lead → four outreach files | `leads.csv` → `output/` |
| 2 | **Inbox Monitor** | Read-only Gmail parse of LinkedIn/Naukri alerts + recruiter replies | Gmail → `tracker.csv`, `new_jobs.csv` |
| 3 | **Tracker** | One CSV with all pipeline state + follow-up logic + daily digest | all layers → `tracker.csv` |

No orchestration framework, no database, no dashboard — plain files you can open
in Excel.

---

## Setup

```bash
cd pacos
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -e .

cp .env.example .env        # then fill in NVIDIA_API_KEY
cp data/sample_leads.csv data/leads.csv   # or supply your own
```

Get a **free** Nemotron key at <https://build.nvidia.com> → pick any Nemotron
model → **Get API Key**, and paste it into `.env` as `NVIDIA_API_KEY`.

---

## Usage

```bash
# Layer 1 — generate assets for every lead (writes output/ + tracker.csv)
pacos generate                 # uses Nemotron
pacos generate --dry-run       # offline templates, no API call (great for testing)
pacos leads                    # preview parsed leads + auto domain_tag

# Human-in-the-loop CRM updates
pacos sent   <lead_id> --channel both      # after you copy-paste and send
pacos reply  <lead_id> --intent interested # record a recruiter reply
pacos status <lead_id> interview           # advance the status flow

# Layer 2 — read Gmail (requires one-time auth below)
pacos monitor --days 1

# Layer 3 — today's action list
pacos digest
```

`lead_id` is the slug shown by `pacos leads` (e.g. `nurix-ai-aarav`).

### Status flow

```
pending → sent → replied → interested → interview → offer
                                              └────────→ rejected
```

---

## The lead sheet

Everything runs off `data/leads.csv`. Required columns:
`full_name, job_title, company_name, city, linkedin_url, persona_tag`
(persona = `hr | engineer | manager | cto | ceo`).

Optional enrichments sharpen personalisation and feed the domain classifier:
`email, company_size, industry, company_website, funding_stage`.
`first_name` and `domain_tag` are derived automatically.
See `data/sample_leads.csv` for a complete example.

---

## Per-lead output

```
output/{company}_{first_name}/
├── cold_email.txt      # 5–7 lines, used when email is known
├── cold_dm.txt         # 3–4 lines, LinkedIn DM
├── cover_letter.txt    # 150–200 words, formal applications
└── cv_notes.txt        # bullets: how to tweak your CV for this role
```

Tone adapts to `domain_tag` (`startup · scaleup · enterprise · product ·
services · research`).

---

## Gmail Inbox Monitor (one-time setup, ~15 min)

1. Create a project at <https://console.cloud.google.com> and **enable the Gmail API**.
2. Create **OAuth 2.0 Desktop** credentials, download as `credentials.json`.
3. Point `GMAIL_CREDENTIALS_PATH` at it in `.env`.
4. Run once:
   ```bash
   python scripts/auth_gmail.py
   ```
   This opens a browser once and writes `token.json`. All later runs reuse it.

Only the `gmail.readonly` scope is requested. The monitor never sends, deletes,
labels, or modifies mail.

---

## Model configuration

| Env var | Default | Notes |
|---------|---------|-------|
| `NVIDIA_API_KEY` | — | required for real generation |
| `NEMOTRON_MODEL` | `nvidia/llama-3.1-nemotron-70b-instruct` | any Nemotron instruct model |
| `NEMOTRON_BASE_URL` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible endpoint |

Because the endpoint is OpenAI-compatible, you can point `NEMOTRON_BASE_URL` at a
self-hosted NIM container without code changes.

---

## Tests

```bash
pip install pytest
pytest -q      # pure logic: classifier, lead parsing, JSON extraction, tracker
```

## Recruiter Discovery

The **Discovery** page (and the "Find people" button on every lead row / chat
proposal) builds boolean people-searches for the humans behind a job — hiring
managers, engineering managers, directors, recruiters, TA, HRBPs — from the
company/role/location PACOS already knows. Each variant comes with a
pre-filled LinkedIn people-search link, a Google X-Ray link, and the raw
query to copy. Deliberately deterministic (no model call) and read-only: you
open the search in your browser, pick a person, and confirm them as a lead
like any other. No scraping — see Legal.

## Deploy online

PACOS can run as a private, token-gated web app (one Docker service on
Render; SQLite + assets on a persistent disk). See
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the platform comparison,
secret-management rules, and step-by-step instructions.

## Legal

All lead data is user-supplied. No scrapers are shipped. You are responsible for
complying with the terms of service of any platform you source leads from.
