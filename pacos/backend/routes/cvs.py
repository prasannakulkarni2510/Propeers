"""Several saved CVs, one in use. The CV in use grounds every message PACOS
writes; the others wait as cards the operator can switch to."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..models import SavedCvIn
from ..service import Service

router = APIRouter(prefix="/api", tags=["cvs"])

MAX_CVS = 12


@router.get("/cvs")
def list_cvs(svc: Service = Depends(get_service)):
    return svc.list_cvs()


@router.post("/cvs")
def create_cv(req: SavedCvIn, svc: Service = Depends(get_service)):
    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="A CV needs some text.")
    if len(svc.list_cvs()) >= MAX_CVS:
        raise HTTPException(status_code=422, detail=f"Up to {MAX_CVS} CVs. Delete one first.")
    name = (req.name or "").strip() or "My CV"
    return svc.create_cv(name, req.content, req.color or "")


@router.patch("/cvs/{cv_id}")
def update_cv(cv_id: str, req: SavedCvIn, svc: Service = Depends(get_service)):
    if req.content is not None and not req.content.strip():
        raise HTTPException(status_code=422, detail="A CV needs some text.")
    name = req.name.strip() if req.name is not None else None
    if name == "":
        raise HTTPException(status_code=422, detail="A CV needs a name.")
    try:
        return svc.update_cv(cv_id, name=name, content=req.content, color=req.color)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cvs/{cv_id}/use")
def use_cv(cv_id: str, svc: Service = Depends(get_service)):
    try:
        return svc.use_cv(cv_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/cvs/{cv_id}")
def delete_cv(cv_id: str, svc: Service = Depends(get_service)):
    try:
        svc.delete_cv(cv_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}
