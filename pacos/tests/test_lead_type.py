"""Unit tests for the person/job split and the browser-fetch block detector.
Pure logic, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pacos.browser_fetch import looks_blocked  # noqa: E402
from pacos.leads import build_lead, derive_lead_type  # noqa: E402


def test_derive_lead_type_placeholder_names_are_jobs():
    for name in ["", "Unknown", "unknown", "N/A", "na", "none", "TBD", "-", "?"]:
        assert derive_lead_type(name) == "job", name


def test_derive_lead_type_real_name_is_person():
    assert derive_lead_type("Priya Nair") == "person"


def test_derive_lead_type_placeholder_overrides_explicit_person():
    # A caller can't force a placeholder-named row to be a person: there is
    # nobody to write outreach to.
    assert derive_lead_type("Unknown", "person") == "job"


def test_derive_lead_type_explicit_job_wins_for_real_name():
    assert derive_lead_type("Priya Nair", "job") == "job"


def test_job_lead_id_uses_role_not_first_name():
    # Two jobs at one company must not collide on `company-` alone.
    a = build_lead({"full_name": "", "company_name": "Acme",
                    "job_title": "ML Engineer", "lead_type": "job"})
    b = build_lead({"full_name": "", "company_name": "Acme",
                    "job_title": "Backend Dev", "lead_type": "job"})
    assert a.lead_type == "job"
    assert a.lead_id == "acme-ml-engineer"
    assert b.lead_id == "acme-backend-dev"
    assert a.lead_id != b.lead_id


def test_job_lead_skips_person_required_field_warnings():
    lead = build_lead({"full_name": "", "company_name": "Acme",
                       "job_title": "ML Engineer", "lead_type": "job"})
    joined = " ".join(lead.warnings)
    assert "full_name" not in joined
    assert "linkedin_url" not in joined
    assert "persona_tag" not in joined


def test_looks_blocked():
    assert looks_blocked("<html>Our systems have detected unusual traffic</html>")
    assert looks_blocked("<html>redirect to consent.google.com/...</html>")
    assert not looks_blocked(
        '<html><a href="https://linkedin.com/in/priya">Priya</a></html>')
