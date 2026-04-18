"""
Scan route.

POST /api/scan  →  trigger a (re-)scan for an existing upload by scan ID.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.models.schemas import ApiResponse, ScanReport
from backend.services import scan_service

router = APIRouter(tags=["scan"])


class ScanRequest(BaseModel):
    scan_id: str


@router.post(
    "/scan",
    response_model=ApiResponse[ScanReport],
    summary="Trigger or re-trigger a scan",
    description="Run (or re-run) the analysis engine for an existing scan record.",
)
def trigger_scan(body: ScanRequest) -> ApiResponse[ScanReport]:
    report = scan_service.run_stub_scan(body.scan_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan '{body.scan_id}' not found.",
        )

    return ApiResponse(
        data=report,
        message="Scan completed",
        success=True,
    )
