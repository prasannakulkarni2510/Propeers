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
