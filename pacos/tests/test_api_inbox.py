"""Tests for the inbox-scan seam: POST /api/inbox/scan.

Gmail is faked only at the `build_service` boundary (the real external system);
`run_monitor`, the store, and the FastAPI wiring all run for real. No network.
"""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

DATA = ROOT / "data" / "sample_leads.csv"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """App wired to a scratch workspace with the sample lead sheet ingested."""
    shutil.copy(DATA, tmp_path / "leads.csv")
    monkeypatch.setenv("LEADS_CSV_PATH", str(tmp_path / "leads.csv"))
    monkeypatch.setenv("TRACKER_CSV_PATH", str(tmp_path / "tracker.csv"))
    monkeypatch.setenv("NEW_JOBS_CSV_PATH", str(tmp_path / "new_jobs.csv"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(tmp_path / "token.json"))
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", str(tmp_path / "credentials.json"))

    from backend.deps import get_service
    from backend.main import app

    get_service.cache_clear()
    with TestClient(app) as c:
        yield c
    get_service.cache_clear()


def test_scan_without_gmail_setup_returns_actionable_503(client):
    r = client.post("/api/inbox/scan")
    assert r.status_code == 503
    assert "auth_gmail" in r.json()["detail"]


def test_job_alerts_empty_when_no_csv(client):
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert r.json() == []


def test_job_alerts_deduped_newest_first(client, tmp_path):
    (tmp_path / "new_jobs.csv").write_text(
        "date,source,title,company,location,url\n"
        "2026-07-04,linkedin,ML Engineer at Acme,,Bengaluru,https://x.example/jobs/1\n"
        "2026-07-05,naukri,Data Scientist at Beta,,Pune,https://x.example/jobs/2\n"
        "2026-07-04,linkedin,ML Engineer at Acme,,Bengaluru,https://x.example/jobs/1\n",
        encoding="utf-8",
    )
    rows = client.get("/api/jobs").json()
    assert len(rows) == 2  # duplicate URL collapsed
    assert rows[0]["url"] == "https://x.example/jobs/2"  # newest first
    assert rows[1]["title"] == "ML Engineer at Acme"


# ── fake Gmail service (stubs only the external boundary) ──────────────────
def _b64(text: str) -> str:
    import base64
    return base64.urlsafe_b64encode(text.encode()).decode()


def _message(sender: str, subject: str, body: str) -> dict:
    return {
        "payload": {
            "headers": [{"name": "From", "value": sender},
                        {"name": "Subject", "value": subject}],
            "mimeType": "text/plain",
            "body": {"data": _b64(body)},
            "parts": [],
        }
    }


class _Call:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class FakeGmail:
    """Mimics the googleapiclient chained interface for list/get."""

    def __init__(self, messages: dict[str, dict]):
        self._messages = messages

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, userId, q, maxResults):
        return _Call({"messages": [{"id": mid} for mid in self._messages]})

    def get(self, userId, id, format):
        return _Call(self._messages[id])


def test_gmail_api_error_returns_readable_503(client, monkeypatch):
    import httplib2
    from googleapiclient.errors import HttpError

    def boom(cfg):
        raise HttpError(
            resp=httplib2.Response({"status": "403"}),
            content=b'{"error": {"message": "Gmail API has not been used in project X"}}',
        )

    monkeypatch.setattr("pacos.inbox_monitor.build_service", boom)
    r = client.post("/api/inbox/scan")
    assert r.status_code == 503
    assert "Gmail API" in r.json()["detail"]


def test_scan_matches_known_lead_and_records_unmatched(client, monkeypatch):
    fake = FakeGmail({
        "m1": _message("Aarav Mehta <aarav@nurix.example>", "Re: your application",
                       "Thanks for reaching out — we are interested, let's connect."),
        "m2": _message("Someone Else <stranger@nowhere.example>", "Re: hello",
                       "We received your application and are reviewing it."),
    })
    monkeypatch.setattr("pacos.inbox_monitor.build_service", lambda cfg: fake)

    r = client.post("/api/inbox/scan")
    assert r.status_code == 200
    counts = r.json()
    assert counts["scanned"] == 2
    assert counts["matched"] == 1
    assert counts["unmatched"] == 1

    # the matched reply flipped the known lead's status (observed via the API)
    lead = client.get("/api/leads/nurix-ai-aarav").json()
    assert lead["status"] == "interested"

    # the stranger landed in the unmatched queue
    unmatched = client.get("/api/tracker/unmatched").json()
    assert len(unmatched) == 1
    assert "stranger@nowhere.example" in unmatched[0]["sender"]
