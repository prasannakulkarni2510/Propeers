"""Images attached in chat: validated, read once, folded into the message."""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from backend import service as service_mod  # noqa: E402
from backend.models import ChatRequest  # noqa: E402

PNG = "data:image/png;base64,iVBORw0KGgo="


def test_image_only_message_is_valid_but_empty_message_is_not():
    ChatRequest(messages=[{"role": "user", "content": "", "images": [PNG]}])
    with pytest.raises(ValidationError):
        ChatRequest(messages=[{"role": "user", "content": "  "}])


def test_only_data_image_urls_and_at_most_three():
    with pytest.raises(ValidationError):
        ChatRequest(messages=[{"role": "user", "images": ["https://evil.example/x.png"]}])
    with pytest.raises(ValidationError):
        ChatRequest(messages=[{"role": "user", "images": [PNG] * 4}])


class _Svc(service_mod.Service):
    """Service without the store: _read_images only needs the LLM client."""

    def __init__(self, available=True):
        self.cfg = None
        self._client = type("C", (), {"available": available})()


def test_latest_images_are_read_and_folded_into_the_message(monkeypatch):
    seen = {}

    def fake_describe(client, images, cfg):
        seen["images"] = images
        return "From: Abhishek Gupta, ABB. We are moving forward with other candidates.\nSummary: rejection."

    monkeypatch.setattr(service_mod, "describe_images", fake_describe)
    msgs = [{"role": "user", "content": "old", "images": ["data:image/png;base64,OLD"]},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "what about this?", "images": [PNG]}]
    out, text, error = _Svc()._read_images(msgs)
    assert not error and seen["images"] == [PNG] and "moving forward" in text
    assert out[-1]["content"].startswith("what about this?\n\n[Attached screenshot")
    assert all("images" not in m for m in out)  # images go no further


def test_images_without_a_key_get_a_clear_reply():
    _, _, error = _Svc(available=False)._read_images(
        [{"role": "user", "content": "", "images": [PNG]}])
    assert "NVIDIA_API_KEY" in error
