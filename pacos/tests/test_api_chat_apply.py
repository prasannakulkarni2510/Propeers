"""POST /api/chat/apply: saving a change the operator confirmed in chat."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    shutil.copy(ROOT / "data" / "sample_leads.csv", tmp_path / "leads.csv")
    monkeypatch.setenv("LEADS_CSV_PATH", str(tmp_path / "leads.csv"))
    monkeypatch.setenv("TRACKER_CSV_PATH", str(tmp_path / "tracker.csv"))
    monkeypatch.setenv("NEW_JOBS_CSV_PATH", str(tmp_path / "new_jobs.csv"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.delenv("PACOS_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("DATABASE_URL", "")

    from backend.deps import get_service
    from backend.main import app

    get_service.cache_clear()
    with TestClient(app) as c:
        yield c
    get_service.cache_clear()


def _priya(client):
    return next(l for l in client.get("/api/leads").json() if l["full_name"] == "Priya Nair")


def test_rejection_with_note_is_saved(client):
    lid = _priya(client)["lead_id"]
    client.post("/api/approvals/sent", json={"lead_id": lid, "channel": "email"})
    r = client.post("/api/chat/apply", json={
        "lead_id": lid, "action": "reply", "intent": "rejected",
        "date": "2026-11-01", "note": "AI Engineer role"})
    assert r.status_code == 200, r.text
    card = r.json()
    assert card["status"] == "rejected" and card["stage"] == "closed"
    assert card["last_reply_date"] == "2026-11-01" and card["follow_up_due"] == ""
    lead = _priya(client)
    assert lead["notes"].endswith("2026-11-01: AI Engineer role")


def test_sent_sets_channel_and_follow_up(client):
    lid = _priya(client)["lead_id"]
    card = client.post("/api/chat/apply", json={
        "lead_id": lid, "action": "sent", "channel": "dm", "date": "2026-10-28"}).json()
    assert card["stage"] == "awaiting" and card["channel"] == "dm"
    assert card["outreach_sent_date"] == "2026-10-28" and card["follow_up_due"]


def test_bad_requests_are_rejected(client):
    lid = _priya(client)["lead_id"]
    assert client.post("/api/chat/apply", json={"lead_id": "nobody", "action": "note",
                                                "note": "x"}).status_code == 404
    assert client.post("/api/chat/apply", json={"lead_id": lid, "action": "reply"}).status_code == 422
    assert client.post("/api/chat/apply", json={"lead_id": lid, "action": "delete"}).status_code == 422
    assert client.post("/api/chat/apply", json={"lead_id": lid, "action": "sent",
                                                "date": "soon"}).status_code == 422
