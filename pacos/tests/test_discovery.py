"""Unit tests for the recruiter-discovery query builder — pure logic, no network."""
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pacos.discovery import TARGET_GROUPS, build_searches  # noqa: E402


def test_requires_company():
    with pytest.raises(ValueError):
        build_searches("   ")


def test_one_variant_per_group_plus_broad():
    variants = build_searches("Razorpay")
    assert len(variants) == len(TARGET_GROUPS) + 1
    assert [v.group for v in variants[:-1]] == [g for g, _, _ in TARGET_GROUPS]
    assert variants[-1].group == "All hiring roles (broad)"


def test_query_shape_and_location():
    variants = build_searches("Razorpay", role="Machine Learning Engineer",
                              location="Bengaluru")
    hm = variants[0]
    assert hm.query.startswith('Razorpay AND ("Hiring Manager" OR ')
    assert '"Bengaluru"' not in hm.query  # single word stays unquoted
    assert "Bengaluru" in hm.query
    assert hm.persona_tag == "manager"
    # role keywords narrow manager-side groups…
    assert "Machine" in hm.query and "Learning" in hm.query
    # …but not recruiter-side groups (titles never echo the role)
    recruiters = next(v for v in variants if v.group == "Technical Recruiters")
    assert "Machine" not in recruiters.query
    assert recruiters.persona_tag == "hr"


def test_multiword_terms_are_quoted_phrases():
    v = build_searches("Nurix AI")[0]
    assert v.query.startswith('"Nurix AI" AND ')


def test_urls_encode_the_query():
    v = build_searches("Razorpay", location="Pune")[0]
    assert v.linkedin_url.startswith(
        "https://www.linkedin.com/search/results/people/?keywords=")
    assert v.xray_url.startswith("https://www.google.com/search?q=")
    assert unquote(v.linkedin_url.split("keywords=")[1]) == v.query
    assert "site:linkedin.com/in" in unquote(v.xray_url.split("q=")[1])


def test_extra_keywords_reach_manager_groups_only():
    variants = build_searches("Acme", extra_keywords=["Python", "PyTorch"])
    assert "PyTorch" in variants[0].query          # hiring managers
    ta = next(v for v in variants if v.group == "Talent Acquisition")
    assert "PyTorch" not in ta.query


def test_seniority_noise_stripped_from_role():
    v = build_searches("Acme", role="Senior Staff Backend Developer (Remote)")[0]
    assert "Senior" not in v.query.replace('"Senior Director"', "")
    assert "Backend" in v.query
