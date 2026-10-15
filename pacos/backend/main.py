"""FastAPI application entry point for PACOS.

Wraps the tested `pacos` core with a REST API for the React dashboard. Strictly
human-in-the-loop: it can generate assets and record approvals, but never sends.

Run:  uvicorn backend.main:app --reload   (from the pacos/ folder)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sys
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pacos.config import REPO_ROOT

# The auth middleware reads os.environ, but config.load() only pulls .env in
# lazily, which left the very first request unauthenticated. Load just the auth
# keys up front (real environment variables still win, as with load_dotenv).
_AUTH_KEYS = ("PACOS_LOGIN_EMAIL", "PACOS_LOGIN_PASSWORD", "PACOS_LOGIN_TRIAL",
              "PACOS_AUTH_TOKEN")
for _k, _v in dotenv_values(REPO_ROOT / ".env").items():
    if _k in _AUTH_KEYS and _v is not None:
        os.environ.setdefault(_k, _v)

from .routes import (agents, approvals, assets, chat, discovery, inbox, leads,
                     settings, tracker)

app = FastAPI(
    title="PACOS API",
    version="1.0.0",
    description="Personal AI Career Operating System. Nemotron-powered, human-in-the-loop.",
)

# CORS for the Vite dev server (and any deployed frontend origin).
_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── auth (cloud deployments) ────────────────────────────────────────────────
# When PACOS_LOGIN_EMAIL + PACOS_LOGIN_PASSWORD are set, the dashboard shows a
# login form; POST /api/login trades the credentials for a session token, and
# every other /api/* call must carry `Authorization: Bearer <token>`. The token
# is derived from the credentials, so it needs no server-side storage and
# changing the password logs every browser out. PACOS_AUTH_TOKEN still works
# as a raw bearer token for scripts. Nothing set (the default) keeps local/exe
# usage frictionless. /api/health and /api/login stay open; OPTIONS passes so
# CORS preflights (which never carry credentials) still work.
_OPEN_PATHS = {"/api/health", "/api/login", "/api/login/trial"}


def _login_creds() -> tuple[str, str]:
    return (os.getenv("PACOS_LOGIN_EMAIL", "").strip().lower(),
            os.getenv("PACOS_LOGIN_PASSWORD", ""))


def _session_token() -> str:
    email, password = _login_creds()
    if not (email and password):
        return ""
    return hmac.new(f"{email}\n{password}".encode(), b"pacos-session",
                    hashlib.sha256).hexdigest()


@app.middleware("http")
async def require_bearer_token(request, call_next):
    valid = [t for t in (_session_token(), os.getenv("PACOS_AUTH_TOKEN", "").strip()) if t]
    path = request.url.path
    if (valid and request.method != "OPTIONS"
            and path.startswith("/api/") and path not in _OPEN_PATHS):
        supplied = request.headers.get("authorization", "")
        if not any(secrets.compare_digest(supplied, f"Bearer {t}") for t in valid):
            return JSONResponse(status_code=401,
                                content={"detail": "unauthorized: please log in"})
    return await call_next(request)


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/api/login")
def login(body: LoginBody):
    email, password = _login_creds()
    if not (email and password):
        raise HTTPException(400, "Login is not configured on this server.")
    ok_email = secrets.compare_digest(body.email.strip().lower().encode(), email.encode())
    ok_pass = secrets.compare_digest(body.password.encode(), password.encode())
    if not (ok_email and ok_pass):
        raise HTTPException(401, "Wrong email or password.")
    return {"token": _session_token()}


@app.get("/api/login/trial")
def login_trial():
    """Trial credentials for the login page's hint box. Only exposed when
    PACOS_LOGIN_TRIAL=1, i.e. the login is deliberately public (a demo)."""
    email, password = _login_creds()
    public = os.getenv("PACOS_LOGIN_TRIAL", "").strip().lower() in {"1", "true", "yes", "on"}
    if not (public and email and password):
        return {"email": "", "password": ""}
    return {"email": email, "password": password}


app.include_router(leads.router)
app.include_router(assets.router)
app.include_router(agents.router)
app.include_router(approvals.router)
app.include_router(tracker.router)
app.include_router(chat.router)
app.include_router(inbox.router)
app.include_router(discovery.router)
app.include_router(settings.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "pacos", "version": "1.0.0"}


# ── static frontend (production / exe) ──────────────────────────────────────
# In dev, Vite serves the UI on :5173 and proxies /api here, so this mount is
# absent. In a build (or the PyInstaller exe) we serve frontend/dist ourselves.
def _dist_dir() -> Path | None:
    if getattr(sys, "frozen", False):  # PyInstaller unpack dir
        cand = Path(sys._MEIPASS) / "frontend_dist"  # noqa: SLF001
    else:
        cand = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    return cand if (cand / "index.html").exists() else None


_dist = _dist_dir()
if _dist is not None:
    # No StaticFiles mount on /assets — it would shadow the React route
    # /assets/:leadId on direct navigation. The SPA fallback below already
    # serves real bundle files (dist/assets/*) and index.html for the rest.

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        # SPA fallback: any non-API path gets index.html (React Router handles it)
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="unknown API path")
        file = (_dist / full_path).resolve()
        if full_path and file.is_file() and file.is_relative_to(_dist.resolve()):
            if full_path.startswith("assets/"):
                # Content-hashed bundle files never change under the same name.
                return FileResponse(file, headers={
                    "Cache-Control": "public, max-age=31536000, immutable"})
            return FileResponse(file)
        # index.html must be revalidated every visit, or browsers keep serving
        # an old page that points at an old bundle after a deploy.
        return FileResponse(_dist / "index.html", headers={"Cache-Control": "no-cache"})
