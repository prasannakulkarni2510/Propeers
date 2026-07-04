# Multi-agent generation on LangGraph

Asset generation is a LangGraph graph, not a single model call. Per lead: a
**Personalization agent** runs first and produces one shared hook + domain read;
then four **asset agents** (cold_email, cold_dm, cover_letter, cv_notes) run in
parallel using that shared context; a **supervisor** orchestrates and assembles
the result (~5 calls/lead). A conditional edge skips the cold_email agent when the
lead has no email. Agents call the existing Nemotron client directly, so the graph
stays model-agnostic.

This **reverses the design PDF** (§5: "one Claude API call per lead… four files"),
which deliberately avoided any orchestration framework. We accept ~5x the calls
per lead and a real dependency (langgraph + langchain-core) in exchange for:

- **Coherent output** — the shared hook keeps all four assets on the same angle.
- **Truthful live status** — LangGraph streaming makes the per-agent UI board real.
- **Checkpoint/resume** — a 500-lead batch that fails partway resumes without
  re-spending tokens.
- **Human-in-the-loop interrupts** — first-class support for the "operator approves
  every send" constraint.

The inbox monitor is explicitly **not** an agent — it makes no model call.
Superseded scope note: `job_scout` is dropped (the lead CSV is the job source).
