"""Visitor contact form. A visitor (no login needed) leaves a name, email and a
short note; the backend appends it as a row in a Google Sheet by posting to a
Google Apps Script web app (docs/contact-form-apps-script.gs).

Off unless PACOS_CONTACT_SHEET_URL is set, so local and exe usage never shows
the form. PACOS_CONTACT_SHEET_SECRET, when set, is sent with every row and the
script rejects rows without it, so the script URL alone can't fill the sheet.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/contact", tags=["contact"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Per-visitor limit: a handful of rows per window, so a bot can't fill the sheet.
RATE_LIMIT = 5
RATE_WINDOW_S = 600
_hits: dict[str, deque] = {}
_hits_lock = threading.Lock()


def _sheet_url() -> str:
    return os.getenv("PACOS_CONTACT_SHEET_URL", "").strip()


class ContactBody(BaseModel):
    name: str = Field(max_length=120)
    email: str = Field(max_length=200)
    company: str = Field(default="", max_length=160)
    message: str = Field(default="", max_length=1000)
    ref: str = Field(default="", max_length=60)
    page: str = Field(default="", max_length=40)
    website: str = Field(default="", max_length=200)  # honeypot: people leave it empty


def _client_ip(request: Request) -> str:
    # Render sits behind a proxy; the first X-Forwarded-For entry is the visitor.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _allow(ip: str) -> bool:
    now = time.monotonic()
    with _hits_lock:
        q = _hits.setdefault(ip, deque())
        while q and now - q[0] > RATE_WINDOW_S:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False
        q.append(now)
        return True


def send_row(url: str, row: dict) -> bool:
    """POST the row to the Apps Script web app. Google answers a POST with a
    302 to script.googleusercontent.com; urllib follows it as a GET, which is
    how Apps Script hands back the doPost result."""
    data = json.dumps(row).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            body = res.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    try:
        return bool(json.loads(body).get("ok"))
    except (ValueError, AttributeError):
        # An HTML page here usually means the script isn't deployed for "Anyone".
        return False


@router.get("")
def status():
    return {"enabled": bool(_sheet_url())}


@router.post("")
def submit(body: ContactBody, request: Request):
    url = _sheet_url()
    if not url:
        raise HTTPException(404, "The contact form is off on this server.")
    if body.website.strip():
        return {"ok": True}  # a bot filled the hidden field: pretend it worked
    name, email = body.name.strip(), body.email.strip()
    if not name:
        raise HTTPException(422, "Please add your name.")
    if not _EMAIL.match(email):
        raise HTTPException(422, "Please add a valid email address.")
    if not _allow(_client_ip(request)):
        raise HTTPException(429, "Too many messages from here. Please try again later.")
    row = {
        "secret": os.getenv("PACOS_CONTACT_SHEET_SECRET", "").strip(),
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "name": name,
        "email": email,
        "company": body.company.strip(),
        "message": body.message.strip(),
        "ref": body.ref.strip(),
        "page": body.page.strip(),
    }
    if not send_row(url, row):
        raise HTTPException(502, "Couldn't save your details right now. Please try again in a minute.")
    return {"ok": True}
