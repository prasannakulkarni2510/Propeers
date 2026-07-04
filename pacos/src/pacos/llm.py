"""Nemotron client wrapper.

PACOS talks to NVIDIA Nemotron through the NIM API, which is OpenAI-compatible,
so we use the `openai` SDK pointed at NVIDIA's base URL. This module exposes a
single `NemotronClient` with a `complete_json` helper that asks the model for a
JSON object and parses it robustly (Nemotron sometimes wraps JSON in prose or a
```json fence, so we extract the first balanced object).

If no API key is configured, the client raises on real calls — callers that want
offline behaviour should check `client.available` and use their own fallback
(the Asset Generator's --dry-run does exactly this).
"""
from __future__ import annotations

import json
import re
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Config


class NemotronError(RuntimeError):
    """Raised when Nemotron cannot produce a usable response."""


class NemotronClient:
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._client = None  # lazy — don't require the key just to import

    @property
    def available(self) -> bool:
        return self._cfg.has_nemotron_key

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.available:
            raise NemotronError(
                "NVIDIA_API_KEY is not set. Add it to .env, or run the generator "
                "with --dry-run to produce template assets without calling Nemotron."
            )
        # Imported lazily so the package imports fine without the dependency.
        from openai import OpenAI

        self._client = OpenAI(
            api_key=self._cfg.nvidia_api_key,
            base_url=self._cfg.nemotron_base_url,
        )
        return self._client

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
    )
    def _chat(self, system: str, user: str, *, temperature: float, max_tokens: int) -> str:
        client = self._ensure_client()
        resp = client.chat.completions.create(
            model=self._cfg.nemotron_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content
        if not content:
            raise NemotronError("Nemotron returned an empty response.")
        return content

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.6,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Call Nemotron and return the parsed JSON object from its reply."""
        raw = self._chat(system, user, temperature=temperature, max_tokens=max_tokens)
        obj = _extract_json(raw)
        if obj is None:
            raise NemotronError(
                "Could not parse JSON from Nemotron response:\n" + raw[:800]
            )
        return obj

    def complete_text(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.6,
        max_tokens: int = 1024,
    ) -> str:
        """Call Nemotron and return the reply as plain text (for asset agents)."""
        return self._chat(
            system, user, temperature=temperature, max_tokens=max_tokens
        ).strip()


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of a model reply.

    Handles three cases: clean JSON, a ```json fenced block, and JSON embedded in
    surrounding prose (by scanning for the first balanced { ... }).
    """
    text = text.strip()

    # 1) Whole response is JSON.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2) Fenced ```json block.
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3) First balanced object scanned from the first '{'.
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break  # malformed — try next '{'
        start = text.find("{", start + 1)

    return None
