"""Adding a person with no email predicts one (never claims it's verified)."""
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
    shutil.copy(DATA, tmp_path / "leads.csv")
    monkeypatch.setenv("LEADS_CSV_PATH", str(tmp_path / "leads.csv"))
    monkeypatch.setenv("TRACKER_CSV_PATH", str(tmp_path / "tracker.csv"))
    monkeypatch.setenv("NEW_JOBS_CSV_PATH", str(tmp_path / "new_jobs.csv"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("DATABASE_URL", "")
    from backend.deps import get_service
    from backend.main import app
    get_service.cache_clear()
    with TestClient(app) as c:
        yield c
    get_service.cache_clear()


def _add(client, **fields):
    base = {"job_title": "ML Manager", "persona_tag": "manager"}
    r = client.post("/api/leads", json={**base, **fields})
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_person_without_email_gets_a_prediction(client):
    body = _add(client, full_name="Neha Gupta", company_name="Flipkart",
                company_website="https://www.flipkart.com")
    lead = body.get("lead", body)
    assert lead["predicted_email"].endswith("@flipkart.com")
    assert lead["email_status"] == "predicted" and lead["email_confidence"] == "high"
    assert any("predicted" in w and "not verified" in w for w in body.get("warnings", []))


def test_given_email_is_kept(client):
    body = _add(client, full_name="Priya Shah", company_name="Razorpay",
                email="priya@razorpay.com")
    lead = body.get("lead", body)
    assert lead["email"] == "priya@razorpay.com" and not lead.get("predicted_email")


def test_job_posting_gets_no_prediction(client):
    body = _add(client, full_name="unknown", company_name="Swiggy")
    lead = body.get("lead", body)
    assert not lead.get("predicted_email") and not lead.get("email")
