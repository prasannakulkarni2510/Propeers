"""Per-lead generated asset endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_service
from ..models import AssetsOut, RegenerateAssetRequest
from ..service import Service

router = APIRouter(prefix="/api", tags=["assets"])


@router.get("/assets/{lead_id}", response_model=AssetsOut)
def get_assets(lead_id: str, svc: Service = Depends(get_service)):
    data = svc.assets_for(lead_id)
    if data is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return data


@router.post("/assets/{lead_id}/regenerate", response_model=AssetsOut)
def regenerate_asset(lead_id: str, req: RegenerateAssetRequest,
                     svc: Service = Depends(get_service)):
    try:
        data = svc.regenerate_asset(lead_id, req.asset, dry_run=req.dry_run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if data is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return data
