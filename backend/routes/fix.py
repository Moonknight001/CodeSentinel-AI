"""
Fix route.

POST /api/fix – accepts raw source code and a language identifier, sends it
                to the AI auto-fix service, and returns the original code
                alongside the corrected version plus a change summary.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import ApiResponse, FixRequest, FixResponse
from backend.services.fix_service import get_fixed_code

router = APIRouter(tags=["fix"])

_MAX_CODE_CHARS = 100_000


@router.post(
    "/fix",
    response_model=ApiResponse[FixResponse],
    status_code=status.HTTP_200_OK,
    summary="Auto-fix security vulnerabilities in code",
    description=(
        "Accepts raw source code and a language identifier, sends the code "
        "to the AI auto-fix engine, and returns a security-hardened rewrite "
        "together with a plain-English summary of every change made.\n\n"
        "Requires ``OPENAI_API_KEY`` to be configured on the server.  "
        "If the AI service is unavailable the endpoint returns the original "
        "code unchanged with a descriptive message."
    ),
)
async def fix_code(body: FixRequest) -> ApiResponse[FixResponse]:
    """
    Auto-fix security vulnerabilities in the submitted source code.

    - ``code`` must be a non-empty string up to 100 000 characters.
    - ``language`` must be ``python`` or ``javascript``.
    """
    if len(body.code) > _MAX_CODE_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Code exceeds the maximum allowed length of "
                f"{_MAX_CODE_CHARS:,} characters."
            ),
        )

    fix_result = await get_fixed_code(body.code, body.language.value)

    if fix_result is None:
        # AI service unavailable – return the original code unchanged so
        # the frontend can still show something meaningful.
        return ApiResponse(
            data=FixResponse(
                originalCode=body.code,
                fixedCode=body.code,
                summary=(
                    "The AI fix service is currently unavailable "
                    "(OPENAI_API_KEY not configured or API error). "
                    "The original code is shown unchanged."
                ),
            ),
            message="AI fix service unavailable – original code returned.",
            success=False,
        )

    return ApiResponse(
        data=FixResponse(
            originalCode=body.code,
            fixedCode=fix_result.fixed_code,
            summary=fix_result.summary,
        ),
        message="Code fixed successfully.",
        success=True,
    )
