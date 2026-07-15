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

    # ── Embeddings (Hugging Face) ────────────────────────────────────────
    embedding_model: str
    hf_token: str

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
            "NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct"
        ).strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3").strip(),
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
        gmail_credentials=_path(os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")),
        gmail_token=_path(os.getenv("GMAIL_TOKEN_PATH", "token.json")),
    )
