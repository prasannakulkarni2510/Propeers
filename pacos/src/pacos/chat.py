"""PACOS chat assistant — a Nemotron-backed copilot for the operator.

One turn = one `complete_json` call. The model replies with
`{"reply": <text>, "lead": null | {...}, "draft": null | {...}}`; when the
operator mentions a specific person/company worth tracking, `lead` carries a
proposed lead-sheet row. The proposal is only ever *shown* — the operator
confirms it through the same POST /api/leads write path as everything else
(human-in-the-loop). When the operator asks for a piece of outreach ("write an
email to X asking for Y"), `draft` names it and a second call writes it with the
same spec, playbook and CV grounding as the pipeline assets.

Questions about the operator's own data ("where am I with <person>?") are
answered from records that retrieval.py looks up for each turn: matching
leads with their live tracker state, assets and inbox replies. The model says
which leads it used (`records`), and those come back as cards for the UI.

When the operator reports something that happened ("Rajesh rejected me",
"I emailed Priya today"), `change` proposes one update to one looked-up lead.
Like lead proposals it is only shown: the operator applies it from a card
(POST /api/chat/apply, or DELETE /api/leads/<id> for a removal).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Callable

from .graph.prompts import strip_dashes
from .jd_parser import PROPOSAL_KEYS, normalise_proposal
from .llm import NemotronClient, NemotronError
from .retrieval import Retrieval, record_context

_SYSTEM = """You are the PACOS assistant — the copilot inside the operator's
Personal AI Career Operating System, a local job-search outreach tool.

PACOS pipeline: leads (people at companies) -> generated outreach assets
(cold email, cold DM, cover letter, CV notes) -> operator sends manually ->
replies tracked. PACOS NEVER sends anything itself; never claim otherwise.

Today is {today}. Dates around today: {calendar}
Current tracker snapshot: {stats}

RECORDS from the operator's PACOS data, looked up for this question (may be
empty or only loosely related):
<<<
{records}
>>>

Help the operator with outreach strategy, wording, prioritising leads, and
capturing new leads from whatever they paste or describe.

Answer the operator's LAST message. Earlier messages are context only: never
carry a person or company over from them unless the last message refers back.
Every name and company you output must come from the operator's own words
or from RECORDS; the placeholders in these instructions (<person>, <company>)
are not real.

Reply with ONLY a JSON object:
  {{"reply": "<your conversational answer, plain text>",
    "records": [],
    "lead": null,
    "draft": null,
    "change": null}}

WHEN the operator asks about their own leads, outreach, replies, follow-ups or
drafts (where things stand with someone, their "position", "stage" or
"status", who replied, who to chase, what an email said), answer ONLY from
RECORDS. PACOS has no chat logs with contacts: "my chat/conversation/thread
with <person>" means the outreach to them, so answer with where it stands
instead of saying no chat was found. Lines starting with "Note:" in RECORDS
are guidance for you; never quote them. Say plainly where each person stands (sent or not, by which channel
and when, any reply and its intent, when to follow up), quoting dates exactly.
Several people with the same name: list each with their company and ask which
one is meant. Nobody in RECORDS fits: say you couldn't find them in PACOS and
suggest adding them as a lead. Never guess a status, date or reply. RECORDS is
the only truth about the data: earlier messages may be out of date (a lead
can be updated or deleted since), so never repeat facts about a person from
the conversation unless RECORDS still shows them. Write plain sentences: do
not copy labels like "Tracker status:", "Board column:" or lead_ids into the
reply, and only mention follow-ups or other leads when asked about them. Put the
lead_id of every lead your reply talks about into "records" (they are shown
to the operator as cards under your reply); otherwise leave it empty.

WHEN the operator tells you something happened with a lead, or asks to update
or delete one ("<person> rejected me", "I emailed <person> today", "<person>
replied, interested", "interview with <company> on Friday", "add a note",
"delete <person>"), and exactly ONE lead in RECORDS is that person, set
"change":
  {{"lead_id": "<lead_id from RECORDS>",
    "action": "sent" | "reply" | "status" | "note" | "delete",
    "channel": "email" | "dm" | "both" | "",
    "intent": "interested" | "follow-up" | "rejected" | "",
    "status": "pending" | "sent" | "replied" | "interested" | "interview" | "offer" | "rejected" | "",
    "date": "YYYY-MM-DD" | "",
    "note": "<short detail worth keeping, e.g. the role or the interview time>"}}
Use "sent" (with channel) when they sent outreach; "reply" (with intent) when
the person answered, including a rejection; "status" for interview, offer or
any other direct status; "note" to only record a detail; "delete" only when
they explicitly ask to remove the lead. Work out relative dates ("yesterday",
"Friday") with the dates listed above; leave "date" empty for today. Never ask "should
I update it?" and never tell the operator to update it themselves: always
attach the change, because the card IS the confirmation step (they can edit
it, apply it or dismiss it). Keep "reply" to one line saying what will
change, and that nothing is saved until they click Apply on the card. Also put that lead_id in "records". Several RECORDS match:
leave "change" null and ask which one. Nobody matches: leave "change" null,
say they aren't in PACOS yet, and offer to add them (set "lead" if they gave
enough to start one).

WHEN the operator asks you to write, draft, or compose outreach (an email, a
cold email, a DM, a LinkedIn note or message, a cover letter), set "draft":
  {{"asset": "cold_email" | "cold_dm" | "cover_letter",
    "to": {{"full_name": "", "job_title": "", "company_name": "", "city": ""}},
    "request": "<what the operator is asking for, in their words>"}}
Use cold_dm for LinkedIn notes/messages/DMs, cover_letter for cover letters,
cold_email otherwise. Fill "to" from the operator's words, or from the
matching RECORDS entry when they name someone already in PACOS. Keep "reply"
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
    retriever: Callable[[list[dict]], Retrieval] | None = None,
    today: date | None = None,
) -> tuple[str, dict | None, list[str], bool, dict | None, list[dict], dict | None]:
    """Run one chat turn. Returns (reply, lead_proposal|None, warnings,
    llm_used, draft|None, records, change|None). `drafter(asset, to, request)`
    writes a requested draft; without one, drafts are not offered.
    `retriever(messages)` looks up the operator's records for the question;
    `records` are the cards of the leads the reply talks about, and `change`
    is a proposed update to one of them (never applied here)."""
    today = today or date.today()
    found = retriever(messages) if retriever is not None else Retrieval()
    if not client.available:
        # Lookups by name still work offline: the facts are already in words.
        if found.matched:
            cards = [found.cards[i] for i in found.matched]
            return _offline_lookup_reply(cards), None, [], False, None, cards, None
        return _OFFLINE_REPLY, None, [], False, None, [], None

    # Serialise history into one prompt; last message is the live question.
    lines = []
    for m in messages[-16:]:  # keep the window bounded
        who = "Operator" if m.get("role") == "user" else "Assistant"
        lines.append(f"{who}: {m.get('content', '').strip()}")
    convo = "\n\n".join(lines)

    system = _SYSTEM.format(stats=stats, keys=", ".join(PROPOSAL_KEYS),
                            records=found.context or "(nothing matched)",
                            today=_day(today), calendar=_calendar(today))
    user = f"Conversation so far:\n\n{convo[-16000:]}\n\nRespond to the operator's last message."
    # The model sometimes returns the lead with an empty or misnamed "reply";
    # one retry usually fixes it, and a proposal alone still gets a reply.
    for attempt in range(2):
        try:
            raw = client.complete_json(
                system=system, user=user, temperature=0.5, max_tokens=1536)
        except NemotronError as e:
            return f"Nemotron error: {e}", None, [], False, None, [], None
        proposal, warnings = None, []
        lead = raw.get("lead")
        if isinstance(lead, dict) and any(str(v or "").strip() for v in lead.values()):
            proposal, warnings = normalise_proposal(lead)
        reply = _reply_text(raw)
        want = _draft_request(raw)
        change = _change_request(raw, found, today)
        if reply or proposal or want or change:
            break

    draft = None
    if want and drafter is not None:
        asset, to, request = want
        try:
            draft = {"asset": asset, "text": strip_dashes(drafter(asset, to, request))}
        except NemotronError as e:
            return (f"Nemotron error while drafting: {e}", proposal, warnings, True,
                    None, [], change)
        # Fixed line, not the model's: it sometimes writes its own rough
        # draft into "reply", which would show twice and skip the rules.
        reply = f"Here's a draft {_DRAFT_NAMES[asset]}. Review it before sending."

    # The main call often answers an event ("X rejected me") in prose without
    # attaching the change. When the message reports one about exactly one
    # named lead, a narrow second call extracts just the change.
    question = next((m.get("content", "") for m in reversed(messages)
                     if m.get("role") == "user"), "")
    if (change is None and not want and len(found.named) == 1
            and _reports_event(question)):
        # The model sometimes misses the record and offers to add the person
        # as a new lead instead; a proposal for the lead already found is
        # a duplicate, so it gives way to the change.
        named = found.cards[found.named[0]]
        if proposal and _same_person(proposal, named):
            proposal, warnings = None, []
        if not proposal:
            change = _extract_change(client, question, found, today)
    if change:
        # Fixed line, not the model's: it has claimed "Removed X" or "already
        # rejected" when nothing was saved. Only the card can save.
        reply = _change_reply(change, found)
    elif proposal and _claims_saved(reply):
        # Same for lead proposals: "I've added X" when it is only a card.
        reply = _proposal_reply(proposal)

    if found.missing and not (proposal or draft or change):
        # Asked about a full name no lead has (often: deleted). The model has
        # answered these from earlier messages or other people with the same
        # first name, so the answer is fixed. An "add <name>" still proposes.
        reply = (f"I couldn't find anyone called {found.missing} in PACOS. They may never "
                 f"have been added, or the lead was deleted. If you tell me their role and "
                 f"company, I can add them as a lead.")
    if not reply:
        reply = (_proposal_reply(proposal) if proposal
                 else "Sorry, I didn't get a usable answer that time. Please try again.")
    # Only cards for leads that were actually looked up, so a made-up id
    # can't surface; if the model forgot to list the people or company the
    # operator named, show those anyway.
    # The lead a change is for is drawn by the change card itself.
    ids = [i for i in _record_ids(raw) if i in found.cards]
    if not ids and not (proposal or draft or change):
        ids = found.matched
    if found.missing and not (proposal or draft or change):
        ids = []
    skip = change["lead_id"] if change else None
    cards = [found.cards[i] for i in dict.fromkeys(ids) if i != skip]
    # House style everywhere: no em/en dashes in anything the operator reads.
    return strip_dashes(reply), proposal, warnings, True, draft, cards, change


CHANGE_ACTIONS = ("sent", "reply", "status", "note", "delete")
CHANNELS = ("email", "dm", "both")
INTENTS = ("interested", "follow-up", "rejected")
STATUSES = ("pending", "sent", "replied", "interested", "interview", "offer", "rejected")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _change_request(raw: dict, found: Retrieval, today: date) -> dict | None:
    """The model's proposed update, kept only if it is complete and targets a
    lead that was actually looked up this turn. Returns the change with the
    lead's current card attached (the UI draws before -> after from it)."""
    c = raw.get("change")
    if not isinstance(c, dict):
        return None
    lead_id = str(c.get("lead_id", "") or "").strip()
    action = str(c.get("action", "") or "").strip().lower()
    if lead_id not in found.cards or action not in CHANGE_ACTIONS:
        return None
    pick = lambda key, allowed: (v if (v := str(c.get(key, "") or "").strip().lower()) in allowed
                                 else "")
    channel, intent, status = pick("channel", CHANNELS), pick("intent", INTENTS), pick("status", STATUSES)
    note = strip_dashes(str(c.get("note", "") or "").strip())[:300]
    if not _adds_detail(note, found.cards[lead_id]):
        note = ""
    when = str(c.get("date", "") or "").strip()
    when = when if _ISO.match(when) else ""
    # "Status: rejected/interested" is really their answer: record it as a
    # reply so the reply date and intent are kept too.
    if action == "status" and status in ("rejected", "interested"):
        action, intent = "reply", status
    if action == "status" and when and status:
        # A status has no date of its own; an interview/offer date is worth
        # keeping, so it goes into the note.
        dated = f"{status.capitalize()} on {when}"
        note = dated if not note else (note if when in note else f"{dated}, {note}")
    # A sent date or reply date can't be in the future.
    if when > today.isoformat():
        when = ""

    if action == "sent" and not channel:
        channel = "email" if found.cards[lead_id]["email"] else "dm"
    if action == "reply" and not intent:
        if status in ("interested", "rejected"):
            intent = status
        else:
            return None
    if action == "status" and not status:
        return None
    if action == "note" and not note:
        return None
    # Keep only the fields the action uses, so the card shows no stray values.
    return {"lead_id": lead_id, "action": action,
            "channel": channel if action == "sent" else "",
            "intent": intent if action == "reply" else "",
            "status": status if action == "status" else "",
            "date": when if action in ("sent", "reply") else "",
            "note": note if action != "delete" else "",
            "lead": found.cards[lead_id]}


_NOTE_FILLER = set("""
a an the to from at for with on via by of and me i my you he she they them his her
sent send dm dmed email emailed mail mailed message messaged linkedin outreach
reply replied rejected rejection interested interview scheduled offer status
follow up followup lead today yesterday
""".split())


def _adds_detail(note: str, card: dict) -> bool:
    """False for notes that only restate who and what ("DM sent to Abhishek
    Gupta from ABB"); the card already says that."""
    known = _NOTE_FILLER | set(re.findall(r"[a-z0-9]+", f"{card['full_name']} "
                                                       f"{card['company_name']}".lower()))
    return any(t not in known for t in re.findall(r"[a-z0-9]+", note.lower()))


def _same_person(proposal: dict, card: dict) -> bool:
    norm = lambda s: " ".join(re.findall(r"[a-z0-9]+", (s or "").lower()))
    return bool(norm(card["full_name"])) and norm(proposal.get("full_name")) == norm(card["full_name"])


_REPLY_WORDS = {"rejected": "{who} rejected you{when}",
                "interested": "{who} replied{when} and is interested",
                "follow-up": "{who} replied{when} asking you to follow up"}
_CHANNEL_WORDS = {"email": "by email", "dm": "by LinkedIn DM", "both": "by email and DM"}


def _change_reply(change: dict, found: Retrieval) -> str:
    card = found.cards[change["lead_id"]]
    who = card["full_name"] or card["company_name"] or change["lead_id"]
    if card["full_name"] and card["company_name"]:
        who = f"{card['full_name']} at {card['company_name']}"
    when = f" on {change['date']}" if change["date"] else " today"
    what = {
        "sent": f"you sent outreach to {who}{when} {_CHANNEL_WORDS.get(change['channel'], '')}",
        "reply": _REPLY_WORDS.get(change["intent"], "{who} replied{when}").format(
            who=who, when=when),
        "status": f"{who} is now at {change['status']}",
        "note": f"a note on {who}",
    }.get(change["action"])
    if change["action"] == "delete":
        return (f"Ready to delete {who}. Nothing is removed until you confirm "
                f"on the card below.")
    note = (f" (note: {change['note']})"
            if change["note"] and change["action"] != "note" else "")
    return (f"Ready to record that {what.strip()}{note}. Check the card below; "
            f"nothing is saved until you click Apply.")


_EVENT_RE = re.compile(
    r"\b(reject\w*|declin\w*|turn\w*\s+(me\s+)?down|repl(y|ied|ies)|respond\w*|"
    r"got back|heard back|email(ed)?|mail(ed)?|sent|messag\w*|dm(ed|'d|d)?|texted|wrote|ping\w*|"
    r"interview\w*|offer\w*|accept\w*|hired|ghost\w*|delete|remove|note|"
    r"mark\w*|update|change)\b", re.I)


def _reports_event(text: str) -> bool:
    """Says something happened, or asks for an update. Questions ("has X
    replied?") are lookups, not changes."""
    t = text.strip()
    return bool(t) and not t.endswith("?") and bool(_EVENT_RE.search(t))


_EXTRACT_SYSTEM = """You turn one message from a job seeker into a structured
update of their outreach tracker. Today is {today}.
Dates around today (use these, don't count days yourself): {calendar}

The lead it is about:
{record}

Reply with ONLY a JSON object:
  {{"change": null}} when the message does not report something that happened
  with this lead and does not ask to update or delete it; otherwise
  {{"change": {{"lead_id": "{lead_id}",
    "action": "sent" | "reply" | "status" | "note" | "delete",
    "channel": "email" | "dm" | "both" | "",
    "intent": "interested" | "follow-up" | "rejected" | "",
    "status": "pending" | "sent" | "replied" | "interested" | "interview" | "offer" | "rejected" | "",
    "date": "YYYY-MM-DD" | "",
    "note": ""}}}}

Rules: they sent an email/DM/message -> "sent" with channel. The person
answered (including any rejection or "not a fit") -> "reply" with intent.
Interview or offer -> "status", with the interview/offer date in "date"
(it may be upcoming) and any time in "note". Only a detail to remember ->
"note". Explicit
request to delete/remove the lead -> "delete". Relative dates ("yesterday",
"Monday") become YYYY-MM-DD from today; empty means today. "note" is only
for a detail the other fields don't already capture (the role, the interview
date and time with relative days written as dates, who referred them); keep
it under 12 words, never repeat the person's name or the action, and use ""
when there is nothing extra.
"""


def _extract_change(client, question: str, found: Retrieval, today: date) -> dict | None:
    lead_id = found.named[0]

    card = found.cards[lead_id]
    system = _EXTRACT_SYSTEM.format(
        today=_day(today), lead_id=lead_id, calendar=_calendar(today),
        record=record_context(card, card))
    try:
        raw = client.complete_json(system=system, user=f"Message: {question}",
                                   temperature=0.0, max_tokens=400)
    except NemotronError:
        return None
    # It sometimes returns the change object without the wrapper.
    if "change" not in raw and "action" in raw:
        raw = {"change": raw}
    return _change_request(raw, found, today)


def _day(d: date) -> str:
    return f"{d.strftime('%A')} {d.isoformat()}"


def _calendar(today: date) -> str:
    """Last week and next week by weekday name. Models are unreliable at
    counting days, so "Friday" and "last Tuesday" become a lookup."""
    from datetime import timedelta

    past = [today - timedelta(days=n) for n in range(7, 0, -1)]
    ahead = [today + timedelta(days=n) for n in range(1, 8)]
    return ("past: " + ", ".join(_day(d) for d in past)
            + "; upcoming: " + ", ".join(_day(d) for d in ahead)
            + f"; yesterday is {(today - timedelta(days=1)).isoformat()}")


def _record_ids(raw: dict) -> list[str]:
    ids = raw.get("records")
    if not isinstance(ids, list):
        return []
    return [str(i).strip() for i in ids if isinstance(i, (str, int))]


def _offline_lookup_reply(cards: list[dict]) -> str:
    lines = []
    for c in cards:
        who = c["full_name"] or "(no contact)"
        where = " at ".join(p for p in (c["job_title"], c["company_name"]) if p)
        lines.append(f"{who}" + (f", {where}" if where else "") + f": {c['summary']}")
    if len(cards) > 1:
        lines.insert(0, f"I found {len(cards)} matching leads:")
    return strip_dashes("\n".join(lines))


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


_SAVED_CLAIM = re.compile(
    r"\b(i'?ve|i have|i)\s+(just\s+)?(added|saved|created|recorded|updated|deleted|removed)\b"
    r"|\b(has|have)\s+been\s+(added|saved|created|recorded|updated|deleted|removed)\b"
    r"|\bis now (in|on) your\b", re.I)


def _claims_saved(reply: str) -> bool:
    """Says something was written. Nothing in chat writes; only cards do."""
    return bool(_SAVED_CLAIM.search(reply or ""))


def _proposal_reply(proposal: dict) -> str:
    who = proposal.get("full_name") or "this lead"
    where = proposal.get("company_name")
    return (f"I've drafted a lead for {who}" + (f" at {where}" if where else "")
            + ". Review the card below and fill in anything missing before adding it.")
