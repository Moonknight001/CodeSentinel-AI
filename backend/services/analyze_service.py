"""
Analyze service.

Creates and persists ``CodeSubmission`` records in PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.code_submission import CodeSubmission


async def create_submission(
    db: AsyncSession,
    *,
    language: str,
    raw_code: str,
    user_id: int | None = None,
) -> CodeSubmission:
    """
    Persist a new ``CodeSubmission`` with status ``pending`` and return it.

    Parameters
    ----------
    db:
        Active async database session (injected by FastAPI).
    language:
        Normalised lowercase language string (e.g. ``"python"``).
    raw_code:
        The full source code submitted by the caller.
    user_id:
        Primary key of the authenticated ``User``, or ``None`` for anonymous
        requests.
    """
    submission = CodeSubmission(
        language=language,
        raw_code=raw_code,
        user_id=user_id,
        status="pending",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission
