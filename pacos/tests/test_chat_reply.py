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
    reply, proposal, _, used = chat_turn(c, {}, MSG)
    assert reply == "Got it, drafted." and proposal["full_name"] == "Priya Shah"
    assert used and c.calls == 1


def test_lead_without_reply_gets_a_written_reply():
    c = FakeClient({"lead": LEAD})
    reply, proposal, _, _ = chat_turn(c, {}, MSG)
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
