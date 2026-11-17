"""Prompts + templates for the personalization and asset agents."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# House style: no em/en dashes in generated copy (the biggest AI tell). The model
# is told this in SYSTEM_ASSET, but it still slips in "do X — because Y" phrasing,
# so we also normalise deterministically after generation.
_EM_DASH = re.compile(r"\s*—\s*")
_EN_RANGE = re.compile(r"(?<=\d)\s*–\s*(?=\d)")
_EN_DASH = re.compile(r"\s*–\s*")


def strip_dashes(text: str) -> str:
    """Turn em dashes into commas and en dashes into 'to' (ranges) or commas.
    Regular hyphens (human-in-the-loop, sub-minute) are left untouched."""
    text = _EM_DASH.sub(", ", text)
    text = _EN_RANGE.sub(" to ", text)
    text = _EN_DASH.sub(", ", text)
    return text

# Domain -> tone guidance (design doc §6).
DOMAIN_TONE = {
    "startup": "Casual, founder-direct, energetic. Short sentences. Show hustle and ownership.",
    "scaleup": "Growth-focused. Lead with impact and metrics. Confident and concrete.",
    "enterprise": "Formal, process-aware, structured. Emphasise reliability and collaboration.",
    "product": "Product thinking first. Talk in users, adoption, and metrics.",
    "services": "Delivery-focused and client-facing. Emphasise reliability and shipping on time.",
    "research": "Technical depth and rigor. Reference methods, evaluation, publications.",
}

# asset key -> (filename, length/purpose guidance) (design doc §5).
ASSET_SPECS = {
    "cold_email": ("cold_email.txt",
        "A cold outreach email in my own voice, 90 to 130 words in 3 or 4 short "
        "paragraphs. Line 1 is 'Subject: ' then a specific subject under 8 words (no "
        "clickbait, no emojis). Open on something concretely true about them or their "
        "company, not about me. Then one proof point copied from my CV context, using "
        "a number only if that exact number appears there; with no usable proof point, "
        "make the ask plainly instead. If I name a project like PACOS, "
        "say in one line what it does. Close with a single easy ask (a short call, or a "
        "yes/no question). Sign off with my first name on its own line."),
    "cold_dm": ("cold_dm.txt",
        "A LinkedIn DM in my own voice: 35 to 60 words, 2 or 3 sentences, no subject "
        "line and no signature. It reads like I'm messaging one person I respect, not "
        "pitching. Lead with the specific hook, give one concrete reason I'd be worth a "
        "reply that comes straight from my CV context (no invented experience), and end "
        "with an easy question they can answer in one line. No links."),
    "cover_letter": ("cover_letter.txt",
        "A cover letter in my own voice, 150 to 200 words, 3 paragraphs, addressed to "
        "the person by name. Para 1: the role and why this company specifically (name a "
        "real detail: their domain, product, funding stage, or a hiring signal). Para 2: "
        "my two strongest, most relevant proof points, concrete and grounded in my CV; "
        "if I mention a project like PACOS, explain in a line what I built and why it "
        "matters for this role. Para 3: a warm, confident close and a clear next step."),
    "cv_notes": ("cv_notes.txt",
        "5 to 8 first-person notes to myself on how to tailor my CV for this specific "
        "role. Each note is a concrete edit I can make today: what to move up, what to "
        "rephrase, which keyword from the job title or industry to surface. Every note "
        "must name the actual CV line or item it edits; never tell me to add a metric, "
        "project, or experience that is not already in my CV context. Write them as "
        "'I'll ...' or 'Move my ...'. No generic advice like 'use action verbs'."),
}

# Writing playbook (skills/job_application_playbook): hiring-manager guidance fed
# to each asset agent. README holds the shared rules; each asset gets its own
# guide. Style guidance only, never facts about me (the CV stays the only source).
_PLAYBOOK_DIR = Path(__file__).resolve().parents[1] / "skills" / "job_application_playbook"
PLAYBOOK_FILES = {
    "cold_email": ["cold-email.md"],
    "cold_dm": ["cold-dm.md"],
    "cover_letter": ["cover-letter.md"],
    "cv_notes": ["cv-tips.md", "resume-tips.md"],
}
# README sections that are not writing rules: the file index, and a sample
# candidate profile the model could mistake for facts about me.
_README_SKIP = ("## Files", "## Candidate profile")


def _drop_sections(md: str, headings: tuple[str, ...]) -> str:
    parts = re.split(r"(?m)^(?=## )", md)
    return "".join(p for p in parts if not p.startswith(headings)).strip()


@lru_cache(maxsize=None)
def playbook_for(asset_key: str) -> str:
    """Shared playbook rules plus the guide for this asset; '' if files are missing."""
    try:
        shared = _drop_sections(
            (_PLAYBOOK_DIR / "README.md").read_text(encoding="utf-8"), _README_SKIP)
        guides = [(_PLAYBOOK_DIR / f).read_text(encoding="utf-8").strip()
                  for f in PLAYBOOK_FILES.get(asset_key, [])]
    except OSError:
        return ""
    return "\n\n".join([shared, *guides])


SYSTEM_PERSONALIZATION = (
    "You are the Personalization agent for PACOS. Given a lead and the candidate, "
    "you find the single most specific, genuine hook connecting them, plus a short "
    "read on the right tone. Return ONE valid JSON object and nothing else."
)

# The banned-phrase list is the biggest lever on quality: these are the exact
# tells that make outreach read like a mass template or AI slop.
_BANNED = (
    # cold-outreach clichés
    "I hope this email finds you well", "I am reaching out", "I wanted to reach out",
    "I came across your profile", "exciting opportunity", "I'd love to", "I would love to",
    "perfect fit", "the perfect candidate", "passionate about", "team player",
    "hit the ground running", "wear many hats", "think outside the box",
    "in today's fast-paced world", "results-driven", "I am confident that",
    "please don't hesitate", "circle back", "touch base",
    # AI-writing tells
    "leverage", "synergy", "delve", "tapestry", "testament", "underscore", "showcase",
    "vibrant", "intricate", "pivotal", "foster", "garner", "seamless", "robust",
    "cutting-edge", "game-changer", "unlock", "elevate", "spearhead", "navigate the",
)

SYSTEM_ASSET = (
    "You write job-search outreach in the sender's own voice. You ARE the sender, "
    "writing as 'I' about my own work. Warm, genuine, and specific, the way a real "
    "person writes to someone they respect, never a mass template and never AI "
    "boilerplate.\n\n"
    "Voice:\n"
    "- First person throughout ('I', 'my'). Never describe the sender in the third "
    "person or by name as if reporting on them.\n"
    "- Warm and human. Write the way I'd talk to a smart colleague, not the way a "
    "brochure sells a product.\n"
    "- Specific beats flattering. Name a real detail about the person or their company. "
    "If I have nothing specific, be plainly direct instead of vague.\n"
    "- Lead with them, then connect it to my work. One clear point, made well.\n"
    "- Short, plain sentences with contractions. Cut any word that isn't pulling weight.\n\n"
    "Grounding (the most important rule):\n"
    "- The CANDIDATE CV CONTEXT is the ONLY source of truth about me. Every skill, "
    "project, employer, metric, and outcome you write must appear there. If it is "
    "not in the CV context, it does not exist.\n"
    "- No number unless that exact number is in the CV context. Never estimate, "
    "round, or 'improve' a figure. A claim without a number beats a fake number.\n"
    "- The LEAD facts are the only source of truth about the person and company. "
    "Do not invent funding news, launches, posts, or anything else about them.\n"
    "- When the CV context is sparse or missing, write a shorter, plainer message "
    "that leans on genuine interest instead of proof points. Omitting always "
    "beats inventing.\n"
    "- When I mention one of my projects (for example PACOS), say in a line what it "
    "actually does so the reader gets it, and keep it true to the CV.\n\n"
    "Never do:\n"
    "- No em dashes or en dashes anywhere. Use a comma, a period, a colon, or "
    "parentheses instead.\n"
    "- No emojis, hashtags, markdown, or exclamation-mark spam.\n"
    "- No groups of three for their own sake, no signposting ('let me explain'), no "
    "one-liners engineered to sound deep.\n"
    "- Never use these phrases or close variants: " + "; ".join(_BANNED) + ".\n\n"
    "Return only the finished text: no preamble, no notes, no 'Here is...', no fences."
)


# ── who is writing to whom ──────────────────────────────────────────────────
# With no contact name on a lead the model has greeted the reader with the
# SENDER's name ("Hi Prasanna, I noticed your work on PACOS"), invented one,
# or left "[First Name]". The prompt says who is who; the greeting is then
# checked in code, because the prompt alone does not hold.
_GREETING = re.compile(
    r"^(?P<hi>(?i:hi|hello|hey|dear))[ \t]+"
    r"(?P<name>\[[^\]\n]*\]|[A-Z][\w'’.-]*(?:[ \t]+[A-Z][\w'’.-]*){0,2})"
    r"(?=[,.:!\s]|$)", re.M)
_PLACEHOLDER = re.compile(r"\[[A-Za-z][^\]\n]{0,40}\]")
_GREETABLE = {"there", "team", "all", "everyone", "folks", "hiring", "recruiting", "talent"}


def _first(name: str) -> str:
    parts = (name or "").split()
    return parts[0] if parts else ""


def who_is_who(recipient_first: str, company: str, candidate: dict, letter: bool = False) -> str:
    """The lines that tell the writer who it is, who reads it, and how to greet."""
    me = _first(candidate.get("name", ""))
    mine = (f"I am {me}, the sender. " if me else "I am the sender. ") + (
        "The reader is someone else: never greet them with my name, and never "
        "credit them with my work. Everything in the CV context (my projects, such "
        "as PACOS, my skills, my results) is mine, so it is 'my' and 'I built', "
        "never 'your' or 'you built'. ")
    if recipient_first:
        return mine + f"Greet the reader as {recipient_first}."
    plain = "'Dear Hiring Team,'" if letter else (
        f"'Hi,' or 'Hi {company} team,'" if company else "'Hi,'")
    return mine + (f"I do not know the reader's name: greet with a plain {plain} "
                   "and nothing else. Never make up a name and never leave a "
                   "[bracketed] placeholder. Say nothing about the reader's own "
                   "work, since I know nothing about it.")


def fix_greeting(text: str, asset_key: str, recipient_first: str, sender_first: str,
                 company: str = "") -> tuple[str, bool]:
    """(text with a truthful greeting, whether the draft should be rewritten).
    A known reader is greeted by their first name; an unknown one by no name
    at all. Rewrite when the sender was greeted (the body then usually treats
    them as the reader too) or a [placeholder] is left anywhere."""
    if asset_key == "cv_notes":
        return text, False
    confused = False
    head, tail = text[:240], text[240:]
    m = _GREETING.search(head)
    if m:
        name = m.group("name")
        word = _first(name).strip(".,").lower()
        to_sender = bool(sender_first) and word == sender_first.lower() \
            and word != recipient_first.lower()
        bracket = name.startswith("[")
        company_words = {w.lower() for w in company.split()}
        new = None
        if recipient_first:
            if to_sender or bracket:
                new = f"{m.group('hi')} {recipient_first}"
        elif to_sender or bracket or not (
                word in _GREETABLE or word in company_words
                or head[m.end():].lower().startswith(" team")):
            new = m.group("hi")
            if not head[m.end():m.end() + 1] == ",":
                new += ","
        confused = to_sender
        if new is not None:
            head = head[:m.start()] + new + head[m.end():]
    text = head + tail
    return text, confused or bool(_PLACEHOLDER.search(text))


REWRITE_NOTE = (
    "\n\nYour last attempt addressed the wrong person or left a placeholder. I am "
    "the sender and the reader is someone else; everything in the CV context is "
    "my own work. Write it again from scratch, following the greeting rule above.")


def tone_for(domain_tag: str) -> str:
    return DOMAIN_TONE.get(domain_tag, DOMAIN_TONE["scaleup"])


def build_personalization_user(lead: dict, candidate: dict, base_cv: str) -> str:
    facts = {k: lead.get(k, "") for k in (
        "full_name", "first_name", "job_title", "company_name", "city",
        "persona_tag", "domain_tag", "industry", "company_size",
        "company_website", "funding_stage")}
    schema = {
        "hook": "one specific sentence tying the candidate to this person/company",
        "domain_read": "one sentence on the tone/angle to use for this company",
    }
    return (
        f"TONE for {lead.get('domain_tag')}: {tone_for(lead.get('domain_tag',''))}\n\n"
        f"LEAD:\n{json.dumps(facts, indent=2)}\n\n"
        f"CANDIDATE:\n{json.dumps(candidate, indent=2)}\n\n"
        f"CANDIDATE CV CONTEXT:\n{base_cv or '(none)'}\n\n"
        f"Return ONLY this JSON:\n{json.dumps(schema, indent=2)}"
    )


def build_asset_user(asset_key: str, lead: dict, candidate: dict, base_cv: str,
                     hook: str, domain_read: str) -> str:
    _, spec = ASSET_SPECS[asset_key]
    facts = {k: lead.get(k, "") for k in (
        "first_name", "full_name", "job_title", "company_name", "city",
        "persona_tag", "domain_tag", "industry", "company_website")}
    # An empty name is left out, not shown as "": the model fills blanks.
    facts = {k: v for k, v in facts.items() if v or k not in ("first_name", "full_name")}
    who = who_is_who(_first(lead.get("first_name") or lead.get("full_name") or ""),
                     lead.get("company_name", ""), candidate, letter=asset_key == "cover_letter")
    playbook = playbook_for(asset_key)
    playbook_block = (
        "WRITING PLAYBOOK (how a hiring manager reads this; follow its structure, "
        "adapt-by-role tables, and checklists):\n"
        "- It is guidance on HOW to write, never facts about me or the lead. Its "
        "examples and sample backgrounds are not my experience.\n"
        "- Its tables name things a role may value (testing, data quality, "
        "observability, evaluation, collaboration...). Use them only to pick WHICH of "
        "my CV facts to lead with. Never claim one unless the CV context shows it.\n"
        "- Never imply I follow, read, or know the person or company beyond the LEAD "
        "facts ('I've been following...', 'I read your...').\n"
        "- Its templates are patterns: never output a [bracketed] placeholder. Fill "
        "each slot from the LEAD facts or CV context, or drop that sentence.\n"
        "- Where it conflicts with the SPEC (length, format, sign-off) or the rules "
        "in your instructions, the SPEC and your instructions win.\n\n"
        f"<playbook>\n{playbook}\n</playbook>\n\n"
    ) if playbook else ""
    return (
        f"Write the {asset_key} asset.\n\n{playbook_block}SPEC: {spec}\n\n"
        f"TONE: {tone_for(lead.get('domain_tag',''))}\n"
        f"DOMAIN READ: {domain_read}\n"
        f"SHARED HOOK (the angle to open on, kept consistent across assets. It may "
        f"describe me in the third person: say it as 'I' and 'my'): {hook}\n\n"
        f"LEAD:\n{json.dumps(facts, indent=2)}\n\n"
        f"CANDIDATE (sender):\n{json.dumps(candidate, indent=2)}\n\n"
        f"CANDIDATE CV CONTEXT:\n{base_cv or '(none)'}\n\n"
        f"WHO IS WHO: {who}\n\n"
        "Write it now, in first person, as me. "
        "Ground every claim in the LEAD facts and CV context above; if a field is empty, "
        "work around it instead of inventing anything. Keep it warm and specific, and "
        "stay inside the SPEC's word count. Use no em dashes. Read it back once and cut "
        "any sentence that could be sent to a hundred other people unchanged, plus any "
        "sentence you cannot point to a LEAD fact or CV line for. Output "
        "only the asset text."
    )


def build_chat_draft_user(asset_key: str, target: dict, request: str,
                          candidate: dict, base_cv: str) -> str:
    """A draft the operator asked for in chat ("write an email to X asking
    for Y"): same spec, playbook and grounding as the pipeline assets, but the
    target comes from the conversation instead of the lead sheet."""
    _, spec = ASSET_SPECS[asset_key]
    facts = {k: str(target.get(k, "") or "") for k in (
        "full_name", "job_title", "company_name", "city")}
    who = who_is_who(_first(facts["full_name"]), facts["company_name"], candidate,
                     letter=asset_key == "cover_letter")
    playbook = playbook_for(asset_key)
    playbook_block = (
        "WRITING PLAYBOOK (guidance on HOW to write, never facts about me or the "
        "recipient; its templates are patterns, so never output a [bracketed] "
        "placeholder; where it conflicts with the SPEC, the SPEC wins):\n"
        f"<playbook>\n{playbook}\n</playbook>\n\n"
    ) if playbook else ""
    return (
        f"Write the {asset_key} asset.\n\n{playbook_block}SPEC: {spec}\n\n"
        f"WHAT I'M ASKING FOR (my words; make this the ask): {request or '(not stated)'}\n\n"
        f"RECIPIENT (only what I told you; empty means unknown):\n{json.dumps(facts, indent=2)}\n\n"
        f"CANDIDATE (sender):\n{json.dumps(candidate, indent=2)}\n\n"
        f"CANDIDATE CV CONTEXT:\n{base_cv or '(none)'}\n\n"
        f"WHO IS WHO: {who}\n\n"
        "Write it now, in first person, as me. Claim nothing about me that is not in the CV context "
        "and nothing about the recipient or company beyond the facts above (do not "
        "say they are hiring, have an opening, or work on anything unless I said "
        "so). Say what I asked to say and nothing more: the SPEC sets the length "
        "and tone, not the purpose. If I'm thanking, declining, or replying, the "
        "message only does that; never add a request, a condition, a delay or a "
        "plan I didn't mention. Keep "
        "inside the SPEC's word count. Use no em dashes. Output only the text."
    )


# ── dry-run templates (no API call) ─────────────────────────────────────────
def tmpl_hook(lead: dict) -> str:
    return (f"I've been following {lead.get('company_name')}'s work in "
            f"{lead.get('industry') or 'AI/ML'} and your {lead.get('job_title')} team.")


def tmpl_asset(asset_key: str, lead: dict, candidate: dict, hook: str) -> str:
    who = candidate.get("name") or "the candidate"
    headline = candidate.get("headline") or "AI engineer"
    first = lead.get("first_name", "there")
    company = lead.get("company_name", "your company")
    role = lead.get("job_title", "the role")
    tag = lead.get("domain_tag", "")
    if asset_key == "cold_email":
        return (f"Subject: quick note on the {role} role at {company}\n\n"
                f"Hi {first},\n\n{hook} I'm {who}, an {headline} based in "
                f"{lead.get('city','')}.\n(Dry run placeholder. Nemotron writes the real "
                f"copy once NVIDIA_API_KEY is set.)\n\nWould a short chat work?\n\n"
                f"Best,\n{who}\n{candidate.get('email','')}")
    if asset_key == "cold_dm":
        return (f"Hi {first}, {hook} I'm an {headline} keen on {company}. "
                f"Open to connecting? (Dry run placeholder.)")
    if asset_key == "cover_letter":
        return (f"Dear {first},\n\nI'm writing about the {role} role at "
                f"{company}. {hook}\n\n(Dry run placeholder. Nemotron writes a warm, "
                f"{tag}-toned 150 to 200 word letter once a key is set.)"
                f"\n\nSincerely,\n{who}")
    return (f"# How I'll tailor my CV for {role} at {company} ({tag})\n"
            f"- I'll lead with the experience closest to {lead.get('industry') or 'this domain'}.\n"
            f"- I'll mirror the keywords from the '{role}' title.\n"
            "- (Dry run placeholder. Nemotron writes specific notes once a key is set.)")


def write_asset(client, asset_key: str, user: str, *, recipient_first: str,
                candidate: dict, company: str = "", temperature: float = 0.3) -> str:
    """Write one asset and make sure it is addressed to the reader, not to the
    sender: the greeting is corrected in code, and a draft that mixed the two
    people up (or left a placeholder) is written once more."""
    me = _first(candidate.get("name", ""))
    text = ""
    for attempt in range(2):
        raw = client.complete_text(system=SYSTEM_ASSET,
                                   user=user + (REWRITE_NOTE if attempt else ""),
                                   temperature=temperature, max_tokens=1600)
        text, again = fix_greeting(strip_dashes(raw.strip()), asset_key,
                                   recipient_first, me, company)
        if not again:
            break
    return _PLACEHOLDER.sub("", text) if asset_key != "cv_notes" else text
