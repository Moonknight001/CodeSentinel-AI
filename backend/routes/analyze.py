"""
Analyze route.

POST /api/analyze – accepts raw source code and a language identifier,
                    validates the input, stores a submission record in
                    PostgreSQL and returns the submission ID with its
                    timestamp.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db
from backend.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ApiResponse,
    ScanStatus,
)
from backend.models.user import User
from backend.services import analyze_service
from backend.utils.security import get_optional_user

router = APIRouter(tags=["analyze"])

# Maximum raw-code size enforced at the service layer (characters)
_MAX_CODE_CHARS = 100_000


@router.post(
    "/analyze",
    response_model=ApiResponse[AnalyzeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for security analysis",
    description=(
        "Accepts raw source code and a language identifier, validates the "
        "input, stores a submission record in PostgreSQL with a timestamp, "
        "and returns the submission ID so the caller can poll for results.\n\n"
        "Authentication is **optional** – authenticated users have their "
        "submission linked to their account."
    ),
)
async def analyze(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> ApiResponse[AnalyzeResponse]:
    """
    Validate and persist a code-analysis submission.

    - ``code`` must be a non-empty string up to 100 000 characters.
    - ``language`` must be ``python`` or ``javascript``.
    """
    # Extra server-side length guard (Pydantic's max_length already covers
    # this for JSON bodies, but keeps us safe if the schema changes).
    if len(body.code) > _MAX_CODE_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Code exceeds the maximum allowed length of "
                f"{_MAX_CODE_CHARS:,} characters."
            ),
        )

    user_id = current_user.id if current_user is not None else None

    submission = await analyze_service.create_submission(
        db,
        language=body.language.value,
        raw_code=body.code,
        user_id=user_id,
    )

    return ApiResponse(
        data=AnalyzeResponse(
            submissionId=submission.id,
            language=body.language,
            status=ScanStatus.PENDING,
            submittedAt=submission.submitted_at,
        ),
        message="Code submission accepted. Analysis is queued.",
        success=True,
    )
