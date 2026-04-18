"""
Health-check route.

GET /api/health  →  returns service status, version, and timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.models.schemas import ApiResponse, HealthResponse
from backend.utils.constants import APP_VERSION

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    summary="Health check",
    description="Returns the current health status and version of the API.",
)
def health_check() -> ApiResponse[HealthResponse]:
    return ApiResponse(
        data=HealthResponse(
            status="ok",
            version=APP_VERSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
        message="Service is healthy",
        success=True,
    )
