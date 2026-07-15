"""Leads + dashboard stats endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..models import (ActionResult, AddLeadRequest, AddLeadResult, LeadOut,
                      ParseJDRequest, ParseJDResult, StatsOut)
from ..service import Service

router = APIRouter(prefix="/api", tags=["leads"])


@router.get("/leads", response_model=list[LeadOut])
def list_leads(svc: Service = Depends(get_service)):
    try:
        return svc.leads_with_state()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/leads/parse-jd", response_model=ParseJDResult)
def parse_jd(req: ParseJDRequest, svc: Service = Depends(get_service)):
    """Extract proposed lead fields from a pasted JD. Writes nothing — the
    operator reviews the proposal, then confirms via POST /api/leads."""
    fields, warnings, llm_used = svc.parse_jd(req.text)
    return ParseJDResult(fields=fields, warnings=warnings, llm_used=llm_used,
                         model=svc.cfg.nemotron_model if llm_used else "offline-fallback")


@router.post("/leads", response_model=AddLeadResult, status_code=201)
def add_lead(req: AddLeadRequest, svc: Service = Depends(get_service)):
    """Add a lead to the lead sheet (leads.csv) and the tracker."""
    try:
        lead, created, message, warnings = svc.add_lead(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return AddLeadResult(lead=lead, created=created, message=message, warnings=warnings)


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, svc: Service = Depends(get_service)):
    for row in svc.leads_with_state():
        if row["lead_id"] == lead_id:
            return row
    raise HTTPException(status_code=404, detail="lead not found")


@router.delete("/leads/{lead_id}", response_model=ActionResult)
def delete_lead(lead_id: str, svc: Service = Depends(get_service)):
    """Remove a lead from the tracker, the lead sheet, and its assets."""
    ok, message = svc.delete_lead(lead_id)
    if not ok:
        raise HTTPException(status_code=404, detail=message)
    return ActionResult(ok=True, lead_id=lead_id, message=message)


@router.get("/stats", response_model=StatsOut)
def stats(svc: Service = Depends(get_service)):
    return svc.stats()
