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

**Lead sheet**:
The hand-editable CSV **input** (`leads.csv`) the operator maintains. Ingested
into the tracker; distinct from the tracker itself.
_Avoid_: leads database.

## Agents

**Agent**:
A component that makes exactly one model call for one narrow job. PACOS has one
Personalization agent and four asset agents (one per asset type). A thing that
does not make its own model call is not an agent (e.g. the inbox monitor is a
process, not an agent).
_Avoid_: bot, worker, service.

**Supervisor**:
The orchestrator that runs the agents for a lead: Personalization first, then the
four asset agents, and assembles the result. It makes no model call of its own.
_Avoid_: manager, coordinator, controller.

**Personalization hook** (or just **hook**):
The single most specific sentence tying the operator to a lead's person/company.
Produced once by the Personalization agent and shared by all four asset agents so
the outreach reads coherently.
_Avoid_: angle, opener, personalization_line (that's the CSV column name).
