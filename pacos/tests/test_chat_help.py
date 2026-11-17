""""How do I use this platform?" brings the walkthrough video into the chat,
opened at the part asked about, with what each part of PACOS does. Answered
without the model."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from pacos.chat import asks_how_to_use  # noqa: E402


@pytest.mark.parametrize("q,chapter", [
    ("how do I use this platform", ""),
    ("How does this work?", ""),
    ("how to use pacos", ""),
    ("is there a tutorial", ""),
    ("what can you do", ""),
    ("How can I get started with this app", ""),
    ("how do i use it?", ""),
    ("walk me through it", ""),
    ("how does find people work?", "find"),
    ("How do I use PACOS to find recruiters", "find"),
    ("how do I use my people", "people"),
    ("how does the board work", "people"),
])
def test_help_questions_pick_a_chapter(q, chapter):
    assert asks_how_to_use(q) == chapter


@pytest.mark.parametrize("q", [
    "How do I follow up with Priya?",
    "how do I use this email",
    "how to use this template in the email",
    "Draft a short LinkedIn DM to an ML manager at Swiggy",
    "Which CV are we using",
])
def test_other_messages_are_not_help(q):
    assert asks_how_to_use(q) is None


@pytest.fixture
def client(tmp_path, monkeypatch):
    shutil.copy(ROOT / "data" / "sample_leads.csv", tmp_path / "leads.csv")
    (tmp_path / "base_cv.txt").write_text("", encoding="utf-8")
    for k, v in {"LEADS_CSV_PATH": "leads.csv", "TRACKER_CSV_PATH": "tracker.csv",
                 "NEW_JOBS_CSV_PATH": "new_jobs.csv", "OUTPUT_DIR": "output",
                 "BASE_CV_PATH": "base_cv.txt"}.items():
        monkeypatch.setenv(k, str(tmp_path / v))
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("NVIDIA_API_KEY", "")
    from backend.deps import get_service
    from backend.main import app
    get_service.cache_clear()
    yield TestClient(app)
    get_service.cache_clear()


def test_help_question_returns_the_video_and_the_features(client):
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "how do I use this platform?"}]}).json()
    assert res["video"] == {"chapter": ""}
    for part in ("My people", "Find people", "My CV", "chat"):
        assert part in res["reply"]
    assert res["llm_used"] is False and res["cv"] is None


def test_help_about_one_part_starts_there(client):
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "how does find people work?"}]}).json()
    assert res["video"] == {"chapter": "find"} and "Find people" in res["reply"]


def test_ordinary_questions_carry_no_video(client):
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Who should I follow up with?"}]}).json()
    assert res["video"] is None
