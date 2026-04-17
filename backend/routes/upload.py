"""
Upload route.

POST /api/upload  →  accepts a code file, creates a pending scan record,
                     optionally triggers a stub analysis, and returns the
                     scan ID so the frontend can poll for results.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, status

from backend.models.schemas import ApiResponse, ScanStatus, UploadResponse
from backend.services import scan_service
from backend.utils.constants import ACCEPTED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES

router = APIRouter(tags=["upload"])


@router.post(
    "/upload",
    response_model=ApiResponse[UploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a code file for analysis",
)
async def upload_code(file: UploadFile) -> ApiResponse[UploadResponse]:
    """
    Accept a source-code file, validate it, create a pending scan record and
    return the scan ID.

    The frontend can then poll ``GET /api/reports/{scanId}`` for results.
    """
    # --- Validate filename / extension ---
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    if not scan_service.validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type. Accepted extensions: "
                f"{', '.join(sorted(ACCEPTED_EXTENSIONS))}"
            ),
        )

    # --- Validate file size ---
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of 10 MB.",
        )

    # --- Create a pending scan and run the stub analysis ---
    report = scan_service.create_pending_scan(file.filename)
    scan_service.run_stub_scan(report.id)  # synchronous stub; replace with async task later

    return ApiResponse(
        data=UploadResponse(
            scanId=report.id,
            filename=file.filename,
            status=ScanStatus.PENDING,
            message="File uploaded successfully. Analysis is queued.",
        ),
        message="Upload accepted",
        success=True,
    )
