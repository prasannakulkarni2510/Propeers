"""Tracker CRM, daily digest, and unmatched-reply endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pacos.digest import build_digest

from ..deps import get_service
from ..models import ActionResult, AssociateRequest, DigestOut, LeadOut, UnmatchedReply
from ..service import Service

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


@router.get("", response_model=list[LeadOut])
def tracker_rows(svc: Service = Depends(get_service)):
    """Only leads that have entered the pipeline (have a tracker status)."""
    return [r for r in svc.leads_with_state() if r["status"]]


@router.get("/digest", response_model=DigestOut)
def digest(svc: Service = Depends(get_service)):
    return DigestOut(text=build_digest(svc.cfg, svc.store))


@router.get("/unmatched", response_model=list[UnmatchedReply])
def unmatched(svc: Service = Depends(get_service)):
    return svc.unmatched()


@router.post("/associate", response_model=ActionResult)
def associate(req: AssociateRequest, svc: Service = Depends(get_service)):
    ok, msg = svc.associate(req.reply_id, req.lead_id)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return ActionResult(ok=True, lead_id=req.lead_id, message=msg)
