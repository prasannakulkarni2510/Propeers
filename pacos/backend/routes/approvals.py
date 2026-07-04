"""Approval queue endpoints — the human-in-the-loop actions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..models import ActionResult, ReplyRequest, SentRequest, StatusRequest
from ..service import Service

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.post("/sent", response_model=ActionResult)
def mark_sent(req: SentRequest, svc: Service = Depends(get_service)):
    ok, msg = svc.mark_sent(req.lead_id, req.channel, req.date)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return ActionResult(ok=True, lead_id=req.lead_id, message=msg)


@router.post("/reply", response_model=ActionResult)
def mark_reply(req: ReplyRequest, svc: Service = Depends(get_service)):
    ok, msg = svc.mark_reply(req.lead_id, req.intent, req.date)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return ActionResult(ok=True, lead_id=req.lead_id, message=msg)


@router.post("/status", response_model=ActionResult)
def mark_status(req: StatusRequest, svc: Service = Depends(get_service)):
    ok, msg = svc.mark_status(req.lead_id, req.status)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return ActionResult(ok=True, lead_id=req.lead_id, message=msg)
