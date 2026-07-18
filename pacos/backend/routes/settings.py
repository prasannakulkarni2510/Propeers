"""Operator settings endpoints. Today: the base CV text that grounds every
generated asset. Keeping it editable in the UI matters because a sample or
empty CV is the main reason generated assets invent facts."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_service
from ..models import CvOut, CvUpdateRequest
from ..service import Service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings/cv", response_model=CvOut)
def get_cv(svc: Service = Depends(get_service)):
    content, is_sample = svc.get_cv()
    return CvOut(content=content, is_sample=is_sample)


@router.put("/settings/cv", response_model=CvOut)
def put_cv(req: CvUpdateRequest, svc: Service = Depends(get_service)):
    svc.save_cv(req.content)
    content, is_sample = svc.get_cv()
    return CvOut(content=content, is_sample=is_sample)
