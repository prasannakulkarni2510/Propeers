"""A message is written by the candidate to someone else, never the reverse.

From a live draft for a lead with no contact name: "Hi Prasanna, I noticed
your hands-on work building PACOS, a multi-layer job-search automation
pipeline. My own experience mirrors that focus…" (Prasanna is the sender.)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pacos.graph import prompts  # noqa: E402
from pacos.graph.prompts import fix_greeting, write_asset  # noqa: E402

ME = {"name": "Prasanna Kulkarni", "headline": "", "email": "", "linkedin": ""}


class FakeClient:
    available = True

    def __init__(self, *texts):
        self.texts = list(texts)
        self.prompts = []

    def complete_text(self, *, user, **_):
        self.prompts.append(user)
        return self.texts.pop(0)


def test_unknown_reader_is_never_greeted_by_a_name():
    for draft, want in [
        ("Hi Prasanna, I saw your work on PACOS.", "Hi, I saw your work on PACOS."),
        ("Hi [First Name],\n\nI noticed ABB.", "Hi,\n\nI noticed ABB."),
        ("Subject: x\n\nHi Priya, I saw ABB.", "Subject: x\n\nHi, I saw ABB."),  # invented
    ]:
        assert fix_greeting(draft, "cold_email", "", "Prasanna", "ABB")[0] == want


def test_truthful_greetings_are_left_alone():
    for draft, first in [
        ("Hi ABB team, I built PACOS.", ""),
        ("Hi, I'm Prasanna, an AI engineer.", ""),
        ("Dear Hiring Team,\n\nI am writing.", ""),
        ("Hi Aditi, I saw your work at ABB.", "Aditi"),
        ("Hi Prasanna, thanks.", "Prasanna"),  # a reader who shares the sender's name
    ]:
        assert fix_greeting(draft, "cold_dm", first, "Prasanna", "ABB") == (draft, False)


def test_known_reader_replaces_the_senders_name():
    text, again = fix_greeting("Hi Prasanna, I saw your work.", "cold_dm", "Aditi", "Prasanna")
    assert text == "Hi Aditi, I saw your work." and again


def test_draft_addressed_to_the_sender_is_written_again():
    c = FakeClient("Hi Prasanna, I noticed your hands-on work building PACOS.",
                   "Hi, I built PACOS, a job-search pipeline. Open to a short chat?")
    text = write_asset(c, "cold_dm", "PROMPT", recipient_first="", candidate=ME, company="ABB")
    assert text.startswith("Hi, I built PACOS") and len(c.prompts) == 2
    assert "wrong person" in c.prompts[1] and "wrong person" not in c.prompts[0]


def test_good_draft_is_written_once_and_placeholders_never_survive():
    c = FakeClient("Hi Aditi, I built PACOS. Open to a short chat?")
    write_asset(c, "cold_dm", "PROMPT", recipient_first="Aditi", candidate=ME)
    assert len(c.prompts) == 1
    c = FakeClient("Hi, ask [Name] about it.", "Hi, ask [Name] about it.")
    assert "[" not in write_asset(c, "cold_dm", "PROMPT", recipient_first="", candidate=ME)


def test_prompt_names_the_sender_and_omits_an_empty_reader_name():
    user = prompts.build_asset_user("cold_dm", {"company_name": "ABB", "first_name": ""},
                                    ME, "CV", "hook", "read")
    assert "I am Prasanna, the sender" in user and "'Hi ABB team,'" in user
    assert '"first_name"' not in user and "by their first name" not in user
    named = prompts.build_asset_user("cold_dm", {"company_name": "ABB", "first_name": "Aditi"},
                                     ME, "CV", "hook", "read")
    assert "Greet the reader as Aditi." in named
