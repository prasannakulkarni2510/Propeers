"""Agent trigger + status endpoints (Layer 1 generation)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_service
from ..models import AgentState, GenerateRequest, GenerateResult
from ..service import Service

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/status", response_model=list[AgentState])
def agent_status(svc: Service = Depends(get_service)):
    return svc.agents()


@router.post("/generate", response_model=GenerateResult)
def generate(req: GenerateRequest, svc: Service = Depends(get_service)):
    return svc.generate(dry_run=req.dry_run, limit=req.limit, lead_id=req.lead_id,
                        review_hooks=req.review_hooks)
