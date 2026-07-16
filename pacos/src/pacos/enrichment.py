"""Lead enrichment: turn a Google X-Ray results page into proposed leads.

This is the deterministic second half of Discovery. `discovery.py` builds the
Boolean queries and the Google X-Ray URL; this module runs *after* that search
exists and does the mechanical part the operator used to do by hand:

    Google X-Ray results  ->  extract linkedin.com/in profiles
                          ->  parse name / title / company
                          ->  predict a likely work email + confidence
                          ->  propose Lead records

Deliberately NOT an LLM agent and NOT a paid people-search API: the only data
source is the operator's own Google X-Ray query (site:linkedin.com/in ...).
Parsing and email prediction are pure functions so they unit-test offline; the
one impure edge is `fetch_xray`, and even that degrades to an operator paste
when Google answers with a consent/CAPTCHA wall instead of results.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from urllib.parse import unquote, urlparse

# A linkedin.com/in/ profile URL, tolerant of country subdomains (in./uk.) and
# of Google's /url?q=<real-url>&… result wrapping (we search the raw href).
_PROFILE_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[^\s\"'&<>?#]+", re.I
)
# Trailing suffix Google appends to a profile result title.
_LINKEDIN_SUFFIX_RE = re.compile(r"\s*[|\-–—]\s*LinkedIn\s*$", re.I)
_WORD_RE = re.compile(r"[A-Za-z]+")

# Legal-entity / noise tokens dropped when guessing a company email domain.
_COMPANY_NOISE = {
    "inc", "llc", "ltd", "limited", "pvt", "private", "corp", "corporation",
    "co", "company", "gmbh", "plc", "technologies", "technology", "labs",
    "software", "solutions", "systems", "global", "group", "the",
}


@dataclass
class ProfileHit:
    """One person parsed from a search result, before any lead is written."""
    linkedin_url: str
    full_name: str = ""
    job_title: str = ""
    company_name: str = ""
    location: str = ""


@dataclass
class EmailPrediction:
    """A predicted work email — never a verified one."""
    email: str = ""
    confidence: str = "low"          # high | medium | low
    status: str = "unknown"          # predicted | unknown  (never 'verified')
    candidates: list[str] = field(default_factory=list)


# ── profile parsing ─────────────────────────────────────────────────────────
def _canonical_profile_url(url: str) -> str:
    """Normalise a profile URL for dedup: drop query/fragment and trailing slash,
    lower-case the host+path so the same person collapses to one key."""
    url = unescape(unquote(url)).split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return url.lower()


def _extract_profile_url(href: str) -> str | None:
    """Pull a linkedin.com/in URL out of an href, unwrapping Google's
    /url?q=<real>&sa=… redirect form on the way."""
    m = _PROFILE_RE.search(unquote(href))
    return m.group(0) if m else None


def _parse_title(text: str) -> tuple[str, str, str]:
    """Split a Google result title into (name, title, company).

    LinkedIn profile titles are stably shaped, e.g.
        "Nitesh Pradhan - Engineering Manager - ABB | LinkedIn"
        "Priya Nair - Engineering Manager at Razorpay | LinkedIn"
        "Aarav Mehta - Nurix AI | LinkedIn"
    """
    text = _LINKEDIN_SUFFIX_RE.sub("", unescape(text)).strip()
    parts = [p.strip() for p in re.split(r"\s[-–—]\s", text) if p.strip()]
    if not parts:
        return "", "", ""
    name = parts[0]
    title = parts[1] if len(parts) > 1 else ""
    company = parts[2] if len(parts) > 2 else ""
    # "Engineering Manager at Razorpay" packs title + company in one segment.
    if title and not company and " at " in title:
        title, company = (s.strip() for s in title.rsplit(" at ", 1))
    return name, title, company


def _result_title_for(anchor) -> str:
    """Find the visible result title (an <h3>) associated with a profile link by
    walking up a few ancestors — robust to Google's shifting result markup."""
    node = anchor
    for _ in range(4):
        if node is None:
            break
        h3 = node.find("h3") if hasattr(node, "find") else None
        if h3 and h3.get_text(strip=True):
            return h3.get_text(" ", strip=True)
        node = node.parent
    # Fall back to the anchor's own text.
    return anchor.get_text(" ", strip=True)


def parse_profiles(html: str) -> list[ProfileHit]:
    """Extract deduped LinkedIn profile hits from a Google X-Ray results page.

    Pure: give it the HTML of a `site:linkedin.com/in <query>` search and it
    returns the people it can see, no network involved.
    """
    hits: dict[str, ProfileHit] = {}
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.find_all("a", href=True)
    except Exception:
        soup, anchors = None, []

    for a in anchors:
        url = _extract_profile_url(a["href"])
        if not url:
            continue
        key = _canonical_profile_url(url)
        if key in hits:
            continue
        name, title, company = _parse_title(_result_title_for(a))
        hits[key] = ProfileHit(linkedin_url=key, full_name=name,
                               job_title=title, company_name=company)

    # Regex safety net: catch profile URLs the DOM walk missed (e.g. results
    # rendered without anchors we recognised) so nothing visible is dropped.
    for m in _PROFILE_RE.finditer(unquote(html)):
        key = _canonical_profile_url(m.group(0))
        hits.setdefault(key, ProfileHit(linkedin_url=key))

    return list(hits.values())


# ── email prediction ────────────────────────────────────────────────────────
def _name_parts(full_name: str) -> tuple[str, str]:
    """(first, last) in lower-case ascii letters only; last is '' for one token."""
    words = _WORD_RE.findall((full_name or "").lower())
    if not words:
        return "", ""
    return words[0], (words[-1] if len(words) > 1 else "")


def infer_domain(company_name: str, company_website: str = "") -> tuple[str, str]:
    """Best-guess email domain for a company and where it came from.

    Returns (domain, source) with source one of 'website' (taken from a known
    company URL — trustworthy) or 'guessed' (slugged from the company name —
    plausible but unconfirmed) or ('', '') when nothing usable is available.
    """
    website = (company_website or "").strip()
    if website:
        host = urlparse(website if "//" in website else f"//{website}").netloc.lower()
        if host.startswith("www."):
            host = host[4:]  # drop the www. prefix only — not leading 'w'/'.'
        if "." in host:
            return host, "website"

    tokens = [t for t in _WORD_RE.findall((company_name or "").lower())
              if t not in _COMPANY_NOISE]
    if tokens:
        return "".join(tokens) + ".com", "guessed"
    return "", ""


def _email_candidates(first: str, last: str, domain: str) -> list[str]:
    """Common work-email formats, most-likely first. Deterministic ordering."""
    if not domain or not first:
        return []
    if last:
        locals_ = [f"{first}.{last}", f"{first}{last}", f"{first[0]}{last}",
                   f"{first}", f"{first}_{last}"]
    else:
        locals_ = [first]
    seen, out = set(), []
    for lp in locals_:
        if lp not in seen:
            seen.add(lp)
            out.append(f"{lp}@{domain}")
    return out


def predict_email(full_name: str, company_name: str,
                  company_website: str = "") -> EmailPrediction:
    """Predict a likely work email and a confidence label. Never 'verified'.

    Confidence blends how sure we are of the *domain* (a known company website
    beats a guessed slug) with how complete the *name* is (first+last beats a
    lone first name).
    """
    first, last = _name_parts(full_name)
    domain, source = infer_domain(company_name, company_website)
    candidates = _email_candidates(first, last, domain)
    if not candidates:
        return EmailPrediction()  # nothing to go on -> unknown / low

    full_name_known = bool(first and last)
    if source == "website":
        confidence = "high" if full_name_known else "medium"
    else:  # guessed domain
        confidence = "medium" if full_name_known else "low"

    return EmailPrediction(email=candidates[0], confidence=confidence,
                           status="predicted", candidates=candidates)


# ── the enrichment step: profiles + a target job -> proposed lead records ────
def hit_to_lead_fields(hit: ProfileHit, *, company_name: str, city: str = "",
                       persona_tag: str = "") -> dict:
    """Turn one parsed profile into a raw lead dict ready for `build_lead` /
    `add_lead`. The target `company_name` (the anchor of the X-Ray search) wins
    over any company text parsed from the result, and drives email prediction.
    """
    pred = predict_email(hit.full_name, company_name)
    return {
        "full_name": hit.full_name,
        "job_title": hit.job_title,
        "company_name": company_name,
        "city": hit.location or city,
        "linkedin_url": hit.linkedin_url,
        "persona_tag": persona_tag,
        "email": pred.email,               # predicted email flows into the
                                           # existing has_email pipeline routing
        "predicted_email": pred.email,
        "email_confidence": pred.confidence if pred.email else "",
        "email_status": pred.status if pred.email else "unknown",
    }


def fetch_xray(url: str, *, timeout: float = 8.0) -> str:
    """GET a Google X-Ray results URL and return its HTML.

    Impure edge of the module. Uses only the stdlib and the operator's own
    Google query — no third-party search API. Google often answers automated
    requests with a consent/CAPTCHA page instead of results; callers treat a
    thin/empty parse as "nothing found" and fall back to an operator paste
    rather than trying to defeat that wall.
    """
    import urllib.request

    req = urllib.request.Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0 Safari/537.36"),
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")
