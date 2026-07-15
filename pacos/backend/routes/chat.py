"""Chat assistant endpoint. Conversational only — lead proposals it returns
are written solely through POST /api/leads after operator confirmation."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_service
from ..models import ChatRequest, ChatResult
from ..service import Service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResult)
def chat(req: ChatRequest, svc: Service = Depends(get_service)):
    reply, proposal, warnings, llm_used = svc.chat([m.model_dump() for m in req.messages])
    return ChatResult(
        reply=reply,
        lead_proposal=proposal,
        warnings=warnings,
        llm_used=llm_used,
        model=svc.cfg.nemotron_model if llm_used else "offline",
    )
