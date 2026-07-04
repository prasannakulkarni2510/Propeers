"""Unit tests for the pure logic — no network, no Gmail, no API key required."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pacos.leads import classify_domain, load_leads  # noqa: E402
from pacos.llm import _extract_json  # noqa: E402
from pacos.store import PacosStore  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "sample_leads.csv"


def test_domain_classifier():
    assert classify_domain(industry="Applied AI", company_size="35", funding_stage="Seed") == "startup"
    assert classify_domain(industry="Fintech", company_size="900", funding_stage="Series F") == "enterprise"
    assert classify_domain(industry="GenAI", company_size="120", funding_stage="Series B") == "scaleup"
    assert classify_domain(industry="AI Research Lab", company_size="", funding_stage="") == "research"
    assert classify_domain(industry="IT services", company_size="", funding_stage="") == "services"
    assert classify_domain(industry="", company_size="", funding_stage="Pre-seed") == "startup"


def test_load_sample_leads_and_derived_fields():
    leads = load_leads(DATA)
    assert len(leads) == 5
    aarav = leads[0]
    assert aarav.first_name == "Aarav"
    assert aarav.domain_tag == "startup"
    assert aarav.folder_name == "Nurix-AI_Aarav"
    assert aarav.has_email is True
    assert leads[1].has_email is False  # Priya, no email


def test_extract_json_variants():
    assert _extract_json('{"a": 1}') == {"a": 1}
    assert _extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert _extract_json('Here:\n{"a": 3, "b": {"c": 4}}\nThanks!') == {"a": 3, "b": {"c": 4}}
    assert _extract_json("no json here") is None


def _store(tmp_path):
    s = PacosStore(tmp_path / "pacos.db")
    s.ingest_leads(load_leads(DATA))
    return s


def test_store_flow(tmp_path):
    s = _store(tmp_path)
    lead = load_leads(DATA)[0]
    assert len(s.get_leads()) == 5

    s.upsert_from_generation(lead.lead_id, "a strong hook")
    assert s.get_lead(lead.lead_id)["assets_generated"] == "true"
    assert s.get_lead(lead.lead_id)["status"] == "pending"

    s.mark_sent(lead.lead_id, channel="email", sent_date=date(2026, 7, 1), follow_up_days=5)
    row = s.get_lead(lead.lead_id)
    assert row["status"] == "sent"
    assert row["follow_up_due"] == "2026-07-06"
    assert len(s.due_followups(on=date(2026, 7, 7))) == 1

    # a replied lead is no longer a cold follow-up
    s.mark_reply(lead.lead_id, intent="interested", reply_date=date(2026, 7, 4))
    assert s.get_lead(lead.lead_id)["status"] == "interested"
    assert len(s.due_followups(on=date(2026, 7, 7))) == 0

    # terminal status clears follow-up
    s.mark_status(lead.lead_id, "offer")
    assert s.get_lead(lead.lead_id)["follow_up_due"] == ""


def test_exact_email_match_and_unmatched(tmp_path):
    s = _store(tmp_path)
    leads = load_leads(DATA)
    aarav = leads[0]  # has email
    assert s.find_lead_by_email(aarav.email) == aarav.lead_id
    assert s.find_lead_by_email("stranger@nowhere.com") is None

    s.add_unmatched_reply(received_date="2026-07-04", sender="r@x.com",
                          subject="hello", intent="interested")
    assert len(s.list_unmatched()) == 1
    rid = s.list_unmatched()[0]["id"]
    assert s.associate_reply(rid, aarav.lead_id) is True
    assert s.get_lead(aarav.lead_id)["status"] == "interested"
    assert len(s.list_unmatched()) == 0  # now associated


def test_conditional_skip_email_route():
    from pacos.graph.edges import route_assets
    assert set(route_assets({"lead": {"has_email": True}})) == \
        {"cold_email", "cold_dm", "cover_letter", "cv_notes"}
    assert "cold_email" not in route_assets({"lead": {"has_email": False}})
