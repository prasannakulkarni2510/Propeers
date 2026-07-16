# PACOS — Demo Data Processing Walkthrough

A reproducible, on-camera demo that shows **real data flowing through the pipeline** —
discovery → enrichment → generation → approval → tracking. Use this as the literal
click-path for the intro recording, or as a standalone "watch it process" clip.

Every number and output below is **verified against the running app** (not invented),
using a throwaway demo company (**Acme Robotics**) so your real 429 leads stay untouched.
Clean-up command is at the end.

> Setup: app running at `http://127.0.0.1:8000`. Use **Dry-run** for all generation so
> the demo needs no API key and spends no tokens — the flow looks identical.

---

## Scene 1 — Discovery builds the searches (🟢 writes nothing)

1. Go to **Discovery**.
2. Type **Company = `Acme Robotics`**, **Role = `Robotics Engineer`**, **City = `Pune`**.
3. Click **Build searches**.

**What processes:** PACOS generates **7 search variants** (Hiring Managers, Engineering
Managers & Leads, Directors, Technical Recruiters, Talent Acquisition, HR Business
Partners, and a broad catch-all). Each shows a Boolean query + LinkedIn / Google X-Ray links.

**On screen to point at:** the query anchors on the company and ORs the target titles —
this is deterministic, so it's instant and identical every time.

---

## Scene 2 — Find People enriches into leads ⭐ (🟡 writes leads)

1. Click **Find People**.
2. The live fetch of Google usually hits a consent wall → the progress ends with
   *"No profiles collected"* and reveals **Paste results instead**. (This is expected —
   Google blocks automated scraping; the operator-paste keeps it 100% Google, no paid API.)
3. Click **Paste results instead**, paste a Google X-Ray results page, click **Import from pasted results**.

**Demo paste (use this exact HTML so the numbers match the recording):**
```html
<div><a href="https://in.linkedin.com/in/asha-verma-acme"><h3>Asha Verma - Engineering Manager - Acme Robotics | LinkedIn</h3></a></div>
<div><a href="https://in.linkedin.com/in/rohan-das-acme"><h3>Rohan Das - Technical Recruiter at Acme Robotics | LinkedIn</h3></a></div>
<div><a href="https://uk.linkedin.com/in/mei-lin-acme"><h3>Mei Lin - Director of Engineering - Acme Robotics | LinkedIn</h3></a></div>
```

**What processes (verified output):**
```
profiles_found: 3 | leads_imported: 3 | source: pasted
  - Asha Verma      | Engineering Manager   | asha.verma@acmerobotics.com   (medium)
  - Rohan Das       | Technical Recruiter   | rohan.das@acmerobotics.com    (medium)
  - Mei Lin         | Director of Engineering| mei.lin@acmerobotics.com     (medium)
```
Result banner: **"3 leads imported."**

**On screen to point at:** it parses each result title into *name · title*, predicts a
work email (`first.last@` on the company domain), and tags confidence **medium** —
because the domain is *guessed* from the name, not confirmed from a website. Duplicates
(same profile twice) collapse to one; a job link (not a `/in/` profile) is ignored.

---

## Scene 3 — The leads are enriched, not blank (🟢)

1. Go to **Leads**, search **`Acme`**.

**What you see:** three real rows — **Name · Title · LinkedIn (profile ↗) · Predicted
Email + confidence chip** — instead of the old `unknown-acme-1` placeholders. This is the
before/after the whole feature exists to create.

---

## Scene 4 — Generate the four assets (🔵 in real mode / 🟡 dry-run)

1. Go to **Dashboard**, click **Dry-run (templates)** (or **Generate with Nemotron** for real).

**What processes (verified, dry-run):**
```
requested: 1  generated: 1   (only the asset-less demo lead is built)
assets: cold_email.txt, cold_dm.txt, cover_letter.txt, cv_notes.txt
```
Because Asha has a predicted email, the **cold email is generated** (the `has_email`
routing). A lead with no email would show only DM + cover letter + CV notes.

**On screen to point at:** the Agent Status board lighting up Personalization → the four
asset agents, each flipping *queued → done*.

---

## Scene 5 — Review a processed draft (🟢🔒)

1. Go to **Assets**, pick **Acme Robotics — … (asha)**, open **Cold DM**.

**Sample processed output (dry-run):**
> "Hi Asha, I've been following Acme Robotics's work in AI/ML and your Engineering
> Manager team. I'm an Aspiring AI Engineer keen on Acme Robotics. Open to connecting?
> (Dry run placeholder.)"

In real mode this is a full Nemotron draft on a shared personalized angle. **Copy** puts
it on your clipboard — *you* paste and send. Nothing leaves PACOS on its own.

---

## Scene 6 — Approve & track (🟡🔒)

1. **Approvals** → the demo lead appears under **Ready to send** → click **Mark sent as → DM**.
2. **Tracker** → the lead's status animates **pending → sent**, with a follow-up date set.

**What processes:** PACOS records *your* send and schedules the follow-up. It never sent
anything — it logged what you did and now tracks the reply.

---

## One-line summary for the voiceover
> "Three people found and emailed-predicted in one click, four drafts written in another,
> and a pipeline that tracks itself — all without a single message sent behind your back."

---

## Clean up the demo data (so your real pipeline is untouched)
Run after recording:
```bash
for id in acme-robotics-asha acme-robotics-rohan acme-robotics-mei; do
  curl -s -X DELETE "http://127.0.0.1:8000/api/leads/$id" >/dev/null
done
```
Or click **Remove** on each Acme row in the Leads page (two-click confirm).
