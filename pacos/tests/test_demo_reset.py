"""Demo reset: save the people, stages and drafts as the demo, then put them
back in one click with every date moved up to today. Off unless the server is
a deliberate public demo."""
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from pacos.store import PacosStore  # noqa: E402


def _seeded(tmp_path):
    from pacos.leads import load_leads
    s = PacosStore(tmp_path / "t.db")
    s.ingest_leads(load_leads(ROOT / "data" / "sample_leads.csv"))
    return s


def test_reset_restores_state_and_moves_dates(tmp_path):
    s = _seeded(tmp_path)
    a, b, c = [r["lead_id"] for r in s.get_leads()[:3]]
    saved = date(2026, 11, 10)
    s.mark_sent(a, channel="email", sent_date=date(2026, 11, 5))
    s.add_note(a, "Sent the email", on=date(2026, 11, 5))
    s.mark_reply(b, intent="interested", reply_date=date(2026, 11, 8))
    s.save_assets(c, {"cold_email.txt": "Hi"})
    s.create_chat("hello", [{"role": "user", "content": "hi"}])
    assert s.save_demo(on=saved)["saved_on"] == "2026-11-10"
    people = len(s.get_leads())

    # A visitor makes a mess.
    s.delete_lead(c)
    s.mark_status(a, "rejected")
    s.create_chat("mess", [])

    out = s.reset_demo(on=saved + timedelta(days=7))
    assert out["days_moved"] == 7 and out["people"] == people
    assert len(s.get_leads()) == people
    la, lb = s.get_lead(a), s.get_lead(b)
    assert la["status"] == "sent" and la["outreach_sent_date"] == "2026-11-12"
    assert la["follow_up_due"] == "2026-11-17"
    assert la["notes"].endswith("2026-11-12: Sent the email")
    assert lb["status"] == "interested" and lb["last_reply_date"] == "2026-11-15"
    assert s.get_assets(c) == {"cold_email.txt": "Hi"}
    assert s.list_chats() == []


def test_reset_without_a_saved_demo_does_nothing(tmp_path):
    s = _seeded(tmp_path)
    assert s.demo_saved_on() == "" and s.reset_demo() is None
    assert len(s.get_leads()) > 0


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    shutil.copy(ROOT / "data" / "sample_leads.csv", tmp_path / "leads.csv")
    (tmp_path / "base_cv.txt").write_text("", encoding="utf-8")
    for k, v in {"LEADS_CSV_PATH": "leads.csv", "TRACKER_CSV_PATH": "tracker.csv",
                 "NEW_JOBS_CSV_PATH": "new_jobs.csv", "OUTPUT_DIR": "output",
                 "BASE_CV_PATH": "base_cv.txt"}.items():
        monkeypatch.setenv(k, str(tmp_path / v))
    for k in ("DATABASE_URL", "NVIDIA_API_KEY", "PACOS_LOGIN_EMAIL", "PACOS_LOGIN_PASSWORD",
              "PACOS_AUTH_TOKEN", "PACOS_DEMO", "PACOS_LOGIN_TRIAL"):
        monkeypatch.setenv(k, "")

    def make(demo: bool):
        monkeypatch.setenv("PACOS_DEMO", "1" if demo else "")
        from backend.deps import get_service
        from backend.main import app
        get_service.cache_clear()
        return TestClient(app)
    yield make
    from backend.deps import get_service
    get_service.cache_clear()


def test_api_is_off_unless_demo(make_client):
    c = make_client(demo=False)
    assert c.get("/api/demo").json() == {"enabled": False, "saved_on": ""}
    assert c.post("/api/demo/reset").status_code == 404
    assert c.post("/api/demo/save").status_code == 404


def test_api_save_then_reset(make_client):
    c = make_client(demo=True)
    assert c.post("/api/demo/reset").status_code == 409
    n = len(c.get("/api/leads").json())
    assert c.post("/api/demo/save").json()["people"] == n
    assert c.get("/api/demo").json() == {"enabled": True, "saved_on": date.today().isoformat()}
    lead = c.get("/api/leads").json()[0]["lead_id"]
    c.delete(f"/api/leads/{lead}")
    assert len(c.get("/api/leads").json()) == n - 1
    assert c.post("/api/demo/reset").json()["people"] == n
    assert len(c.get("/api/leads").json()) == n
