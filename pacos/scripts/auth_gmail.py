"""One-time Gmail OAuth setup for the PACOS Inbox Monitor (read-only).

Run once:  python scripts/auth_gmail.py

Prerequisites (design §6, ~15 min):
  1. Create a project at https://console.cloud.google.com
  2. Enable the Gmail API
  3. Create OAuth 2.0 Desktop credentials, download as credentials.json
  4. Put credentials.json at the path in your .env (GMAIL_CREDENTIALS_PATH)

This opens a browser once, then writes token.json locally. All future runs use
token.json — no browser needed again. Only the read-only scope is requested.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `pacos` importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pacos.config import load  # noqa: E402
from pacos.inbox_monitor import GMAIL_SCOPES  # noqa: E402


def main() -> int:
    cfg = load()
    creds_path = cfg.gmail_credentials
    token_path = cfg.gmail_token

    if not creds_path.exists():
        print(f"[x] credentials.json not found at: {creds_path}")
        print("    Download OAuth 2.0 Desktop credentials from Google Cloud Console")
        print("    and place them there (or set GMAIL_CREDENTIALS_PATH in .env).")
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("[x] google-auth-oauthlib not installed. Run:")
        print("    pip install -r requirements.txt")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"[ok] Authorised. Token saved to: {token_path}")
    print("     The Inbox Monitor is read-only and will not modify your mail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
