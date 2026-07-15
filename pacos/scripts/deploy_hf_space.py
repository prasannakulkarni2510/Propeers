"""Deploy PACOS to a Hugging Face Space (free Docker hosting).

Creates (or updates) a **private** Docker Space on your account, sets the
secrets from your local .env (values never printed), and uploads a clean
copy of the app. Re-run after code changes to redeploy.

Usage (from pacos/):
    python scripts/deploy_hf_space.py [--name pacos] [--public]

Needs HF_TOKEN in .env with *write* access (create a token at
https://huggingface.co/settings/tokens — "Write" role is simplest).

Free-tier reality check (accepted trade-off, see docs/DEPLOYMENT.md): Space
storage is EPHEMERAL — leads/tracker on the Space reset when it restarts.
Your local workspace remains the source of truth.
"""
from __future__ import annotations

import argparse
import secrets as pysecrets
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]  # pacos/

FRONTMATTER = """---
title: PACOS
emoji: "\\U0001F3AF"
colorFrom: red
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

"""

# What the Docker build needs — nothing personal, nothing generated.
COPY_DIRS = {
    "backend": {"__pycache__"},
    "src": {"__pycache__"},
    "frontend": {"node_modules", "dist"},
}
COPY_FILES = ["Dockerfile", ".dockerignore", "pyproject.toml"]

# Forwarded from .env when non-empty; values never echoed. The HF token
# itself is deliberately NOT forwarded — the Space has no reason to hold it.
SECRET_KEYS = [
    "NVIDIA_API_KEY",
    "CANDIDATE_NAME", "CANDIDATE_HEADLINE", "CANDIDATE_EMAIL",
    "CANDIDATE_LINKEDIN",
]


def stage(dst: Path) -> None:
    for name, excl in COPY_DIRS.items():
        shutil.copytree(
            ROOT / name, dst / name,
            ignore=shutil.ignore_patterns(*excl),
        )
    for name in COPY_FILES:
        shutil.copy(ROOT / name, dst / name)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    (dst / "README.md").write_text(FRONTMATTER + readme, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="pacos", help="Space name (default: pacos)")
    ap.add_argument("--public", action="store_true",
                    help="make the Space public (default: private)")
    args = ap.parse_args()

    env = dotenv_values(ROOT / ".env")
    token = (env.get("HF_TOKEN") or "").strip()
    if not token:
        print("HF_TOKEN missing in .env — add a write token first.")
        return 1

    api = HfApi(token=token)
    user = api.whoami()["name"]
    repo_id = f"{user}/{args.name}"

    print(f"Creating/updating Space {repo_id} (private={not args.public}) ...")
    api.create_repo(repo_id, repo_type="space", space_sdk="docker",
                    private=not args.public, exist_ok=True)

    # ── secrets: server-side only, never printed ────────────────────────
    for key in SECRET_KEYS:
        val = (env.get(key) or "").strip()
        if val:
            api.add_space_secret(repo_id, key, val)
            print(f"  secret set: {key}")

    # The dashboard's access token. Reused from .env when present so the
    # gate survives redeploys; otherwise minted and saved locally
    # (.pacos_space_token, gitignored) — read it from there, not from logs.
    gate = (env.get("PACOS_AUTH_TOKEN") or "").strip()
    if not gate:
        token_file = ROOT / ".pacos_space_token"
        if token_file.exists():
            gate = token_file.read_text(encoding="utf-8").strip()
        else:
            gate = pysecrets.token_urlsafe(24)
            token_file.write_text(gate + "\n", encoding="utf-8")
        print(f"  access token saved to {token_file.name} (gitignored)")
    api.add_space_secret(repo_id, "PACOS_AUTH_TOKEN", gate)
    print("  secret set: PACOS_AUTH_TOKEN")

    # ── upload a clean staging copy; the push triggers the Docker build ──
    tmp = Path(tempfile.mkdtemp(prefix="pacos-space-"))
    try:
        stage(tmp)
        api.upload_folder(folder_path=str(tmp), repo_id=repo_id,
                          repo_type="space",
                          commit_message="Deploy PACOS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nUploaded. Build logs: https://huggingface.co/spaces/{repo_id}")
    print(f"App URL when built:  https://{user.lower()}-{args.name.lower()}.hf.space")
    print("Unlock the dashboard with the PACOS_AUTH_TOKEN value.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
