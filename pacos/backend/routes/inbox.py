"""Inbox scan endpoint — operator-triggered, one-shot, read-only Gmail."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pacos.inbox_monitor import GmailUnavailable

from ..deps import get_service
from ..models import JobAlertOut, ScanResult
from ..service import Service

router = APIRouter(prefix="/api", tags=["inbox"])


@router.get("/jobs", response_model=list[JobAlertOut])
def job_alerts(svc: Service = Depends(get_service)):
    return svc.job_alerts()


@router.post("/inbox/scan", response_model=ScanResult)
def scan(days: int = 1, svc: Service = Depends(get_service)):
    try:
        return svc.scan_inbox(days=days)
    except GmailUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
