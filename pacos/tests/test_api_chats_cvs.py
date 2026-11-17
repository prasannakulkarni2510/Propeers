"""Saved chats (list, rename, star, delete) and several CVs with one in use."""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

DATA = ROOT / "data" / "sample_leads.csv"
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

    from backend.deps import get_service
    from backend.main import app
    get_service.cache_clear()
    yield TestClient(app), tmp_path
    get_service.cache_clear()


def test_chat_is_saved_listed_and_reopened(env):
    client, _ = env
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    made = client.post("/api/chats", json={"title": "First", "messages": msgs}).json()
    assert made["title"] == "First" and made["messages"] == msgs and made["starred"] is False

    listed = client.get("/api/chats").json()
    assert [c["chat_id"] for c in listed] == [made["chat_id"]]
    assert "messages" not in listed[0]  # the list stays light

    assert client.get(f"/api/chats/{made['chat_id']}").json()["messages"] == msgs


def test_chat_rename_star_and_delete(env):
    client, _ = env
    cid = client.post("/api/chats", json={"messages": []}).json()["chat_id"]

    out = client.patch(f"/api/chats/{cid}", json={"title": "  Razorpay follow-up "}).json()
    assert out["title"] == "Razorpay follow-up"
    assert client.patch(f"/api/chats/{cid}", json={"starred": True}).json()["starred"] is True
    assert client.patch(f"/api/chats/{cid}", json={"title": "  "}).status_code == 422

    more = [{"role": "user", "content": "later"}]
    out = client.patch(f"/api/chats/{cid}", json={"messages": more}).json()
    assert out["messages"] == more and out["title"] == "Razorpay follow-up" and out["starred"]

    assert client.delete(f"/api/chats/{cid}").status_code == 200
    assert client.get(f"/api/chats/{cid}").status_code == 404
    assert client.delete(f"/api/chats/{cid}").status_code == 404
    assert client.get("/api/chats").json() == []


def test_chat_never_stores_images(env):
    client, _ = env
    msgs = [{"role": "user", "content": "", "images": ["data:image/png;base64,AAAA"]}]
    assert client.post("/api/chats", json={"messages": msgs}).status_code == 422


def test_existing_cv_becomes_the_first_card(env):
    client, _ = env
    cvs = client.get("/api/cvs").json()
    assert len(cvs) == 1
    assert cvs[0]["content"] == SAVED and cvs[0]["is_active"] is True


def test_switching_cv_changes_what_generation_reads(env):
    client, tmp = env
    first = client.get("/api/cvs").json()[0]
    second = client.post("/api/cvs", json={"name": "Data roles", "content": "DATA_CV built pipelines"}).json()
    assert second["is_active"] is False  # adding one never switches silently
    assert (tmp / "base_cv.txt").read_text(encoding="utf-8") == SAVED

    used = client.post(f"/api/cvs/{second['cv_id']}/use").json()
    assert used["is_active"] is True
    assert (tmp / "base_cv.txt").read_text(encoding="utf-8") == "DATA_CV built pipelines"
    assert client.get("/api/settings/cv").json()["content"] == "DATA_CV built pipelines"
    by_id = {c["cv_id"]: c for c in client.get("/api/cvs").json()}
    assert by_id[first["cv_id"]]["is_active"] is False

    # Editing the CV in use updates the file; editing another one does not.
    client.patch(f"/api/cvs/{second['cv_id']}", json={"content": "DATA_CV v2"})
    client.patch(f"/api/cvs/{first['cv_id']}", json={"content": "OTHER v2", "name": "ML roles"})
    assert (tmp / "base_cv.txt").read_text(encoding="utf-8") == "DATA_CV v2"

    # Deleting the CV in use falls back to another one.
    assert client.delete(f"/api/cvs/{second['cv_id']}").status_code == 200
    left = client.get("/api/cvs").json()
    assert len(left) == 1 and left[0]["is_active"] and left[0]["name"] == "ML roles"
    assert (tmp / "base_cv.txt").read_text(encoding="utf-8") == "OTHER v2"


def test_saved_cv_is_restored_after_the_disk_is_wiped(env):
    client, tmp = env
    client.get("/api/cvs")  # adopts the saved CV into the database
    (tmp / "base_cv.txt").write_text("", encoding="utf-8")

    from backend.deps import get_service
    get_service.cache_clear()  # a restart
    assert client.get("/api/settings/cv").json()["content"] == SAVED


def test_old_save_endpoint_keeps_the_card_in_step(env):
    client, _ = env
    client.put("/api/settings/cv", json={"content": "NEW_TEXT via the old editor"})
    cvs = client.get("/api/cvs").json()
    assert len(cvs) == 1 and cvs[0]["content"] == "NEW_TEXT via the old editor"


def test_cv_needs_text(env):
    client, _ = env
    assert client.post("/api/cvs", json={"name": "x", "content": "  "}).status_code == 422
    assert client.post("/api/cvs/nope/use").status_code == 404
