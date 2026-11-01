"""Chat record lookup: name matching, hybrid index, and records in chat replies."""
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pacos.chat import chat_turn  # noqa: E402
from pacos.retrieval import (RecordIndex, build_docs, describe_stage,  # noqa: E402
                             match_leads, retrieve)


def lead(lid, name, company, **kw):
    base = {"lead_id": lid, "full_name": name, "first_name": name.split()[0],
            "job_title": "Engineering Manager", "company_name": company, "city": "Pune",
            "lead_type": "person", "status": "pending", "assets_generated": "",
            "outreach_sent_date": "", "channel": "", "last_reply_date": "",
            "reply_intent": "", "follow_up_due": "", "notes": "", "email": "",
            "predicted_email": "", "email_status": "", "linkedin_url": ""}
    base.update(kw)
    return base


LEADS = [
    lead("abb-abhishek", "Abhishek Gupta", "ABB", status="sent", channel="email",
         outreach_sent_date="2026-10-20", follow_up_due="2026-10-25",
         assets_generated="true"),
    lead("tcs-abhishek", "Abhishek Rao", "TCS"),
    lead("razorpay-priya", "Priya Shah", "Razorpay", status="interested",
         outreach_sent_date="2026-10-01", channel="dm", last_reply_date="2026-10-05",
         reply_intent="interested", assets_generated="true"),
    lead("razorpay-karan", "Karan Mehta", "Razorpay"),
]
ASSETS = {"abb-abhishek": {"cold_email.txt": "Hi Abhishek, I loved ABB's robotics work on grid automation."}}
REPLIES = [{"id": 7, "sender": "hr@zeta.in", "received_date": "2026-10-30",
            "subject": "Re: Data science internship", "intent": "interested",
            "associated_lead_id": ""}]


class FakeEmbedder:
    """Bag-of-letters vectors: deterministic, offline, good enough to rank."""
    available = True
    model = "fake-embed"

    def embed(self, texts, kind="passage"):
        out = []
        for t in texts:
            v = [0.0] * 26
            for ch in t.lower():
                if "a" <= ch <= "z":
                    v[ord(ch) - 97] += 1
            out.append(v)
        return out


def test_full_name_match_beats_company_and_first_name():
    m = {l["lead_id"]: s for l, s in match_leads(
        "What position is my chat with Abhishek Gupta at?", LEADS)}
    assert m == {"abb-abhishek": 3}


def test_company_question_matches_everyone_there():
    m = {l["lead_id"]: s for l, s in match_leads("who have I contacted at Razorpay", LEADS)}
    assert m == {"razorpay-priya": 1, "razorpay-karan": 1}


def test_stage_sentence_uses_live_dates():
    s = describe_stage(LEADS[0], today=date(2026, 11, 2))
    assert "2026-10-20" in s and "email" in s and "chase" in s


def test_keyword_index_finds_asset_text_and_replies(tmp_path):
    idx = RecordIndex(tmp_path / "i.db", embedder=None)
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    hits = idx.search("grid automation robotics")
    assert hits[0]["doc_id"] == "asset:abb-abhishek:cold_email.txt"
    assert any(h["doc_id"] == "reply:7" for h in idx.search("internship reply from zeta"))


def test_sync_drops_removed_leads(tmp_path):
    idx = RecordIndex(tmp_path / "i.db", embedder=None)
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    idx.sync(build_docs(LEADS[1:], {}, []))
    assert idx.status()["documents"] == 3
    assert not idx.search("grid automation")


def test_semantic_index_embeds_in_background(tmp_path):
    idx = RecordIndex(tmp_path / "i.db", embedder=FakeEmbedder())
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    for _ in range(50):
        if idx.status()["embedded"] == idx.status()["documents"]:
            break
        time.sleep(0.05)
    st = idx.status()
    assert st["embedded"] == st["documents"] == 6 and not st["error"]
    assert idx.search("Priya Shah Razorpay")[0]["lead_id"] == "razorpay-priya"


def test_retrieve_gives_named_lead_with_live_state(tmp_path):
    idx = RecordIndex(tmp_path / "i.db", embedder=None)
    idx.sync(build_docs(LEADS, ASSETS, REPLIES))
    r = retrieve([{"role": "user", "content": "where am I with Abhishek Gupta?"}],
                 LEADS, ASSETS, REPLIES, idx)
    assert r.named == ["abb-abhishek"] and list(r.cards) == ["abb-abhishek"]
    assert "Outreach sent on 2026-10-20 by email" in r.context


def test_follow_up_question_reuses_previous_name(tmp_path):
    msgs = [{"role": "user", "content": "status of Priya Shah?"},
            {"role": "assistant", "content": "Interested."},
            {"role": "user", "content": "and when did she reply?"}]
    r = retrieve(msgs, LEADS, ASSETS, REPLIES, None)
    assert "razorpay-priya" in r.cards and "2026-10-05" in r.context


def test_asked_for_email_text_is_included():
    r = retrieve([{"role": "user", "content": "what did my email to Abhishek Gupta say?"}],
                 LEADS, ASSETS, REPLIES, None)
    assert "grid automation" in r.context


class FakeClient:
    available = True

    def __init__(self, reply):
        self.reply = reply
        self.system = ""

    def complete_json(self, *, system, **_):
        self.system = system
        return self.reply


def _retriever(msgs):
    return retrieve(msgs, LEADS, ASSETS, REPLIES, None)


ASK = [{"role": "user", "content": "What position is my chat with Abhishek Gupta at?"}]


def test_chat_returns_cards_for_listed_records_only():
    c = FakeClient({"reply": "Sent by email on 2026-10-20.",
                    "records": ["abb-abhishek", "made-up-id"]})
    reply, _, _, _, _, cards, _ = chat_turn(c, {}, ASK, retriever=_retriever)
    assert "abb-abhishek" in c.system and "2026-10-20" in c.system
    assert [x["lead_id"] for x in cards] == ["abb-abhishek"]
    assert cards[0]["stage"] == "awaiting"


def test_named_lead_shown_even_if_model_forgets_records():
    c = FakeClient({"reply": "You emailed them."})
    cards = chat_turn(c, {}, ASK, retriever=_retriever)[5]
    assert [x["lead_id"] for x in cards] == ["abb-abhishek"]


def test_offline_lookup_answers_from_records():
    class Offline:
        available = False

    reply, _, _, used, _, cards, _ = chat_turn(Offline(), {}, ASK, retriever=_retriever)
    assert not used and "Abhishek Gupta" in reply and "2026-10-20" in reply
    assert cards[0]["lead_id"] == "abb-abhishek"


def test_company_question_shows_company_cards_when_model_lists_none():
    c = FakeClient({"reply": "Two people at Razorpay."})
    msgs = [{"role": "user", "content": "who do I have at Razorpay?"}]
    cards = chat_turn(c, {}, msgs, retriever=_retriever)[5]
    assert {x["lead_id"] for x in cards} == {"razorpay-priya", "razorpay-karan"}


# ── changes proposed from chat ─────────────────────────────────────────────
TODAY = date(2026, 11, 2)
REJECT = [{"role": "user", "content": "Abhishek Gupta from ABB rejected me for the AI Engineer role"}]


def _change(model_change, msgs=REJECT):
    c = FakeClient({"reply": "Marking it rejected.", "records": ["abb-abhishek"],
                    "change": model_change})
    out = chat_turn(c, {}, msgs, retriever=_retriever, today=TODAY)
    assert "Today is Monday 2026-11-02" in c.system
    return out


def test_rejection_becomes_a_reply_change_for_the_named_lead():
    out = _change({"lead_id": "abb-abhishek", "action": "reply", "intent": "rejected",
                   "date": "", "note": "AI Engineer role"})
    change, cards = out[6], out[5]
    assert change["action"] == "reply" and change["intent"] == "rejected"
    assert change["note"] == "AI Engineer role" and change["lead"]["stage"] == "awaiting"
    assert cards == []  # the change card draws this lead itself


def test_change_for_a_lead_that_was_not_looked_up_is_dropped():
    assert _change({"lead_id": "razorpay-karan", "action": "delete"})[6] is None


def test_incomplete_or_future_dated_change_is_cleaned():
    assert _change({"lead_id": "abb-abhishek", "action": "status", "status": "maybe"})[6] is None
    ch = _change({"lead_id": "abb-abhishek", "action": "sent", "date": "2026-12-01"})[6]
    assert ch["date"] == "" and ch["channel"] == "dm"  # no email on file -> DM


def test_delete_change_is_allowed_for_a_looked_up_lead():
    ch = _change({"lead_id": "abb-abhishek", "action": "delete"})[6]
    assert ch["action"] == "delete"


class TwoStepClient:
    """Main call answers in prose only; the extraction call returns the change."""
    available = True

    def __init__(self, main, extracted):
        self.replies = [main, extracted]
        self.systems = []

    def complete_json(self, *, system, **_):
        self.systems.append(system)
        return self.replies.pop(0)


def test_event_without_change_triggers_extraction_and_fixed_reply():
    c = TwoStepClient(
        {"reply": "They were already marked as rejected, nothing to do."},
        {"change": {"lead_id": "abb-abhishek", "action": "reply", "intent": "rejected",
                    "date": "2026-11-01", "note": "AI Engineer role"}})
    reply, _, _, _, _, _, change = chat_turn(c, {}, REJECT, retriever=_retriever, today=TODAY)
    assert len(c.systems) == 2 and "Abhishek Gupta" in c.systems[1]
    assert change["intent"] == "rejected" and change["date"] == "2026-11-01"
    assert "already" not in reply and "nothing is saved until you click Apply" in reply
    assert "rejected you on 2026-11-01" in reply


def test_questions_do_not_trigger_extraction():
    c = TwoStepClient({"reply": "No reply yet.", "records": ["abb-abhishek"]}, {})
    msgs = [{"role": "user", "content": "Has Abhishek Gupta replied?"}]
    assert chat_turn(c, {}, msgs, retriever=_retriever, today=TODAY)[6] is None
    assert len(c.systems) == 1


def test_unknown_company_is_flagged_and_namesakes_not_offered():
    msgs = [{"role": "user", "content": "Abhishek from Capgemini rejected me"}]
    r = retrieve(msgs, LEADS, ASSETS, REPLIES, None)
    assert 'no lead in PACOS works at "Capgemini"' in r.context and r.matched == []
    msgs = [{"role": "user", "content": "Abhishek from ABB rejected me"}]
    assert "no lead in PACOS" not in retrieve(msgs, LEADS, ASSETS, REPLIES, None).context


def test_duplicate_lead_proposal_gives_way_to_change():
    c = TwoStepClient(
        {"reply": "Not in PACOS, want me to add them?",
         "lead": {"full_name": "Abhishek Gupta", "company_name": "ABB"}},
        {"change": {"lead_id": "abb-abhishek", "action": "sent", "channel": "email",
                    "date": "2026-11-01", "note": "Abhishek Gupta emailed"}})
    msgs = [{"role": "user", "content": "I emailed Abhishek Gupta at ABB yesterday"}]
    reply, proposal, _, _, _, _, change = chat_turn(c, {}, msgs, retriever=_retriever, today=TODAY)
    assert proposal is None and change["action"] == "sent" and change["intent"] == ""
    assert "Not in PACOS" not in reply


def test_interview_date_kept_in_note_and_unwrapped_change_accepted():
    c = TwoStepClient(
        {"reply": "Nice!"},
        {"lead_id": "abb-abhishek", "action": "status", "status": "interview",
         "date": "2026-11-06", "note": "3pm"})
    msgs = [{"role": "user", "content": "Interview with Abhishek Gupta from ABB on Friday at 3pm"}]
    change = chat_turn(c, {}, msgs, retriever=_retriever, today=TODAY)[6]
    assert change["note"] == "Interview on 2026-11-06, 3pm" and change["date"] == ""
    assert "Friday 2026-11-06" in c.systems[1]  # the calendar the model reads


def test_event_wording_variants_are_recognised():
    from pacos.chat import _reports_event
    for msg in ["I DMed Abhishek last Thursday", "texted Priya", "Karan turned me down",
                "Priya got back to me", "delete Karan"]:
        assert _reports_event(msg), msg
    assert not _reports_event("Did I email Priya?")


def test_notes_that_only_restate_the_change_are_dropped():
    ch = _change({"lead_id": "abb-abhishek", "action": "reply", "intent": "rejected",
                  "note": "Rejection from Abhishek Gupta at ABB"})[6]
    assert ch["note"] == ""
    ch = _change({"lead_id": "abb-abhishek", "action": "reply", "intent": "rejected",
                  "note": "AI Engineer role at ABB"})[6]
    assert ch["note"] == "AI Engineer role at ABB"


def test_rejected_status_is_recorded_as_a_reply():
    ch = _change({"lead_id": "abb-abhishek", "action": "status", "status": "rejected",
                  "date": "2026-10-31"})[6]
    assert ch["action"] == "reply" and ch["intent"] == "rejected" and ch["date"] == "2026-10-31"


# ── regressions from the first live conversation ───────────────────────────
def test_deleted_person_is_reported_missing_not_swapped_for_a_namesake():
    gone = [l for l in LEADS if l["lead_id"] != "abb-abhishek"]
    gone.append(lead("x-gupta", "Avni Gupta", "Accenture"))  # Gupta is a known surname
    r = retrieve([{"role": "user", "content": "where am I with Abhishek Gupta?"}],
                 gone, {}, [], None)
    assert 'nobody called "Abhishek Gupta" is in PACOS' in r.context
    assert "tcs-abhishek" not in r.matched  # Abhishek Rao is someone else


def test_status_question_lists_leads_with_that_status():
    leads = LEADS + [lead("acme-offer", "Neha Rao", "Acme", status="offer")]
    r = retrieve([{"role": "user", "content": "Do I have any offers?"}], leads, {}, [], None)
    assert r.matched == ["acme-offer"]
    assert "1 lead(s) in PACOS have status offer" in r.context


def test_overdue_list_only_for_general_or_follow_up_questions():
    ask = lambda q: retrieve([{"role": "user", "content": q}], LEADS, ASSETS, REPLIES, None).context
    assert "Follow-ups due" not in ask("what's up with Priya Shah?")
    assert "Follow-ups due" in ask("who should I follow up with?")
    assert "Follow-ups due" in ask("anything I should do today")


def test_missing_person_gets_a_fixed_reply_and_no_cards():
    gone = [l for l in LEADS if l["lead_id"] != "abb-abhishek"]
    gone.append(lead("x-gupta", "Avni Gupta", "Accenture"))
    c = FakeClient({"reply": "He's still pending.", "records": ["tcs-abhishek"]})
    msgs = [{"role": "user", "content": "where am I with Abhishek Gupta?"}]
    reply, _, _, _, _, cards, _ = chat_turn(
        c, {}, msgs, retriever=lambda m: retrieve(m, gone, {}, [], None))
    assert reply.startswith("I couldn't find anyone called Abhishek Gupta") and cards == []


def test_adding_a_missing_person_still_proposes_a_lead():
    c = FakeClient({"reply": "Drafted.", "lead": {"full_name": "Abhishek Gupta", "company_name": "ABB"}})
    gone = [l for l in LEADS if l["lead_id"] != "abb-abhishek"] + [lead("x", "Avni Gupta", "Acc")]
    msgs = [{"role": "user", "content": "add Abhishek Gupta, EM at ABB"}]
    reply, proposal, *_ = chat_turn(c, {}, msgs, retriever=lambda m: retrieve(m, gone, {}, [], None))
    assert proposal["full_name"] == "Abhishek Gupta" and reply == "Drafted."
