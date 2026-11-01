"""Central configuration for PACOS, loaded from environment / .env.

All tunables live here so the rest of the code never touches os.environ
directly. Call `load()` once at process start (the CLI does this for you).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root = two levels up from this file (src/pacos/config.py -> repo root).
# In a frozen (PyInstaller) build, __file__ lives in an unpack temp dir, so the
# root is instead the folder the exe sits in — .env, data/ and output/ go there.
if getattr(sys, "frozen", False):
    REPO_ROOT = Path(sys.executable).resolve().parent
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_EMBEDDING_MODEL = "nvidia/nemotron-3.5-embed-1b"
# Shipped in older .env.example files, before embeddings moved to NVIDIA NIM.
# NIM has retired it, so sending it would only fail on every chat turn.
_RETIRED_EMBEDDING_MODELS = {"baai/bge-m3"}


def _embedding_model(value: str | None) -> str:
    """EMBEDDING_MODEL, with a retired legacy value swapped for the default.
    Unset means the default; set but empty means "no semantic search"."""
    if value is None:
        return DEFAULT_EMBEDDING_MODEL
    value = value.strip()
    if value.lower() in _RETIRED_EMBEDDING_MODELS:
        print(f"[pacos] EMBEDDING_MODEL={value} is retired; using "
              f"{DEFAULT_EMBEDDING_MODEL}. Update your .env.", file=sys.stderr)
        return DEFAULT_EMBEDDING_MODEL
    return value


def _path(env_value: str) -> Path:
    """Resolve a configured path relative to the repo root when not absolute."""
    p = Path(env_value)
    return p if p.is_absolute() else (REPO_ROOT / p)


@dataclass(frozen=True)
class Config:
    # ── Nemotron (generation model) ──────────────────────────────────────
    nvidia_api_key: str
    nemotron_base_url: str
    nemotron_model: str
    # Reads images attached in chat (screenshots of emails, DMs, job posts).
    vision_model: str
    # Reasoning mode for models that support it (the 3.5 family). Off by
    # default: thinking tokens count against max_tokens, and with our small
    # per-call budgets the answer itself can come back empty.
    nemotron_thinking: bool
    nemotron_reasoning_budget: int

    # ── Embeddings (chat record retrieval, via NVIDIA NIM) ──────────────
    embedding_model: str
    hf_token: str  # Hugging Face: only used to deploy to Spaces now

    # ── Tracker backend ──────────────────────────────────────────────────
    # Empty = SQLite file next to tracker.csv (local/exe mode). A Postgres
    # URL = cloud mode, where the filesystem is ephemeral (docs/DEPLOYMENT.md).
    database_url: str

    # ── Files ────────────────────────────────────────────────────────────
    leads_csv: Path
    output_dir: Path
    tracker_csv: Path
    new_jobs_csv: Path
    base_cv: Path

    # ── Candidate identity ───────────────────────────────────────────────
    candidate_name: str
    candidate_headline: str
    candidate_email: str
    candidate_linkedin: str

    # ── Policy ───────────────────────────────────────────────────────────
    follow_up_days: int

    # ── Discovery fetch ──────────────────────────────────────────────────
    # Use a headless browser (Playwright Chromium) for the Google X-Ray fetch
    # when the package is installed. Off = urllib only (paste fallback stays).
    browser_fetch: bool

    # ── Gmail ────────────────────────────────────────────────────────────
    gmail_credentials: Path
    gmail_token: Path

    @property
    def has_nemotron_key(self) -> bool:
        return bool(self.nvidia_api_key)

    @property
    def db_path(self) -> Path:
        """SQLite source of truth (ADR 0003); derived from the tracker path."""
        return self.tracker_csv.with_suffix(".db")


def load(dotenv_path: str | os.PathLike | None = None) -> Config:
    """Load configuration from .env + environment, with sensible defaults."""
    load_dotenv(dotenv_path or (REPO_ROOT / ".env"))

    return Config(
        nvidia_api_key=os.getenv("NVIDIA_API_KEY", "").strip(),
        nemotron_base_url=os.getenv(
            "NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1"
        ).strip(),
        nemotron_model=os.getenv(
            "NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"
        ).strip(),
        vision_model=os.getenv(
            "VISION_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"
        ).strip(),
        nemotron_thinking=os.getenv("NEMOTRON_THINKING", "0").strip().lower()
        in {"1", "true", "yes", "on"},
        nemotron_reasoning_budget=int(os.getenv("NEMOTRON_REASONING_BUDGET", "4096")),
        database_url=os.getenv("DATABASE_URL", "").strip(),
        embedding_model=_embedding_model(os.getenv("EMBEDDING_MODEL")),
        hf_token=os.getenv("HF_TOKEN", "").strip(),
        leads_csv=_path(os.getenv("LEADS_CSV_PATH", "data/leads.csv")),
        output_dir=_path(os.getenv("OUTPUT_DIR", "output")),
        tracker_csv=_path(os.getenv("TRACKER_CSV_PATH", "tracker.csv")),
        new_jobs_csv=_path(os.getenv("NEW_JOBS_CSV_PATH", "new_jobs.csv")),
        base_cv=_path(os.getenv("BASE_CV_PATH", "data/base_cv.txt")),
        candidate_name=os.getenv("CANDIDATE_NAME", "").strip(),
        candidate_headline=os.getenv("CANDIDATE_HEADLINE", "").strip(),
        candidate_email=os.getenv("CANDIDATE_EMAIL", "").strip(),
        candidate_linkedin=os.getenv("CANDIDATE_LINKEDIN", "").strip(),
        follow_up_days=int(os.getenv("FOLLOW_UP_DAYS", "5")),
        browser_fetch=os.getenv("PACOS_BROWSER_FETCH", "1").strip().lower()
        not in {"0", "false", "no", "off"},
        gmail_credentials=_path(os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")),
        gmail_token=_path(os.getenv("GMAIL_TOKEN_PATH", "token.json")),
    )
