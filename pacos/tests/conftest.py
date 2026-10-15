"""Shared test setup.

Tests exercise the API as local/exe usage does: no login. The operator's .env
may turn the login on, and config.load() pulls .env into os.environ, so pin the
auth variables empty first (load_dotenv never overrides an existing variable).
"""
import os

for _key in ("PACOS_LOGIN_EMAIL", "PACOS_LOGIN_PASSWORD", "PACOS_LOGIN_TRIAL",
             "PACOS_AUTH_TOKEN"):
    os.environ[_key] = ""
