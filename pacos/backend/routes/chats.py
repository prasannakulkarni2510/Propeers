"""Saved chats: the list in the sidebar, and each chat's messages.

One operator, so chats are not per-user. Messages are stored as the UI holds
them; the UI strips images first (they are read once and never stored).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..models import SavedChatIn
from ..service import Service

router = APIRouter(prefix="/api", tags=["chats"])

MAX_CHAT_BYTES = 2_000_000


def _check(messages) -> None:
    if messages is None:
        return
    blob = json.dumps(messages)
    if len(blob) > MAX_CHAT_BYTES:
        raise HTTPException(status_code=413, detail="This chat is too long to save. Start a new one.")
    if "data:image/" in blob:
        raise HTTPException(status_code=422, detail="Images are not stored with a chat.")


@router.get("/chats")
def list_chats(svc: Service = Depends(get_service)):
    return svc.store.list_chats()


@router.post("/chats")
def create_chat(req: SavedChatIn, svc: Service = Depends(get_service)):
    _check(req.messages)
    title = (req.title or "").strip() or "New chat"
    return svc.store.create_chat(title, req.messages or [])


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str, svc: Service = Depends(get_service)):
    chat = svc.store.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.patch("/chats/{chat_id}")
def update_chat(chat_id: str, req: SavedChatIn, svc: Service = Depends(get_service)):
    _check(req.messages)
    if not svc.store.get_chat(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    title = req.title.strip() if req.title is not None else None
    if title == "":
        raise HTTPException(status_code=422, detail="A chat needs a name.")
    return svc.store.update_chat(chat_id, title=title, starred=req.starred,
                                 messages=req.messages)


@router.delete("/chats/{chat_id}")
def delete_chat(chat_id: str, svc: Service = Depends(get_service)):
    if not svc.store.delete_chat(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"ok": True}
