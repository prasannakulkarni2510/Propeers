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
        thinking = self._cfg.nemotron_thinking
        extra_body: dict[str, Any] = {"chat_template_kwargs": {"enable_thinking": thinking}}
        if thinking:
            # Reasoning tokens share max_tokens with the answer, so grow the
            # cap by the budget or the visible reply gets starved.
            budget = self._cfg.nemotron_reasoning_budget
            extra_body["reasoning_budget"] = budget
            max_tokens += budget
        resp = client.chat.completions.create(
            model=self._cfg.nemotron_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body=extra_body,
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


class NemotronEmbedder:
    """Text embeddings from the same NVIDIA NIM endpoint and key as generation.
    Used by the chat's record retrieval (retrieval.py). `kind` is "query" for
    the operator's question and "passage" for the records being indexed;
    retrieval models embed the two differently."""

    BATCH = 50

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._client = None

    @property
    def available(self) -> bool:
        return self._cfg.has_nemotron_key and bool(self._cfg.embedding_model)

    @property
    def model(self) -> str:
        return self._cfg.embedding_model

    def _embed_once(self, texts: list[str], kind: str, *, timeout: float,
                    max_retries: int) -> list[list[float]]:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._cfg.nvidia_api_key,
                                  base_url=self._cfg.nemotron_base_url)
        resp = self._client.with_options(timeout=timeout, max_retries=max_retries).embeddings.create(
            model=self._cfg.embedding_model,
            input=texts,
            extra_body={"input_type": kind, "truncate": "END"},
        )
        return [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]

    @retry(reraise=True, stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=2, max=20))
    def _embed_batch(self, texts: list[str], kind: str) -> list[list[float]]:
        # Background indexing: patient, it isn't blocking anyone.
        return self._embed_once(texts, kind, timeout=60, max_retries=2)

    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        if not self.available:
            raise NemotronError("Embeddings need NVIDIA_API_KEY and EMBEDDING_MODEL.")
        out: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH):
            try:
                if kind == "query":
                    # A chat turn is waiting: one short try, then the caller
                    # falls back to keyword search.
                    out.extend(self._embed_once(texts[i:i + self.BATCH], kind,
                                                timeout=8, max_retries=0))
                else:
                    out.extend(self._embed_batch(texts[i:i + self.BATCH], kind))
            except Exception as e:  # network/API errors -> one error type for callers
                raise NemotronError(f"Embedding call failed: {e}") from e
        return out


_VISION_PROMPT = """These are screenshots a job seeker attached to a message
about their job search (emails, LinkedIn messages, job posts, calendar
invites). Transcribe all readable text exactly, keeping names, email
addresses, companies, roles and dates. Then add one line starting
"Summary:" saying what it is, who it is from and at which company, the date,
and what it means for the job seeker. If an image has no text, describe it
in one sentence. Plain text only."""


def describe_images(client: NemotronClient, images: list[str], cfg: Config) -> str:
    """Read attached images (data: URLs) with the vision model. The images
    are only sent to NVIDIA for this call; nothing is stored."""
    oc = client._ensure_client()
    content: list[dict[str, Any]] = [{"type": "text", "text": _VISION_PROMPT}]
    content += [{"type": "image_url", "image_url": {"url": u}} for u in images]
    try:
        resp = oc.chat.completions.create(
            model=cfg.vision_model,
            messages=[{"role": "user", "content": content}],
            temperature=0.0,
            max_tokens=1500,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
    except Exception as e:
        raise NemotronError(f"Couldn't read the image: {e}") from e
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise NemotronError("The vision model returned nothing for that image.")
    return text


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of a model reply.

    Handles three cases: clean JSON, a ```json fenced block, and JSON embedded in
    surrounding prose (by scanning for the first balanced { ... }). Raw line
    breaks inside strings are accepted (strict=False): models emit them in
    long replies, and rejecting the whole answer over that helps no one.
    """
    text = text.strip()

    # 1) Whole response is JSON.
    try:
        parsed = json.loads(text, strict=False)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2) Fenced ```json block.
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1), strict=False)
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
                        parsed = json.loads(candidate, strict=False)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break  # malformed — try next '{'
        start = text.find("{", start + 1)

    return None
