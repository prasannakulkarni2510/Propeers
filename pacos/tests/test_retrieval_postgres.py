"""Chat record index on Postgres + pgvector (the cloud backend). Skipped
unless PACOS_TEST_DATABASE_URL points at a Postgres with pgvector available,
so the default suite stays offline:

    PACOS_TEST_DATABASE_URL=postgresql://... pytest tests/test_retrieval_postgres.py
"""
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_retrieval import ASSETS, LEADS, REPLIES, FakeEmbedder  # noqa: E402

from pacos.retrieval import PgRecordIndex, build_docs, open_index, retrieve  # noqa: E402

PG_URL = os.getenv("PACOS_TEST_DATABASE_URL", "").strip()
pytestmark = pytest.mark.skipif(not PG_URL, reason="PACOS_TEST_DATABASE_URL not set")


@pytest.fixture(autouse=True)
def clean():
    import psycopg

    with psycopg.connect(PG_URL) as conn:
        conn.execute("DROP TABLE IF EXISTS chat_docs, chat_meta")


def _wait_embedded(idx, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        st = idx.status()
        if not st["embedding_now"] and st["embedded"] == st["documents"]:
            return st
        time.sleep(0.05)
    return idx.status()


def test_database_url_picks_postgres():
    idx = open_index(database_url=PG_URL, sqlite_path="unused.db")
    assert isinstance(idx, PgRecordIndex) and idx.status()["backend"] == "postgres"


def test_keyword_search_finds_asset_text_and_replies():
    idx = PgRecordIndex(PG_URL)
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    assert idx.search("grid automation robotics")[0]["doc_id"] == "asset:abb-abhishek:cold_email.txt"
    assert any(h["doc_id"] == "reply:7" for h in idx.search("internship reply from zeta"))


def test_sync_updates_and_drops_rows():
    idx = PgRecordIndex(PG_URL)
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    assert idx.status()["documents"] == 6
    idx.sync(build_docs(LEADS[1:], {}, []))
    assert idx.status()["documents"] == 3
    assert not idx.search("grid automation")


def test_vectors_persist_and_only_changed_docs_are_re_embedded():
    emb = FakeEmbedder()
    calls = []
    real = emb.embed
    emb.embed = lambda texts, kind="passage": (calls.append((kind, len(texts))), real(texts, kind))[1]

    idx = PgRecordIndex(PG_URL, emb)
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    st = _wait_embedded(idx)
    assert st["embedded"] == st["documents"] == 6 and not st["error"]
    # The fake embedder is letter counts, so only ask for a top-2 placing.
    assert "razorpay-priya" in [h["lead_id"] for h in idx.search("Priya Shah Razorpay")[:2]]

    # A "restart": a fresh index object over the same database re-embeds nothing.
    calls.clear()
    again = PgRecordIndex(PG_URL, emb)
    again.sync(build_docs(LEADS, ASSETS, REPLIES))
    _wait_embedded(again)
    assert [c for c in calls if c[0] == "passage"] == []

    # One lead's status changes: only its document is embedded again.
    changed = [dict(LEADS[3], status="sent", outreach_sent_date="2026-11-01")] + LEADS[:3]
    again.sync(build_docs(changed, ASSETS, REPLIES))
    _wait_embedded(again)
    assert [c for c in calls if c[0] == "passage"] == [("passage", 1)]


def test_new_embedding_model_re_embeds_everything():
    idx = PgRecordIndex(PG_URL, FakeEmbedder())
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    _wait_embedded(idx)
    other = FakeEmbedder()
    other.model = "another-model"
    idx2 = PgRecordIndex(PG_URL, other)
    idx2.sync(build_docs(LEADS, ASSETS, REPLIES))
    st = _wait_embedded(idx2)
    assert st["embedded"] == 6
    import psycopg

    with psycopg.connect(PG_URL) as c:
        assert c.execute("SELECT value FROM chat_meta WHERE key='vec_model'").fetchone()[0] == "another-model"


def test_retrieve_works_over_postgres():
    idx = PgRecordIndex(PG_URL)
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    r = retrieve([{"role": "user", "content": "what did my email about grid automation say?"}],
                 LEADS, ASSETS, REPLIES, idx)
    assert "abb-abhishek" in r.cards and "grid automation" in r.context
