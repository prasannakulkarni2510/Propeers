"""Operator settings endpoints. Today: the base CV text that grounds every
generated asset. Keeping it editable in the UI matters because a sample or
empty CV is the main reason generated assets invent facts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from pacos.cv_extract import MAX_BYTES, CvExtractError, extract_cv_text

from ..deps import get_service
from ..models import CvExtractOut, CvOut, CvUpdateRequest
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


@router.post("/settings/cv/extract", response_model=CvExtractOut)
async def extract_cv(request: Request, filename: str = ""):
    """Extract text from an uploaded CV (raw file bytes in the body). Writes
    nothing: the editor shows the text and the operator saves it with PUT."""
    data = await request.body()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 5 MB.")
    try:
        content = extract_cv_text(filename, data)
    except CvExtractError as e:
        raise HTTPException(422, str(e)) from e
    return CvExtractOut(content=content, filename=filename)
