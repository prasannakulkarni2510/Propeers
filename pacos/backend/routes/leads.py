"""Leads + dashboard stats endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..models import LeadOut, StatsOut
from ..service import Service

router = APIRouter(prefix="/api", tags=["leads"])


@router.get("/leads", response_model=list[LeadOut])
def list_leads(svc: Service = Depends(get_service)):
    try:
        return svc.leads_with_state()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, svc: Service = Depends(get_service)):
    for row in svc.leads_with_state():
        if row["lead_id"] == lead_id:
            return row
    raise HTTPException(status_code=404, detail="lead not found")


@router.get("/stats", response_model=StatsOut)
def stats(svc: Service = Depends(get_service)):
    return svc.stats()
