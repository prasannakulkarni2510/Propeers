"""Recruiter discovery endpoints. Read-only: builds boolean search queries and
links from job details — the operator runs them in the browser and confirms any
found person through POST /api/leads like every other write."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..models import DiscoveryRequest, DiscoveryResult
from ..service import Service

router = APIRouter(prefix="/api", tags=["discovery"])


@router.post("/discovery", response_model=DiscoveryResult)
def discovery(req: DiscoveryRequest, svc: Service = Depends(get_service)):
    """Boolean search variants for the people behind a job (by explicit fields)."""
    try:
        variants = svc.discover(req.company_name, req.job_title, req.city, req.keywords)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return DiscoveryResult(company_name=req.company_name.strip(),
                           job_title=req.job_title.strip(), city=req.city.strip(),
                           variants=variants)


@router.get("/discovery/{lead_id}", response_model=DiscoveryResult)
def discovery_for_lead(lead_id: str, svc: Service = Depends(get_service)):
    """Boolean search variants seeded from an existing lead's company/role/city."""
    lead = svc.store.get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    try:
        variants = svc.discover(lead["company_name"], lead["job_title"], lead["city"], [])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return DiscoveryResult(company_name=lead["company_name"],
                           job_title=lead["job_title"], city=lead["city"],
                           variants=variants)
