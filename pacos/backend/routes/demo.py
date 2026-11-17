"""Demo reset. On a deliberately public demo (PACOS_LOGIN_TRIAL=1, or
PACOS_DEMO=1) the current people, stages and drafts can be saved as the demo,
and put back in one click, with dates moved up to today. Off everywhere else,
so nobody's real tracker can be wiped by a button."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..service import Service

router = APIRouter(prefix="/api/demo", tags=["demo"])

_ON = {"1", "true", "yes", "on"}


def demo_enabled() -> bool:
    return any(os.getenv(k, "").strip().lower() in _ON for k in ("PACOS_DEMO", "PACOS_LOGIN_TRIAL"))


def _require_demo() -> None:
    if not demo_enabled():
        raise HTTPException(status_code=404, detail="Demo reset is off on this server.")


@router.get("")
def status(svc: Service = Depends(get_service)):
    return svc.demo_status(demo_enabled())


@router.post("/save")
def save(svc: Service = Depends(get_service)):
    _require_demo()
    return svc.save_demo()


@router.post("/reset")
def reset(svc: Service = Depends(get_service)):
    _require_demo()
    out = svc.reset_demo()
    if out is None:
        raise HTTPException(status_code=409, detail="No demo has been saved yet.")
    return out
