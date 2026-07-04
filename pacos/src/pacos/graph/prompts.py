"""Prompts + templates for the personalization and asset agents."""
from __future__ import annotations

import json

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
                   "5–7 lines. Primary outreach when an email is known. First line "
                   "must be 'Subject: ...'. Sign off with the candidate's name."),
    "cold_dm": ("cold_dm.txt",
                "3–4 lines. A LinkedIn DM (no subject line). Warm, specific, easy to reply to."),
    "cover_letter": ("cover_letter.txt",
                     "150–200 words. For formal applications. Reference the company, "
                     "role, domain, and any hiring signal."),
    "cv_notes": ("cv_notes.txt",
                 "A bulleted list (5–8 bullets) of how to tweak the CV for THIS role. "
                 "Actionable, specific, not generic."),
}

SYSTEM_PERSONALIZATION = (
    "You are the Personalization agent for PACOS. Given a lead and the candidate, "
    "you find the single most specific, genuine hook connecting them, plus a short "
    "read on the right tone. Return ONE valid JSON object and nothing else."
)

SYSTEM_ASSET = (
    "You are an expert career-outreach copywriter for PACOS. You write personalised, "
    "human-sounding outreach that never reads like a mass template. Return only the "
    "requested text — no preamble, no markdown fences, no commentary."
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
        f"SHARED HOOK (open on this — keep all assets consistent): {hook}\n\n"
        f"LEAD:\n{json.dumps(facts, indent=2)}\n\n"
        f"CANDIDATE (sender):\n{json.dumps(candidate, indent=2)}\n\n"
        f"CANDIDATE CV CONTEXT:\n{base_cv or '(none)'}\n\n"
        "Address the person by first name. Be specific to their company and role. "
        "Never invent candidate facts beyond the CV context. Output only the asset text."
    )


# ── dry-run templates (no API call) ─────────────────────────────────────────
def tmpl_hook(lead: dict) -> str:
    return (f"I've followed {lead.get('company_name')}'s work in "
            f"{lead.get('industry') or 'AI/ML'} and your {lead.get('job_title')} team.")


def tmpl_asset(asset_key: str, lead: dict, candidate: dict, hook: str) -> str:
    who = candidate.get("name") or "The candidate"
    headline = candidate.get("headline") or "AI engineer"
    first = lead.get("first_name", "there")
    company = lead.get("company_name", "your company")
    role = lead.get("job_title", "the role")
    tag = lead.get("domain_tag", "")
    if asset_key == "cold_email":
        return (f"Subject: {role} at {company} — quick note\n\n"
                f"Hi {first},\n\n{hook} {who} here — an {headline} based in "
                f"{lead.get('city','')}.\n[DRY RUN placeholder — Nemotron writes real "
                f"copy when NVIDIA_API_KEY is set.]\n\nOpen to a short chat?\n\n"
                f"Best,\n{who}\n{candidate.get('email','')}")
    if asset_key == "cold_dm":
        return (f"Hi {first} — {hook} I'm an {headline} keen on {company}. "
                f"Open to connecting? [DRY RUN placeholder.]")
    if asset_key == "cover_letter":
        return (f"Dear {first},\n\nI'm writing about the {role} opportunity at "
                f"{company}. {hook}\n\n[DRY RUN placeholder — a 150–200 word, "
                f"{tag}-toned cover letter is generated by Nemotron when a key is set.]"
                f"\n\nSincerely,\n{who}")
    return (f"# CV tweaks for {role} @ {company} ({tag})\n"
            f"- Lead with experience relevant to {lead.get('industry') or 'this domain'}.\n"
            f"- Mirror keywords from the '{role}' title.\n"
            "- [DRY RUN placeholder — Nemotron writes specific bullets with a key set.]")
