"""PACOS chat assistant — a Nemotron-backed copilot for the operator.

One turn = one `complete_json` call. The model replies with
`{"reply": <text>, "lead": null | {...}}`; when the operator mentions a
specific person/company worth tracking, `lead` carries a proposed lead-sheet
row. The proposal is only ever *shown* — the operator confirms it through the
same POST /api/leads write path as everything else (human-in-the-loop).
"""
from __future__ import annotations

from .graph.prompts import strip_dashes
from .jd_parser import PROPOSAL_KEYS, normalise_proposal
from .llm import NemotronClient, NemotronError

_SYSTEM = """You are the PACOS assistant — the copilot inside the operator's
Personal AI Career Operating System, a local job-search outreach tool.

PACOS pipeline: leads (people at companies) -> generated outreach assets
(cold email, cold DM, cover letter, CV notes) -> operator sends manually ->
replies tracked. PACOS NEVER sends anything itself; never claim otherwise.

Current tracker snapshot: {stats}

Help the operator with outreach strategy, wording, prioritising leads, and
capturing new leads from whatever they paste or describe.

Reply with ONLY a JSON object:
  {{"reply": "<your conversational answer, plain text>",
    "lead": null}}

EXCEPT when the operator wants someone or some company tracked as a lead —
any add/track intent counts ("add rahul to my leads", "add Swiggy", a pasted
JD, a name mentioned for outreach), no matter how incomplete the details are.
Then ALWAYS set "lead" to an object with these string keys, filling what you
know and leaving the rest as empty strings (never invent, never refuse for
missing fields — the operator completes them on the review card): {keys}.
persona_tag must be one of hr|engineer|manager|cto|ceo (or empty).
In that case "reply" should briefly say what you captured, list what is
missing, and remind the operator to review and confirm before it is saved.
Do NOT respond with only questions when add-intent is present — attach the
partial lead as well."""

_OFFLINE_REPLY = (
    "Chat needs Nemotron, and NVIDIA_API_KEY is not set in .env. "
    "You can still add leads with the Add-lead form or the JD parser "
    "(both work offline)."
)


def chat_turn(
    client: NemotronClient, stats: dict, messages: list[dict]
) -> tuple[str, dict | None, list[str], bool]:
    """Run one chat turn. Returns (reply, lead_proposal|None, warnings, llm_used)."""
    if not client.available:
        return _OFFLINE_REPLY, None, [], False

    # Serialise history into one prompt; last message is the live question.
    lines = []
    for m in messages[-16:]:  # keep the window bounded
        who = "Operator" if m.get("role") == "user" else "Assistant"
        lines.append(f"{who}: {m.get('content', '').strip()}")
    convo = "\n\n".join(lines)

    system = _SYSTEM.format(stats=stats, keys=", ".join(PROPOSAL_KEYS))
    try:
        raw = client.complete_json(
            system=system,
            user=f"Conversation so far:\n\n{convo[-16000:]}\n\nRespond to the operator's last message.",
            temperature=0.5,
            max_tokens=1536,
        )
    except NemotronError as e:
        return f"Nemotron error: {e}", None, [], False

    # House style everywhere: no em/en dashes in anything the operator reads.
    reply = strip_dashes(str(raw.get("reply", "") or "").strip()) \
        or "(empty reply from model)"
    proposal, warnings = None, []
    lead = raw.get("lead")
    if isinstance(lead, dict) and any(str(v or "").strip() for v in lead.values()):
        proposal, warnings = normalise_proposal(lead)
    return reply, proposal, warnings, True
