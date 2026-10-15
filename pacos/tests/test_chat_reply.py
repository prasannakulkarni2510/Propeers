"""Chat must never show an empty bubble when the model drops its 'reply'."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pacos.chat import chat_turn  # noqa: E402

LEAD = {"full_name": "Priya Shah", "job_title": "Engineering Manager",
        "company_name": "Razorpay", "city": "Bengaluru",
        "email": "priya@razorpay.com"}
MSG = [{"role": "user", "content": "Add Priya Shah, EM at Razorpay"}]


class FakeClient:
    available = True

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def complete_json(self, **_):
        self.calls += 1
        return self.replies.pop(0)


def test_normal_reply_passes_through():
    c = FakeClient({"reply": "Got it — drafted.", "lead": LEAD})
    reply, proposal, _, used, _ = chat_turn(c, {}, MSG)
    assert reply == "Got it, drafted." and proposal["full_name"] == "Priya Shah"
    assert used and c.calls == 1


def test_lead_without_reply_gets_a_written_reply():
    c = FakeClient({"lead": LEAD})
    reply, proposal, _, _, _ = chat_turn(c, {}, MSG)
    assert "Priya Shah" in reply and "Razorpay" in reply
    assert proposal["company_name"] == "Razorpay" and c.calls == 1


def test_misnamed_reply_key_is_accepted():
    c = FakeClient({"response": "Here you go."})
    assert chat_turn(c, {}, MSG)[0] == "Here you go."


def test_empty_answer_is_retried_once():
    c = FakeClient({}, {"reply": "Second try worked."})
    assert chat_turn(c, {}, MSG)[0] == "Second try worked." and c.calls == 2


def test_two_empty_answers_give_a_clear_message():
    c = FakeClient({}, {"reply": ""})
    reply = chat_turn(c, {}, MSG)[0]
    assert reply and "try again" in reply and c.calls == 2


# ── drafts asked for in chat ────────────────────────────────────────────────
ASK = [{"role": "user", "content": "Write an email to OML asking for a data science internship"}]


def test_draft_request_returns_the_written_draft():
    c = FakeClient({"reply": "Here's a draft.", "draft": {
        "asset": "cold_email", "to": {"company_name": "OML"},
        "request": "a data science internship"}})
    seen = {}

    def drafter(asset, to, request):
        seen.update(asset=asset, to=to, request=request)
        return "Subject: Data science internship — OML\n\nHi OML team,"

    reply, proposal, _, used, draft = chat_turn(c, {}, ASK, drafter=drafter)
    assert seen == {"asset": "cold_email", "to": {"company_name": "OML"},
                    "request": "a data science internship"}
    assert draft == {"asset": "cold_email",
                     "text": "Subject: Data science internship, OML\n\nHi OML team,"}
    assert proposal is None and used
    assert reply == "Here's a draft email. Review it before sending."


def test_linkedin_dm_draft():
    c = FakeClient({"draft": {"asset": "cold_dm", "to": {}, "request": "intro"}})
    reply, _, _, _, draft = chat_turn(c, {}, ASK, drafter=lambda a, t, r: "Hi, quick note.")
    assert draft == {"asset": "cold_dm", "text": "Hi, quick note."}
    assert reply  # a reply line is written even when the model omits it


def test_unknown_draft_type_is_ignored():
    c = FakeClient({"reply": "ok", "draft": {"asset": "poem", "to": {}, "request": "x"}})
    assert chat_turn(c, {}, ASK, drafter=lambda a, t, r: "never")[4] is None
