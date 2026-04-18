"""
Analyze service.

Creates and persists ``CodeSubmission`` records in PostgreSQL and
runs the regex-based security scanner on the submitted code.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.code_submission import CodeSubmission
from backend.models.schemas import ScanIssue, ScanResult
from backend.services.scanner import scan_code


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


async def run_scan(
    db: AsyncSession,
    submission: CodeSubmission,
) -> ScanResult:
    """
    Run the regex-based vulnerability scanner on *submission* and persist
    the updated status back to the database.

    The submission status is set to ``"completed"`` on success or
    ``"failed"`` if an unexpected error occurs.

    Parameters
    ----------
    db:
        Active async database session.
    submission:
        ORM instance previously created by :func:`create_submission`.

    Returns
    -------
    ScanResult
        Pydantic model containing the list of vulnerability findings.
    """
    try:
        raw_result = scan_code(submission.raw_code, submission.language)
        submission.status = "completed"
    except Exception:
        submission.status = "failed"
        db.add(submission)
        await db.commit()
        raise

    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return ScanResult(
        issues=[
            ScanIssue(
                type=issue.type,
                line=issue.line,
                severity=issue.severity,
                message=issue.message,
            )
            for issue in raw_result.issues
        ]
    )
