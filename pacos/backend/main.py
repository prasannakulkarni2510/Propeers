"""FastAPI application entry point for PACOS.

Wraps the tested `pacos` core with a REST API for the React dashboard. Strictly
human-in-the-loop: it can generate assets and record approvals, but never sends.

Run:  uvicorn backend.main:app --reload   (from the pacos/ folder)
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import agents, approvals, assets, leads, tracker

app = FastAPI(
    title="PACOS API",
    version="1.0.0",
    description="Personal AI Career Operating System — Nemotron-powered, human-in-the-loop.",
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

app.include_router(leads.router)
app.include_router(assets.router)
app.include_router(agents.router)
app.include_router(approvals.router)
app.include_router(tracker.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "pacos", "version": "1.0.0"}
