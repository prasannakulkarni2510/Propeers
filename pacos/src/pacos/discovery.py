"""Recruiter discovery: boolean search queries for the people behind a job.

Given the job details PACOS already knows (company, role, location, keywords),
build optimised boolean queries per target persona group — hiring managers,
engineering managers, team leads, directors, recruiters, TA, HRBPs — and the
LinkedIn people-search and Google X-Ray URLs that run them.

Deliberately deterministic, not model-generated: a boolean query is a small
formal language, so a template beats an LLM on correctness and works offline.
Read-only like every extractor — it proposes searches, the operator runs them
in the browser and decides who becomes a lead (human-in-the-loop; no scraping,
which LinkedIn's ToS prohibits).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote

# Persona groups to hunt for, in outreach-priority order. Each is a boolean
# OR-clause of current-title phrases; persona_tag is the lead-sheet tag the
# found person would carry.
TARGET_GROUPS: list[tuple[str, str, list[str]]] = [
    ("Hiring Managers", "manager",
     ["Hiring Manager", "Head of Engineering", "VP Engineering"]),
    ("Engineering Managers & Team Leads", "manager",
     ["Engineering Manager", "Team Lead", "Tech Lead", "Engineering Lead"]),
    ("Directors", "manager",
     ["Director of Engineering", "Engineering Director", "Senior Director"]),
    ("Technical Recruiters", "hr",
     ["Technical Recruiter", "Tech Recruiter", "IT Recruiter"]),
    ("Talent Acquisition", "hr",
     ["Talent Acquisition", "Talent Partner", "Recruitment Specialist"]),
    ("HR Business Partners", "hr",
     ["HR Business Partner", "HRBP", "People Partner"]),
]

_WORD_RE = re.compile(r"[A-Za-z0-9+#.]+")


@dataclass
class SearchVariant:
    """One runnable people search: a boolean query plus the URLs that run it."""
    group: str
    persona_tag: str
    query: str          # boolean string, paste-able into LinkedIn search
    linkedin_url: str   # LinkedIn people search pre-filled with the query
    xray_url: str       # Google X-Ray over linkedin.com/in profiles
    keywords: list[str] = field(default_factory=list)


def _phrase(term: str) -> str:
    """Quote a term when it has spaces so boolean engines treat it as a phrase."""
    term = term.strip()
    return f'"{term}"' if " " in term else term


def _or_clause(terms: list[str]) -> str:
    return "(" + " OR ".join(_phrase(t) for t in terms) + ")"


def _role_keywords(role: str) -> list[str]:
    """Distil a role string into the discriminating keywords for title matching.

    "Senior Machine Learning Engineer (Remote)" -> ["Machine", "Learning", ...]
    keeps tech-ish tokens, drops seniority/noise words.
    """
    noise = {"senior", "sr", "junior", "jr", "lead", "staff", "principal",
             "i", "ii", "iii", "remote", "hybrid", "onsite", "the", "a", "an",
             "of", "and", "for", "engineer", "developer", "role", "position"}
    words = [w for w in _WORD_RE.findall(role) if w.lower() not in noise]
    return words[:4]


def _linkedin_url(query: str) -> str:
    return ("https://www.linkedin.com/search/results/people/?keywords="
            + quote(query, safe=""))


def _xray_url(query: str) -> str:
    return ("https://www.google.com/search?q="
            + quote(f'site:linkedin.com/in {query}', safe=""))


def build_searches(
    company: str,
    role: str = "",
    location: str = "",
    extra_keywords: list[str] | None = None,
) -> list[SearchVariant]:
    """Build one search variant per target group, plus a broad catch-all.

    `company` is required — it is the anchor of every query. `role` narrows
    the manager-side groups (a recruiter's title rarely echoes the role, so
    recruiter groups skip it). `location` and `extra_keywords` (tech stack)
    are appended when given.
    """
    company = company.strip()
    if not company:
        raise ValueError("company is required to build discovery searches")
    location = location.strip()
    extras = [k.strip() for k in (extra_keywords or []) if k.strip()]
    role_kw = _role_keywords(role) if role.strip() else []

    variants: list[SearchVariant] = []
    for group, persona, titles in TARGET_GROUPS:
        parts = [_phrase(company), _or_clause(titles)]
        keywords = [company] + titles
        # Titles like "Engineering Manager, Payments" echo the team/domain —
        # only manager-side groups benefit from role keywords.
        if role_kw and persona == "manager":
            parts.append(_or_clause(role_kw))
            keywords += role_kw
        if extras and persona == "manager":
            parts.append(_or_clause(extras))
            keywords += extras
        if location:
            parts.append(_phrase(location))
            keywords.append(location)
        query = " AND ".join(parts)
        variants.append(SearchVariant(
            group=group, persona_tag=persona, query=query,
            linkedin_url=_linkedin_url(query), xray_url=_xray_url(query),
            keywords=keywords,
        ))

    # Broad catch-all: everyone likely involved in hiring at the company.
    all_titles = ["Hiring Manager", "Engineering Manager", "Director",
                  "Recruiter", "Talent Acquisition", "HR Business Partner"]
    broad_parts = [_phrase(company), _or_clause(all_titles)]
    if location:
        broad_parts.append(_phrase(location))
    broad = " AND ".join(broad_parts)
    variants.append(SearchVariant(
        group="All hiring roles (broad)", persona_tag="",
        query=broad, linkedin_url=_linkedin_url(broad),
        xray_url=_xray_url(broad),
        keywords=[company] + all_titles + ([location] if location else []),
    ))
    return variants
