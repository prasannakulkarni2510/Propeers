"""Tests for the discovery endpoints and the auth-token middleware.

No network — the query builder is pure and the app runs against a scratch
workspace with the sample lead sheet ingested.
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
    """App wired to a scratch workspace; auth off (PACOS_AUTH_TOKEN unset)."""
    shutil.copy(DATA, tmp_path / "leads.csv")
    monkeypatch.setenv("LEADS_CSV_PATH", str(tmp_path / "leads.csv"))
    monkeypatch.setenv("TRACKER_CSV_PATH", str(tmp_path / "tracker.csv"))
    monkeypatch.setenv("NEW_JOBS_CSV_PATH", str(tmp_path / "new_jobs.csv"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.delenv("PACOS_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("DATABASE_URL", "")  # force the sqlite backend

    from backend.deps import get_service
    from backend.main import app

    get_service.cache_clear()
    with TestClient(app) as c:
        yield c
    get_service.cache_clear()


def test_discovery_by_fields(client):
    r = client.post("/api/discovery", json={
        "company_name": "Razorpay", "job_title": "ML Engineer", "city": "Bengaluru",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["company_name"] == "Razorpay"
    groups = [v["group"] for v in body["variants"]]
    assert "Hiring Managers" in groups and "Technical Recruiters" in groups
    v = body["variants"][0]
    assert "Razorpay" in v["query"] and "Bengaluru" in v["query"]
    assert v["linkedin_url"].startswith("https://www.linkedin.com/search/")
    assert v["xray_url"].startswith("https://www.google.com/search?q=")


def test_discovery_blank_company_is_422(client):
    r = client.post("/api/discovery", json={"company_name": "   "})
    assert r.status_code == 422


def test_discovery_for_lead_seeds_from_tracker(client):
    r = client.get("/api/discovery/nurix-ai-aarav")
    assert r.status_code == 200
    body = r.json()
    assert body["company_name"]
    assert all(body["company_name"] in v["query"] or
               f'"{body["company_name"]}"' in v["query"] for v in body["variants"])


def test_discovery_unknown_lead_is_404(client):
    assert client.get("/api/discovery/nope").status_code == 404


# ── auth middleware (token is read per request, so setenv is enough) ───────
@pytest.fixture
def auth_client(client, monkeypatch):
    monkeypatch.setenv("PACOS_AUTH_TOKEN", "s3cret")
    return client


def test_auth_off_by_default(client):
    assert client.get("/api/stats").status_code == 200


def test_auth_rejects_missing_or_wrong_token(auth_client):
    assert auth_client.get("/api/stats").status_code == 401
    r = auth_client.get("/api/stats", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_auth_accepts_token_and_exempts_health(auth_client):
    assert auth_client.get("/api/health").status_code == 200
    r = auth_client.get("/api/stats", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200
