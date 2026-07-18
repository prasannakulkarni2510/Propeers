"""Parse a pasted job description into proposed lead-sheet fields.

Extraction only — nothing here writes to leads.csv or the tracker. The API
returns the proposal to the operator, who reviews/edits it and then explicitly
adds the lead (human-in-the-loop, same as every other PACOS write).

Uses Nemotron when a key is configured; falls back to regex heuristics offline
so the endpoint always answers.
"""
from __future__ import annotations

import re
from typing import Any

from .leads import VALID_PERSONAS
from .llm import NemotronClient, NemotronError

# The keys a proposal may carry — mirrors AddLeadRequest / CSV_INPUT_COLUMNS.
PROPOSAL_KEYS = [
    "full_name", "job_title", "company_name", "city", "linkedin_url",
    "persona_tag", "email", "company_size", "industry", "company_website",
    "funding_stage",
]

_SYSTEM = """You extract job-lead data from a pasted job description (JD).
Reply with ONLY a JSON object with these string keys (empty string when the JD
does not state it — never invent values):

- full_name: the CONTACT PERSON named in the JD (recruiter/hiring manager/founder), NOT the candidate role
- job_title: the contact person's title if named; otherwise the role being hired for
- company_name: the hiring company
- city: primary location of the role
- linkedin_url: any LinkedIn profile/company URL in the JD
- persona_tag: one of hr|engineer|manager|cto|ceo for the contact person (empty if no contact named)
- email: any contact email in the JD
- company_size: employee count if stated (digits only, e.g. "40")
- industry: the company's industry if stated
- company_website: the company's website URL if stated
- funding_stage: e.g. "seed", "series a", "public" if stated"""

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/\S+", re.I)
_URL_RE = re.compile(r"https?://(?!(?:www\.)?linkedin\.com)[\w.-]+\.[a-z]{2,}\S*", re.I)
_COMPANY_RE = re.compile(
    r"(?:\b[Aa]t|\b[Jj]oin|\b[Aa]bout)\s+([A-Z][\w&.-]*(?:\s+[A-Z][\w&.-]*){0,3})"
)
_LOCATION_RE = re.compile(r"location\s*[:\-]\s*([^\n|]+)", re.I)


def _fallback_parse(text: str) -> dict[str, str]:
    """Best-effort regex extraction when Nemotron is unavailable."""
    fields = {k: "" for k in PROPOSAL_KEYS}
    if m := _EMAIL_RE.search(text):
        fields["email"] = m.group(0)
    if m := _LINKEDIN_RE.search(text):
        fields["linkedin_url"] = m.group(0).rstrip(".,)")
    if m := _URL_RE.search(text):
        fields["company_website"] = m.group(0).rstrip(".,)")
    if m := _COMPANY_RE.search(text):
        fields["company_name"] = m.group(1).strip()
    if m := _LOCATION_RE.search(text):
        fields["city"] = m.group(1).strip()
    # First non-empty line is usually the role title.
    for line in text.splitlines():
        line = line.strip()
        if line:
            fields["job_title"] = line[:80]
            break
    return fields


def normalise_proposal(raw: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Keep only known keys, coerce to stripped strings, validate persona.

    Shared by the JD parser and the chat assistant — any model-proposed lead
    goes through here before it reaches the operator for review.
    """
    warnings: list[str] = []
    fields = {k: str(raw.get(k, "") or "").strip() for k in PROPOSAL_KEYS}
    persona = fields["persona_tag"].lower()
    if persona and persona not in VALID_PERSONAS:
        warnings.append(f"persona_tag '{persona}' not in {sorted(VALID_PERSONAS)}; cleared")
        persona = ""
    fields["persona_tag"] = persona
    for key in ("full_name", "company_name", "persona_tag"):
        if not fields[key]:
            warnings.append(f"'{key}' not found in JD; fill it in before adding")
    return fields, warnings


def parse_jd(client: NemotronClient, text: str) -> tuple[dict[str, str], list[str], bool]:
    """Extract proposed lead fields from JD text.

    Returns (fields, warnings, llm_used).
    """
    llm_used = False
    if client.available:
        try:
            raw = client.complete_json(
                system=_SYSTEM,
                user=f"Job description:\n\n{text[:12000]}",
                temperature=0.2,
                max_tokens=1024,
            )
            llm_used = True
        except NemotronError as e:
            raw = _fallback_parse(text)
            fields, warnings = normalise_proposal(raw)
            warnings.insert(0, f"Nemotron failed ({e}); used offline fallback")
            return fields, warnings, False
    else:
        raw = _fallback_parse(text)

    fields, warnings = normalise_proposal(raw)
    if not llm_used:
        warnings.insert(0, "NVIDIA_API_KEY not set; used offline regex fallback")
    return fields, warnings, llm_used
