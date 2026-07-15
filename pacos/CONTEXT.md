# PACOS

Personal AI Career Operating System — a local-first, single-user pipeline that
generates personalised job-search outreach and tracks it, keeping a human in the
loop for every send.

## Language

**Lead**:
A specific person PACOS reaches out to (a hiring manager, recruiter, or founder),
sourced into `leads.csv`. The unit the whole pipeline runs on.
_Avoid_: prospect, contact, target.

**Asset**:
One generated outreach artefact for a lead — a cold email, cold DM, cover letter,
or CV-notes file. Four assets are produced per lead in one model call.
_Avoid_: content, document, message.

**Operator**:
The single human running PACOS (the job seeker). PACOS acts on their behalf but
never sends without their explicit copy-paste.
_Avoid_: user, admin.

**Tracker**:
The authoritative record of every lead's pipeline state, stored in the local
SQLite database (`pacos.db`). `tracker.csv` is a read-only **export** of it, not
the source of truth.
_Avoid_: CRM, database, tracker.csv (that's the export file).

**Workspace**:
The one folder PACOS runs from and keeps all its state in — the lead sheet,
the tracker, generated assets, and the operator's configuration. For the
packaged app, this is the folder `PACOS.exe` sits in. One operator, one
workspace.
_Avoid_: install directory, data folder, repo root (that's the dev-mode
special case).

**Search variant** (or just **variant**):
One runnable boolean people-search for a job — a target persona group plus the
query and the LinkedIn / Google X-Ray links that run it. Built
deterministically by the discovery module (no model call, so not an agent or
extractor). Like a proposal, it never writes: the operator runs the search and
confirms any person found as a lead through the normal add-lead path.
_Avoid_: search suggestion, query template.

**Lead sheet**:
The hand-editable CSV **input** (`leads.csv`) the operator maintains. Ingested
into the tracker; distinct from the tracker itself.
_Avoid_: leads database.

## Agents

**Agent**:
A component that makes exactly one model call for one narrow job, **inside the
generation pipeline, under the Supervisor, for a lead**. PACOS has one
Personalization agent and four asset agents (one per asset type). A thing that
does not make its own model call is not an agent (e.g. the inbox monitor is a
process, not an agent), and a model-caller serving the operator directly is an
extractor, not an agent. The status board shows components (agents and the
inbox-monitor process), not only agents.
_Avoid_: bot, worker, service.

**Extractor**:
A model-backed helper that turns operator-supplied text (a pasted JD, a chat
message) into a lead proposal. PACOS has two: the JD parser and the chat
assistant. An extractor never writes — it only proposes.
_Avoid_: agent (reserved for the pipeline), parser (that's one specific
extractor), copilot.

**Lead proposal** (or just **proposal**):
Lead-sheet fields produced by an extractor, awaiting the operator's review.
A proposal only becomes a lead when the operator confirms it; extractors
cannot write one to the lead sheet or tracker themselves.
_Avoid_: draft lead, suggestion, extracted lead.

**Supervisor**:
The orchestrator that runs the agents for a lead: Personalization first, then the
four asset agents, and assembles the result. It makes no model call of its own.
_Avoid_: manager, coordinator, controller.

**Personalization hook** (or just **hook**):
The single most specific sentence tying the operator to a lead's person/company.
Produced once by the Personalization agent and shared by all four asset agents so
the outreach reads coherently.
_Avoid_: angle, opener, personalization_line (that's the CSV column name).
