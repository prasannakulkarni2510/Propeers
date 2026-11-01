"""Chat assistant endpoint. Conversational only — lead proposals it returns
are written solely through POST /api/leads after operator confirmation."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_service
from fastapi import HTTPException

from ..models import ChatChangeRequest, ChatRecord, ChatRequest, ChatResult
from ..service import Service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResult)
def chat(req: ChatRequest, svc: Service = Depends(get_service)):
    reply, proposal, warnings, llm_used, draft, records, change, image_text = svc.chat(
        [m.model_dump() for m in req.messages], cv_text=req.cv_text, today=req.today)
    return ChatResult(
        reply=reply,
        lead_proposal=proposal,
        draft=draft,
        records=records,
        change=change,
        image_text=image_text,
        warnings=warnings,
        llm_used=llm_used,
        model=svc.cfg.nemotron_model if llm_used else "offline",
    )


@router.post("/chat/apply", response_model=ChatRecord)
def apply_change(req: ChatChangeRequest, svc: Service = Depends(get_service)):
    """Save an update the operator confirmed on a chat change card. Returns
    the lead's new state so the card can show it."""
    try:
        return svc.apply_chat_change(req.model_dump())
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/chat/index")
def chat_index(svc: Service = Depends(get_service)):
    """How much of the operator's data the chat can search semantically."""
    return svc.chat_index_status()
