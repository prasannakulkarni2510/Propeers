"""Visitor contact form: open without login, validated, forwarded to the sheet."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.routes import contact  # noqa: E402

GOOD = {"name": "Asha", "email": "asha@example.com", "company": "Acme",
        "message": "Saw your post", "ref": "linkedin", "page": "login"}


@pytest.fixture
def sent(monkeypatch):
    rows = []
    monkeypatch.setattr(contact, "send_row", lambda url, row: rows.append((url, row)) or True)
    monkeypatch.setattr(contact, "_hits", {})
    # Login on, like the hosted demo: the form must still work logged out.
    monkeypatch.setenv("PACOS_LOGIN_EMAIL", "abc@pacos.com")
    monkeypatch.setenv("PACOS_LOGIN_PASSWORD", "12345678")
    monkeypatch.setenv("PACOS_CONTACT_SHEET_URL", "https://script.example/exec")
    monkeypatch.setenv("PACOS_CONTACT_SHEET_SECRET", "s3cret")
    return rows


@pytest.fixture
def client():
    return TestClient(app)


def test_off_without_sheet_url(client, monkeypatch):
    monkeypatch.delenv("PACOS_CONTACT_SHEET_URL", raising=False)
    monkeypatch.delenv("PACOS_LOGIN_EMAIL", raising=False)
    assert client.get("/api/contact").json() == {"enabled": False}
    assert client.post("/api/contact", json=GOOD).status_code == 404


def test_submits_without_login(client, sent):
    assert client.get("/api/contact").json() == {"enabled": True}
    r = client.post("/api/contact", json=GOOD)
    assert r.status_code == 200, r.text
    url, row = sent[0]
    assert url == "https://script.example/exec"
    assert row["secret"] == "s3cret"
    assert (row["name"], row["email"], row["company"], row["ref"], row["page"]) == (
        "Asha", "asha@example.com", "Acme", "linkedin", "login")
    assert row["time"].endswith("UTC")


def test_rejects_bad_email_and_missing_name(client, sent):
    assert client.post("/api/contact", json={**GOOD, "email": "nope"}).status_code == 422
    assert client.post("/api/contact", json={**GOOD, "name": "  "}).status_code == 422
    assert sent == []


def test_honeypot_is_dropped_quietly(client, sent):
    r = client.post("/api/contact", json={**GOOD, "website": "http://spam"})
    assert r.status_code == 200
    assert sent == []


def test_rate_limited_per_visitor(client, sent):
    for _ in range(contact.RATE_LIMIT):
        assert client.post("/api/contact", json=GOOD).status_code == 200
    assert client.post("/api/contact", json=GOOD).status_code == 429


def test_sheet_failure_is_reported(client, sent, monkeypatch):
    monkeypatch.setattr(contact, "send_row", lambda url, row: False)
    assert client.post("/api/contact", json=GOOD).status_code == 502


# ── short links ──────────────────────────────────────────────────────────────
PHONE_IG = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Mobile/15E148 Instagram 300.0")
DESKTOP_CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


@pytest.mark.parametrize("path,source", [("/in", "linkedin"), ("/ig", "instagram"), ("/r", "resume")])
def test_short_link_logs_visit_and_redirects_home(client, sent, path, source):
    r = client.get(path, headers={"User-Agent": DESKTOP_CHROME,
                                  "Referer": "https://www.linkedin.com/feed/"},
                   follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/"
    assert "no-store" in r.headers["cache-control"]
    assert r.cookies.get("pacos_ref") == source
    _, row = sent[0]
    assert row["kind"] == "visit" and row["source"] == source
    assert row["device"] == "computer, Chrome"
    assert row["referrer"] == "www.linkedin.com"
    assert row["secret"] == "s3cret"


def test_short_link_needs_no_login(client, sent):
    # Login is on in the fixture; the link must still redirect, not 401.
    assert client.get("/ig", headers={"User-Agent": PHONE_IG},
                      follow_redirects=False).status_code == 302
    assert sent[0][1]["device"] == "phone, Instagram app"


@pytest.mark.parametrize("ua", ["LinkedInBot/1.0", "facebookexternalhit/1.1",
                                "WhatsApp/2.23", "Slackbot-LinkExpanding 1.0", ""])
def test_preview_crawlers_are_not_counted(client, sent, ua):
    r = client.get("/in", headers={"User-Agent": ua}, follow_redirects=False)
    assert r.status_code == 302
    assert sent == []


def test_contact_form_carries_short_link_source(client, sent):
    client.get("/ig", headers={"User-Agent": PHONE_IG}, follow_redirects=False)
    sent.clear()
    r = client.post("/api/contact", json={**GOOD, "ref": ""})
    assert r.status_code == 200
    assert sent[0][1]["ref"] == "instagram"
    # An explicit ?ref= on the address still wins.
    client.post("/api/contact", json={**GOOD, "ref": "linkedin"})
    assert sent[1][1]["ref"] == "linkedin"


def test_short_links_without_sheet_still_redirect(client, monkeypatch):
    monkeypatch.delenv("PACOS_CONTACT_SHEET_URL", raising=False)
    rows = []
    monkeypatch.setattr(contact, "send_row", lambda url, row: rows.append(row) or True)
    r = client.get("/r", headers={"User-Agent": DESKTOP_CHROME}, follow_redirects=False)
    assert r.status_code == 302 and rows == []
