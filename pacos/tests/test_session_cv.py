"""Temporary CV: grounds generation for that request only, and is stored nowhere."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

DATA = ROOT / "data" / "sample_leads.csv"
TEMP = "TEMP_CV_MARKER Built a rocket in my garage."
SAVED = "SAVED_CV_MARKER Shipped PACOS."


@pytest.fixture
def env(tmp_path, monkeypatch):
    shutil.copy(DATA, tmp_path / "leads.csv")
    (tmp_path / "base_cv.txt").write_text(SAVED, encoding="utf-8")
    monkeypatch.setenv("LEADS_CSV_PATH", str(tmp_path / "leads.csv"))
    monkeypatch.setenv("TRACKER_CSV_PATH", str(tmp_path / "tracker.csv"))
    monkeypatch.setenv("NEW_JOBS_CSV_PATH", str(tmp_path / "new_jobs.csv"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("BASE_CV_PATH", str(tmp_path / "base_cv.txt"))
    monkeypatch.setenv("DATABASE_URL", "")

    # Stand-in model: records every prompt instead of calling NVIDIA.
    from pacos import llm
    prompts: list[str] = []
    monkeypatch.setattr(llm.NemotronClient, "available", property(lambda self: True))
    monkeypatch.setattr(llm.NemotronClient, "complete_json",
                        lambda self, *, system, user, **k: prompts.append(user)
                        or {"hook": "h", "domain_read": "d"})
    monkeypatch.setattr(llm.NemotronClient, "complete_text",
                        lambda self, *, system, user, **k: prompts.append(user) or "draft")

    from backend.deps import get_service
    from backend.main import app

    get_service.cache_clear()
    with TestClient(app) as c:
        yield c, prompts, tmp_path
    get_service.cache_clear()


def _person_lead(c):
    return next(ld for ld in c.get("/api/leads").json() if ld.get("lead_type") != "job")


def _files_containing(root: Path, text: str) -> list[str]:
    return [str(p) for p in root.rglob("*")
            if p.is_file() and text.encode() in p.read_bytes()]


def test_generate_uses_temp_cv_and_stores_it_nowhere(env):
    c, prompts, tmp = env
    lead = _person_lead(c)
    r = c.post("/api/agents/generate", json={"lead_id": lead["lead_id"], "cv_text": TEMP})
    assert r.status_code == 200 and r.json()["generated"] == 1
    assert prompts and all("TEMP_CV_MARKER" in p for p in prompts)
    assert not any("SAVED_CV_MARKER" in p for p in prompts)
    assert _files_containing(tmp, "TEMP_CV_MARKER") == []  # db, checkpoints, output
    assert "TEMP_CV_MARKER" not in c.get("/api/settings/cv").json()["content"]


def test_regenerate_uses_temp_cv(env):
    c, prompts, tmp = env
    lead = _person_lead(c)
    c.post("/api/agents/generate", json={"lead_id": lead["lead_id"]})
    prompts.clear()
    r = c.post(f"/api/assets/{lead['lead_id']}/regenerate",
               json={"asset": "cold_dm", "cv_text": TEMP})
    assert r.status_code == 200
    assert prompts and all("TEMP_CV_MARKER" in p for p in prompts)
    assert _files_containing(tmp, "TEMP_CV_MARKER") == []


def test_without_temp_cv_the_saved_cv_is_used(env):
    c, prompts, _ = env
    lead = _person_lead(c)
    c.post("/api/agents/generate", json={"lead_id": lead["lead_id"], "cv_text": TEMP})
    prompts.clear()
    c.post("/api/agents/generate", json={"lead_id": lead["lead_id"], "only_missing": False})
    assert prompts and all("SAVED_CV_MARKER" in p for p in prompts)
    assert not any("TEMP_CV_MARKER" in p for p in prompts)
