"""Prompts + templates for the personalization and asset agents."""
from __future__ import annotations

import json
import re

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
    return (
        f"Write the {asset_key} asset.\n\nSPEC: {spec}\n\n"
        f"TONE: {tone_for(lead.get('domain_tag',''))}\n"
        f"DOMAIN READ: {domain_read}\n"
        f"SHARED HOOK (open on this, keep all assets consistent): {hook}\n\n"
        f"LEAD:\n{json.dumps(facts, indent=2)}\n\n"
        f"CANDIDATE (sender):\n{json.dumps(candidate, indent=2)}\n\n"
        f"CANDIDATE CV CONTEXT:\n{base_cv or '(none)'}\n\n"
        "Write it now, in first person, as me. Address the person by their first name. "
        "Ground every claim in the LEAD facts and CV context above; if a field is empty, "
        "work around it instead of inventing anything. Keep it warm and specific, and "
        "stay inside the SPEC's word count. Use no em dashes. Read it back once and cut "
        "any sentence that could be sent to a hundred other people unchanged, plus any "
        "sentence you cannot point to a LEAD fact or CV line for. Output "
        "only the asset text."
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
