"""Layer 2 — Inbox Monitor (read-only Gmail).

Connects to Gmail via the official API with a READ-ONLY scope, parses LinkedIn and
Naukri alert emails, and classifies recruiter replies (design §6). It appends job
alerts to new_jobs.csv and updates the tracker's status/reply columns.

READ-ONLY BY DESIGN: the only scope requested is gmail.readonly. The code never
sends, deletes, labels, or modifies anything in the inbox.
"""
from __future__ import annotations

import base64
import csv
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

from .config import Config
from .store import PacosStore

# Read-only. Do not widen this scope.
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

NEW_JOBS_COLUMNS = ["date", "source", "title", "company", "location", "url"]

# Query used to pull candidate alert/reply mail from the last N days.
DEFAULT_QUERY = (
    'newer_than:{days}d ('
    'from:linkedin.com OR from:naukri.com OR from:jobs-listings@linkedin.com '
    'OR subject:(job OR "job alert" OR application OR interview OR recruiter))'
)

_INTENT_RULES = [
    ("interested", ("interested", "shortlist", "schedule a call", "move forward",
                    "next steps", "would love to", "keen to", "let's connect",
                    "set up a call", "assessment", "take-home")),
    ("interview", ("interview", "invite you", "availability", "calendar",
                   "meeting link", "google meet", "zoom", "teams call")),
    ("rejected", ("unfortunately", "not moving forward", "other candidates",
                  "regret to inform", "position has been filled", "not a fit",
                  "decided not to")),
    ("follow-up", ("received your application", "reviewing", "get back to you",
                   "under review", "will be in touch")),
]


@dataclass
class JobAlert:
    date: str
    source: str
    title: str
    company: str
    location: str
    url: str


class GmailUnavailable(RuntimeError):
    pass


# ── Gmail service construction ──────────────────────────────────────────────
def build_service(cfg: Config):
    """Build a read-only Gmail service from stored OAuth token."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as e:  # pragma: no cover
        raise GmailUnavailable(
            "Google API libraries not installed. `pip install -r requirements.txt`."
        ) from e

    token_path: Path = cfg.gmail_token
    if not token_path.exists():
        raise GmailUnavailable(
            f"No Gmail token at {token_path}. Run `python scripts/auth_gmail.py` once."
        )
    creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ── Parsing helpers ─────────────────────────────────────────────────────────
def _header(payload: dict, name: str) -> str:
    for h in payload.get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_part(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", "replace")


def _extract_bodies(payload: dict) -> tuple[str, str]:
    """Return (plain_text, html) walking the MIME tree."""
    plain, html = "", ""
    stack = [payload]
    while stack:
        part = stack.pop()
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data:
            text = _decode_part(data)
            if mime == "text/plain":
                plain += text
            elif mime == "text/html":
                html += text
        stack.extend(part.get("parts", []) or [])
    return plain, html


def classify_intent(subject: str, body: str) -> str:
    """Best-effort recruiter-reply intent classifier (design §6)."""
    text = f"{subject}\n{body}".lower()
    # interview beats interested beats rejected beats follow-up if multiple match
    for intent in ("interview", "interested", "rejected", "follow-up"):
        keywords = dict(_INTENT_RULES)[intent]
        if any(k in text for k in keywords):
            return intent
    return "follow-up"


def parse_job_alerts(source: str, html: str, plain: str, on: str) -> list[JobAlert]:
    """Extract job postings from a LinkedIn/Naukri alert email."""
    alerts: list[JobAlert] = []
    soup = BeautifulSoup(html or "", "html.parser") if html else None
    if soup is not None:
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True)
            href = a["href"]
            if not text or len(text) < 4:
                continue
            low = href.lower()
            if source == "linkedin" and "/jobs/view/" not in low:
                continue
            if source == "naukri" and "job-listings" not in low and "/jobs/" not in low:
                continue
            alerts.append(
                JobAlert(
                    date=on,
                    source=source,
                    title=text[:140],
                    company="",
                    location="",
                    url=href.split("?")[0],
                )
            )
    # De-dup by url, cap to keep digests readable.
    seen: set[str] = set()
    unique = []
    for al in alerts:
        if al.url in seen:
            continue
        seen.add(al.url)
        unique.append(al)
    return unique[:25]


def _source_of(sender: str) -> str | None:
    s = sender.lower()
    if "linkedin" in s:
        return "linkedin"
    if "naukri" in s:
        return "naukri"
    return None


def _sender_email(sender: str) -> str:
    """Extract the bare email from a From header: 'Jane <jane@acme.com>' -> jane@acme.com."""
    m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", sender or "")
    return m.group(0).lower() if m else ""


def _append_new_jobs(path: Path, alerts: list[JobAlert]) -> None:
    if not alerts:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=NEW_JOBS_COLUMNS)
        if not exists:
            writer.writeheader()
        for al in alerts:
            writer.writerow(asdict(al))


@dataclass
class MonitorResult:
    scanned: int
    job_alerts: int
    replies_classified: int
    matched: int
    unmatched: int


def run_monitor(cfg: Config, store: PacosStore, *, days: int = 1,
                max_messages: int = 100) -> MonitorResult:
    """Read recent mail, extract job alerts, and classify recruiter replies.

    Reply matching is EXACT (ADR: no fuzzy company guessing): a reply updates a
    lead only when its sender email equals a lead's email. Everything else is
    recorded as an unmatched reply for the operator to associate manually.
    """
    service = build_service(cfg)
    today = date.today().isoformat()
    store.set_agent_status("inbox_monitor", "running", "reading Gmail")

    query = DEFAULT_QUERY.format(days=days)
    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_messages)
        .execute()
    )
    message_ids = [m["id"] for m in resp.get("messages", [])]

    all_alerts: list[JobAlert] = []
    replies = matched = unmatched = 0

    for mid in message_ids:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=mid, format="full")
            .execute()
        )
        payload = msg.get("payload", {})
        sender = _header(payload, "From")
        subject = _header(payload, "Subject")
        plain, html = _extract_bodies(payload)
        source = _source_of(sender)

        if source:  # job-board alert email
            all_alerts.extend(parse_job_alerts(source, html, plain, today))
            continue

        # Potential recruiter reply.
        body = plain or BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
        intent = classify_intent(subject, body)
        replies += 1
        email = _sender_email(sender)
        lead_id = store.find_lead_by_email(email) if email else None
        if lead_id:
            store.mark_reply(lead_id, intent=intent)
            matched += 1
        else:
            store.add_unmatched_reply(
                received_date=today, sender=sender, subject=subject, intent=intent)
            unmatched += 1

    _append_new_jobs(cfg.new_jobs_csv, all_alerts)
    store.set_agent_status(
        "inbox_monitor", "done",
        f"{matched} matched, {unmatched} unmatched")

    return MonitorResult(
        scanned=len(message_ids),
        job_alerts=len(all_alerts),
        replies_classified=replies,
        matched=matched,
        unmatched=unmatched,
    )
