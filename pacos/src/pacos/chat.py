"""PACOS chat assistant — a Nemotron-backed copilot for the operator.

One turn = one `complete_json` call. The model replies with
`{"reply": <text>, "lead": null | {...}, "draft": null | {...}}`; when the
operator mentions a specific person/company worth tracking, `lead` carries a
proposed lead-sheet row. The proposal is only ever *shown* — the operator
confirms it through the same POST /api/leads write path as everything else
(human-in-the-loop). When the operator asks for a piece of outreach ("write an
email to X asking for Y"), `draft` names it and a second call writes it with the
same spec, playbook and CV grounding as the pipeline assets.
"""
from __future__ import annotations

from typing import Callable

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

Answer the operator's LAST message. Earlier messages are context only: never
carry a person or company over from them unless the last message refers back.
Every name and company you output must come from the operator's own words;
the placeholders in these instructions (<person>, <company>) are not real.

Reply with ONLY a JSON object:
  {{"reply": "<your conversational answer, plain text>",
    "lead": null,
    "draft": null}}

WHEN the operator asks you to write, draft, or compose outreach (an email, a
cold email, a DM, a LinkedIn note or message, a cover letter), set "draft":
  {{"asset": "cold_email" | "cold_dm" | "cover_letter",
    "to": {{"full_name": "", "job_title": "", "company_name": "", "city": ""}},
    "request": "<what the operator is asking for, in their words>"}}
Use cold_dm for LinkedIn notes/messages/DMs, cover_letter for cover letters,
cold_email otherwise. Fill "to" only from the operator's words. Keep "reply"
to one short line (the draft itself is written separately and shown below
it), and leave "lead" null unless they also asked to track someone.

WHEN the operator wants someone or some company tracked as a lead (any
add/track intent: "add <person> to my leads", "track <company>", a pasted JD),
no matter how incomplete the details are.
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


DRAFT_ASSETS = ("cold_email", "cold_dm", "cover_letter")
_DRAFT_NAMES = {"cold_email": "email", "cold_dm": "LinkedIn DM",
                "cover_letter": "cover letter"}


def chat_turn(
    client: NemotronClient, stats: dict, messages: list[dict],
    *, drafter: Callable[[str, dict, str], str] | None = None,
) -> tuple[str, dict | None, list[str], bool, dict | None]:
    """Run one chat turn. Returns (reply, lead_proposal|None, warnings,
    llm_used, draft|None). `drafter(asset, to, request)` writes a requested
    draft; without one, drafts are not offered."""
    if not client.available:
        return _OFFLINE_REPLY, None, [], False, None

    # Serialise history into one prompt; last message is the live question.
    lines = []
    for m in messages[-16:]:  # keep the window bounded
        who = "Operator" if m.get("role") == "user" else "Assistant"
        lines.append(f"{who}: {m.get('content', '').strip()}")
    convo = "\n\n".join(lines)

    system = _SYSTEM.format(stats=stats, keys=", ".join(PROPOSAL_KEYS))
    user = f"Conversation so far:\n\n{convo[-16000:]}\n\nRespond to the operator's last message."
    # The model sometimes returns the lead with an empty or misnamed "reply";
    # one retry usually fixes it, and a proposal alone still gets a reply.
    for attempt in range(2):
        try:
            raw = client.complete_json(
                system=system, user=user, temperature=0.5, max_tokens=1536)
        except NemotronError as e:
            return f"Nemotron error: {e}", None, [], False, None
        proposal, warnings = None, []
        lead = raw.get("lead")
        if isinstance(lead, dict) and any(str(v or "").strip() for v in lead.values()):
            proposal, warnings = normalise_proposal(lead)
        reply = _reply_text(raw)
        want = _draft_request(raw)
        if reply or proposal or want:
            break

    draft = None
    if want and drafter is not None:
        asset, to, request = want
        try:
            draft = {"asset": asset, "text": strip_dashes(drafter(asset, to, request))}
        except NemotronError as e:
            return f"Nemotron error while drafting: {e}", proposal, warnings, True, None
        # Fixed line, not the model's: it sometimes writes its own rough
        # draft into "reply", which would show twice and skip the rules.
        reply = f"Here's a draft {_DRAFT_NAMES[asset]}. Review it before sending."

    if not reply:
        reply = (_proposal_reply(proposal) if proposal
                 else "Sorry, I didn't get a usable answer that time. Please try again.")
    # House style everywhere: no em/en dashes in anything the operator reads.
    return strip_dashes(reply), proposal, warnings, True, draft


def _draft_request(raw: dict) -> tuple[str, dict, str] | None:
    d = raw.get("draft")
    if not isinstance(d, dict):
        return None
    asset = str(d.get("asset", "")).strip()
    if asset not in DRAFT_ASSETS:
        return None
    to = d.get("to") if isinstance(d.get("to"), dict) else {}
    return asset, to, str(d.get("request", "") or "").strip()


def _reply_text(raw: dict) -> str:
    for key in ("reply", "response", "message", "answer", "text"):
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _proposal_reply(proposal: dict) -> str:
    who = proposal.get("full_name") or "this lead"
    where = proposal.get("company_name")
    return (f"I've drafted a lead for {who}" + (f" at {where}" if where else "")
            + ". Review the card below and fill in anything missing before adding it.")
