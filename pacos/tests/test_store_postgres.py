"""Postgres-backend tests for PacosStore — the full store surface against a
real Postgres (Neon/Supabase/local). Skipped unless PACOS_TEST_DATABASE_URL
is set, so the default suite stays offline/sqlite-only.

    PACOS_TEST_DATABASE_URL=postgresql://... pytest tests/test_store_postgres.py
"""
import os
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PG_URL = os.getenv("PACOS_TEST_DATABASE_URL", "").strip()
pytestmark = pytest.mark.skipif(not PG_URL, reason="PACOS_TEST_DATABASE_URL not set")

DATA = ROOT / "data" / "sample_leads.csv"


@pytest.fixture
def store(tmp_path):
    import psycopg

    with psycopg.connect(PG_URL) as conn:  # clean slate per test
        conn.execute(
            "DROP TABLE IF EXISTS leads, tracker, agent_status, unmatched_replies"
        )
    from pacos.store import PacosStore

    return PacosStore(tmp_path / "unused.db", database_url=PG_URL)


def test_schema_and_agent_seed(store):
    assert store.is_postgres
    assert store.leads_empty()
    agents = store.get_agent_status()
    assert len(agents) == 6
    assert all(a["status"] == "idle" for a in agents)


def test_ingest_and_lead_lifecycle(store):
    from pacos.leads import load_leads

    leads = load_leads(DATA)
    assert store.ingest_leads(leads) == 5
    assert not store.leads_empty()

    rows = store.get_leads()
    assert len(rows) == 5
    assert all(r["status"] == "pending" for r in rows)

    lid = rows[0]["lead_id"]
    assert store.mark_sent(lid, channel="email", sent_date=date(2026, 7, 10),
                           follow_up_days=5)
    row = store.get_lead(lid)
    assert row["status"] == "sent"
    assert row["follow_up_due"] == "2026-07-15"
    assert store.due_followups(on=date(2026, 7, 15))

    assert store.mark_reply(lid, intent="interested", reply_date=date(2026, 7, 12))
    row = store.get_lead(lid)
    assert row["status"] == "interested"
    assert row["reply_intent"] == "interested"

    assert store.mark_status(lid, "offer")
    assert store.get_lead(lid)["follow_up_due"] == ""  # terminal clears follow-up
    assert store.status_counts()["offer"] == 1

    # idempotent re-ingest (upsert, not duplicate)
    store.ingest_leads(leads)
    assert len(store.get_leads()) == 5
    assert store.get_lead(lid)["status"] == "offer"  # tracker state survives


def test_add_lead_created_flag(store):
    from pacos.leads import build_lead

    lead = build_lead({"full_name": "Test Person", "company_name": "Acme AI",
                       "job_title": "CTO", "persona_tag": "cto"})
    assert store.add_lead(lead) is True
    assert store.add_lead(lead) is False  # second time = update
    assert store.find_lead_by_email("") is None


def test_unmatched_replies_flow(store):
    from pacos.leads import build_lead

    lead = build_lead({"full_name": "Reply Target", "company_name": "Beta Labs",
                       "job_title": "HR", "persona_tag": "hr"})
    store.add_lead(lead)
    store.add_unmatched_reply(received_date="2026-07-14", sender="x@y.example",
                              subject="Re: hello", intent="interested")
    unmatched = store.list_unmatched()
    assert len(unmatched) == 1
    assert store.associate_reply(unmatched[0]["id"], lead.lead_id)
    assert store.list_unmatched() == []
    assert store.get_lead(lead.lead_id)["status"] == "interested"
    assert not store.associate_reply(99999, lead.lead_id)


def test_agent_status_updates(store):
    store.set_agent_status("cold_email", "running", "lead 3/5")
    st = {a["name"]: a for a in store.get_agent_status()}
    assert st["cold_email"]["status"] == "running"
    store.reset_agent_status()
    st = {a["name"]: a for a in store.get_agent_status()}
    assert st["cold_email"]["status"] == "idle"


def test_export_csv(store, tmp_path):
    from pacos.leads import load_leads

    store.ingest_leads(load_leads(DATA))
    out = store.export_csv(tmp_path / "tracker.csv")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("lead_id,")
    assert len(text.splitlines()) == 6  # header + 5 leads
