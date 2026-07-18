"""FastAPI application entry point for PACOS.

Wraps the tested `pacos` core with a REST API for the React dashboard. Strictly
human-in-the-loop: it can generate assets and record approvals, but never sends.

Run:  uvicorn backend.main:app --reload   (from the pacos/ folder)
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

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
# When PACOS_AUTH_TOKEN is set, every /api/* call must carry
# `Authorization: Bearer <token>`. Unset (the default) keeps local/exe usage
# frictionless. /api/health stays open for uptime probes; OPTIONS passes so
# CORS preflights (which never carry credentials) still work.
@app.middleware("http")
async def require_bearer_token(request, call_next):
    token = os.getenv("PACOS_AUTH_TOKEN", "").strip()
    path = request.url.path
    if (token and request.method != "OPTIONS"
            and path.startswith("/api/") and path != "/api/health"):
        supplied = request.headers.get("authorization", "")
        if not secrets.compare_digest(supplied, f"Bearer {token}"):
            return JSONResponse(status_code=401,
                                content={"detail": "unauthorized: bearer token required"})
    return await call_next(request)


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
            return FileResponse(file)
        return FileResponse(_dist / "index.html")
