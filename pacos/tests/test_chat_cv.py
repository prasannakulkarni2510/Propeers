""""Which CV are we using?" is answered from the store with a card, never by
the model. From a live chat (2026-11-17) where the model said no CV was set."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from pacos.chat import asks_which_cv  # noqa: E402

DATA = ROOT / "data" / "sample_leads.csv"


@pytest.mark.parametrize("q", [
    "Which CV are we using to generate stuff",   # the live transcript
    "which cv is in use?",
    "What resume are you using",
    "show me my CV",
    "Can I download my CV?",
    "which CV is active",
])
def test_cv_questions_are_caught(q):
    assert asks_which_cv(q)


@pytest.mark.parametrize("q", [
    "Draft a cold email to Asha using my CV",
    "Update my CV with the new project",
    "What does my CV say about Python?",
    "How can I improve my resume?",
    "Who should I follow up with this week?",
    "Switch to my data science CV",
])
def test_other_messages_are_left_to_the_model(q):
    assert not asks_which_cv(q)


@pytest.fixture
def client(tmp_path, monkeypatch):
    shutil.copy(DATA, tmp_path / "leads.csv")
    (tmp_path / "base_cv.txt").write_text("", encoding="utf-8")
    for k, v in {"LEADS_CSV_PATH": "leads.csv", "TRACKER_CSV_PATH": "tracker.csv",
                 "NEW_JOBS_CSV_PATH": "new_jobs.csv", "OUTPUT_DIR": "output",
                 "BASE_CV_PATH": "base_cv.txt"}.items():
        monkeypatch.setenv(k, str(tmp_path / v))
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("NVIDIA_API_KEY", "")  # the answer must not need the model
    from backend.deps import get_service
    from backend.main import app
    get_service.cache_clear()
    yield TestClient(app)
    get_service.cache_clear()


def ask(client, q, cv_text=None):
    body = {"messages": [{"role": "user", "content": q}]}
    if cv_text:
        body["cv_text"] = cv_text
    r = client.post("/api/chat", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_names_the_cv_in_use_with_a_card(client):
    client.post("/api/cvs", json={"name": "Data Scientist", "content": "Built forecasting models in Python."})
    ml = client.post("/api/cvs", json={"name": "ML Engineer", "content": "Shipped a RAG assistant to 40 agents."}).json()
    client.post(f"/api/cvs/{ml['cv_id']}/use")

    res = ask(client, "Which CV are we using to generate stuff")
    assert "ML Engineer" in res["reply"] and "1 other CV" in res["reply"]
    assert "haven't set" not in res["reply"].lower()
    cv = res["cv"]
    assert cv["source"] == "saved" and cv["cv_id"] == ml["cv_id"] and cv["name"] == "ML Engineer"
    assert cv["words"] == 7 and cv["total"] == 2
    assert res["llm_used"] is False


def test_temporary_cv_of_this_tab_wins(client):
    client.post("/api/cvs", json={"name": "Data Scientist", "content": "Saved one."})
    res = ask(client, "which cv is in use?", cv_text="A visitor's own CV text here.")
    assert res["cv"]["source"] == "tab" and res["cv"]["words"] == 6
    assert "this tab" in res["reply"].lower()


def test_no_cv_saved_says_so_and_offers_adding_one(client):
    res = ask(client, "which cv is in use?")
    assert res["cv"] == {**res["cv"], "source": "none"}
    assert "sample" in res["reply"] and "My CV" in res["reply"]


def test_other_questions_carry_no_cv_card(client):
    res = ask(client, "Who should I follow up with this week?")
    assert res["cv"] is None
