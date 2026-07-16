"""Tests for deterministic lead enrichment.

No network: parsing and email prediction are pure, and the /enrich endpoint is
driven with a pasted Google X-Ray results page (the same path an operator uses
when Google blocks the automated fetch).
"""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from pacos.enrichment import (infer_domain, parse_profiles,  # noqa: E402
                              predict_email)

DATA = ROOT / "data" / "sample_leads.csv"

# A trimmed but structurally real Google results page for a
# `site:linkedin.com/in "ABB" ("Engineering Manager")` X-Ray search.
XRAY_HTML = """
<html><body>
<div class="g"><a href="https://www.google.com/url?q=https://in.linkedin.com/in/nitesh-pradhan-abb&sa=U">
  <h3>Nitesh Pradhan - Engineering Manager - ABB | LinkedIn</h3></a>
  <span>Bengaluru, India · Engineering Manager at ABB</span></div>
<div class="g"><a href="https://uk.linkedin.com/in/sara-lund-abb">
  <h3>Sara Lund - Engineering Manager at ABB | LinkedIn</h3></a></div>
<div class="g"><a href="https://in.linkedin.com/in/nitesh-pradhan-abb?trk=public">
  <h3>Nitesh Pradhan - Engineering Manager - ABB | LinkedIn</h3></a></div>
<div class="g"><a href="https://www.linkedin.com/jobs/view/12345">
  <h3>Some job post - not a profile</h3></a></div>
</body></html>
"""


# ── pure parsing ────────────────────────────────────────────────────────────
def test_parse_profiles_extracts_and_dedupes():
    hits = parse_profiles(XRAY_HTML)
    urls = {h.linkedin_url for h in hits}
    # Two distinct people; the ?trk= duplicate of Nitesh collapses; the /jobs/
    # link is not a profile and is excluded.
    assert "https://in.linkedin.com/in/nitesh-pradhan-abb" in urls
    assert "https://uk.linkedin.com/in/sara-lund-abb" in urls
    assert not any("/jobs/" in u for u in urls)
    assert len(hits) == 2


def test_parse_title_splits_name_title_company():
    by_url = {h.linkedin_url: h for h in parse_profiles(XRAY_HTML)}
    nitesh = by_url["https://in.linkedin.com/in/nitesh-pradhan-abb"]
    assert nitesh.full_name == "Nitesh Pradhan"
    assert nitesh.job_title == "Engineering Manager"
    assert nitesh.company_name == "ABB"
    sara = by_url["https://uk.linkedin.com/in/sara-lund-abb"]
    assert sara.job_title == "Engineering Manager"
    assert sara.company_name == "ABB"  # parsed out of "... at ABB"


# ── email prediction ────────────────────────────────────────────────────────
def test_infer_domain_prefers_website_over_guess():
    assert infer_domain("ABB", "https://new.abb.com/careers") == ("new.abb.com", "website")
    assert infer_domain("ABB Technologies Ltd") == ("abb.com", "guessed")
    assert infer_domain("") == ("", "")


def test_infer_domain_strips_only_the_www_prefix():
    # A leading 'www.' is dropped, but a domain that merely starts with 'w'
    # (walmart, wework) or a non-www subdomain (web.) must survive intact.
    assert infer_domain("Walmart", "https://www.walmart.com") == ("walmart.com", "website")
    assert infer_domain("WeWork", "http://www.wework.com/careers") == ("wework.com", "website")
    assert infer_domain("Acme", "https://web.acme.com") == ("web.acme.com", "website")


def test_predict_email_is_never_verified():
    p = predict_email("Nitesh Pradhan", "ABB", "https://abb.com")
    assert p.email == "nitesh.pradhan@abb.com"
    assert p.confidence == "high"      # known domain + full name
    assert p.status == "predicted"     # never 'verified'


def test_predict_email_guessed_domain_is_medium():
    p = predict_email("Nitesh Pradhan", "ABB")
    assert p.email == "nitesh.pradhan@abb.com"
    assert p.confidence == "medium"    # guessed domain, full name
    assert p.status == "predicted"


def test_predict_email_no_name_is_unknown():
    p = predict_email("", "ABB")
    assert p.email == ""
    assert p.status == "unknown"


def test_predict_email_single_name_confidence():
    # One-token name: never as strong as first+last. Guessed domain -> low,
    # a known company website -> medium. Still predicted, never verified.
    guessed = predict_email("Cher", "Sony")
    assert guessed.email == "cher@sony.com"
    assert guessed.confidence == "low" and guessed.status == "predicted"
    known = predict_email("Cher", "Sony", "https://sony.com")
    assert known.confidence == "medium" and known.status == "predicted"


def test_predict_email_candidate_patterns_ordered():
    # first.last is the primary guess; the common alternates follow it so the
    # operator can eyeball other formats without recomputing them.
    cands = predict_email("Nitesh Pradhan", "ABB").candidates
    assert cands[0] == "nitesh.pradhan@abb.com"
    assert "npradhan@abb.com" in cands and "niteshpradhan@abb.com" in cands


def test_parse_profiles_canonicalises_before_dedup():
    # Same person, three URL shapes (case, trailing slash, tracking query) must
    # collapse to one profile hit.
    html = (
        '<a href="https://www.linkedin.com/in/John-Doe/">a</a>'
        '<a href="https://www.linkedin.com/in/john-doe">b</a>'
        '<a href="https://www.linkedin.com/in/john-doe?trk=public">c</a>'
    )
    hits = parse_profiles(html)
    assert len(hits) == 1
    assert hits[0].linkedin_url == "https://www.linkedin.com/in/john-doe"


# ── endpoint (pasted-HTML path, no network) ─────────────────────────────────
@pytest.fixture
def client(tmp_path, monkeypatch):
    shutil.copy(DATA, tmp_path / "leads.csv")
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


def test_enrich_imports_leads_from_pasted_results(client):
    before = len(client.get("/api/leads").json())
    r = client.post("/api/discovery/enrich", json={
        "company_name": "ABB", "job_title": "Engineering Manager",
        "city": "Bengaluru", "pasted_html": XRAY_HTML,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "pasted"
    assert body["profiles_found"] == 2
    assert body["leads_imported"] == 2

    imported = {l["full_name"]: l for l in body["leads"]}
    nitesh = imported["Nitesh Pradhan"]
    assert nitesh["company_name"] == "ABB"
    assert nitesh["predicted_email"] == "nitesh.pradhan@abb.com"
    assert nitesh["email_confidence"] == "medium"   # guessed domain
    assert nitesh["email_status"] == "predicted"

    # Leads actually landed in the tracker and carry the predicted email so the
    # generation pipeline's has_email routing will build a cold email too.
    leads = {l["lead_id"]: l for l in client.get("/api/leads").json()}
    assert len(leads) == before + 2
    row = leads[nitesh["lead_id"]]
    assert row["has_email"] is True
    assert row["email_status"] == "predicted"


# ── E: backward-compat migration (older workspaces) ─────────────────────────
def test_legacy_lead_sheet_header_is_upgraded_on_append(tmp_path):
    """A lead sheet written before the enrichment columns existed must not be
    corrupted when an enriched lead is appended — the header self-upgrades so
    every row stays column-aligned and re-readable."""
    from pacos.leads import CSV_INPUT_COLUMNS, append_lead_to_csv, load_leads

    csv = tmp_path / "leads.csv"
    csv.write_text(  # legacy 11-column header, no predicted_* columns
        "full_name,job_title,company_name,city,linkedin_url,persona_tag,"
        "email,company_size,industry,company_website,funding_stage\n"
        "Old Lead,EM,ABB,Pune,,manager,,,,,\n",
        encoding="utf-8",
    )
    assert append_lead_to_csv(csv, {
        "full_name": "New Person", "job_title": "EM", "company_name": "ABB",
        "persona_tag": "manager", "email": "new.person@abb.com",
        "predicted_email": "new.person@abb.com", "email_confidence": "medium",
        "email_status": "predicted",
    }) is True

    header = csv.read_text(encoding="utf-8").splitlines()[0]
    assert all(col in header for col in CSV_INPUT_COLUMNS)
    leads = {ld.lead_id: ld for ld in load_leads(csv)}  # would raise if misaligned
    assert set(leads) == {"abb-old", "abb-new"}
    assert leads["abb-new"].predicted_email == "new.person@abb.com"


def test_legacy_tracker_db_gains_enrichment_columns(tmp_path):
    """A tracker DB whose leads table predates the enrichment columns must be
    migrated in place (ADD COLUMN), preserving existing leads and accepting the
    new predicted-email fields."""
    import sqlite3

    from pacos.leads import Lead
    from pacos.store import PacosStore

    db = tmp_path / "legacy.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE leads (lead_id TEXT PRIMARY KEY, full_name TEXT, "
        "first_name TEXT, job_title TEXT, company_name TEXT, city TEXT, "
        "linkedin_url TEXT, persona_tag TEXT, domain_tag TEXT, email TEXT, "
        "company_size TEXT, industry TEXT, company_website TEXT, "
        "funding_stage TEXT, folder_name TEXT)"
    )
    con.execute("INSERT INTO leads(lead_id, full_name) VALUES ('old-lead','Old Lead')")
    con.commit()
    con.close()

    store = PacosStore(db)  # __init__ runs the migration
    store.ingest_leads([Lead(
        full_name="New Person", first_name="New", job_title="EM",
        company_name="ABB", city="", linkedin_url="https://in.linkedin.com/in/new",
        persona_tag="manager", domain_tag="enterprise", email="new.person@abb.com",
        predicted_email="new.person@abb.com", email_confidence="medium",
        email_status="predicted",
    )])

    assert store.get_lead("old-lead") is not None  # pre-existing lead survives
    row = store.get_lead("abb-new")
    assert row["predicted_email"] == "new.person@abb.com"
    assert row["email_confidence"] == "medium"
    assert row["email_status"] == "predicted"


def test_enrich_reports_when_no_profiles(client):
    r = client.post("/api/discovery/enrich", json={
        "company_name": "ABB", "pasted_html": "<html><body>nothing here</body></html>",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["leads_imported"] == 0
