"""
Settings routes.

GET /api/settings  →  retrieve current settings
PUT /api/settings  →  update settings (partial update supported)
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import ApiResponse, AppSettings, AppSettingsUpdate

router = APIRouter(tags=["settings"])

# ---------------------------------------------------------------------------
# In-memory settings store (replace with DB-backed persistence later)
# ---------------------------------------------------------------------------

_current_settings = AppSettings()


@router.get(
    "/settings",
    response_model=ApiResponse[AppSettings],
    summary="Get application settings",
)
def get_settings() -> ApiResponse[AppSettings]:
    return ApiResponse(data=_current_settings, success=True)


@router.put(
    "/settings",
    response_model=ApiResponse[AppSettings],
    summary="Update application settings",
    description="Accepts a partial settings object; only provided fields are updated.",
)
def update_settings(body: AppSettingsUpdate) -> ApiResponse[AppSettings]:
    global _current_settings
    updates = body.model_dump(exclude_none=True, by_alias=False)
    _current_settings = _current_settings.model_copy(update=updates)
    return ApiResponse(
        data=_current_settings,
        message="Settings saved successfully",
        success=True,
    )
