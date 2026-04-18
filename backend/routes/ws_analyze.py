"""
WebSocket endpoint for real-time code analysis progress (Prompt 14).

WS  /api/ws/analyze

Protocol
--------
The client sends **one** JSON message:

    {"code": "<source>", "language": "python"|"javascript"}

The server replies with a sequence of JSON progress frames:

    {"stage": "scanning",  "message": "Running security scanner…"}
    {"stage": "analyzing", "message": "Running AI review…"}
    {"stage": "completed", "result": <AnalyzeResponse>}

On any error the server sends:

    {"stage": "error", "message": "<human-readable description>"}

and immediately closes the connection.

The WebSocket path intentionally sits *outside* the normal REST prefix so
that it is easy to proxy separately (e.g. ``/api/ws/analyze`` via nginx
``proxy_pass`` with ``Upgrade`` headers).

Authentication is **optional** — the caller may pass a JWT via the
``token`` query parameter (``?token=<jwt>``).  When provided and valid
the submission is linked to the authenticated user's account; anonymous
connections still work.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db_session
from backend.models.schemas import (
    AnalyzeResponse,
    ScanStatus,
    SupportedLanguage,
)
from backend.services import analyze_service
from backend.services.ai_review_service import get_ai_review
from backend.utils.security import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAX_CODE_CHARS = 100_000


async def _send(ws: WebSocket, payload: dict[str, Any]) -> None:
    """Send a JSON frame to the connected client (best-effort)."""
    try:
        await ws.send_text(json.dumps(payload))
    except Exception:
        pass  # client may have disconnected


async def _resolve_user(token: str | None) -> int | None:
    """Return the user's primary-key integer from a JWT, or ``None``."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/analyze")
async def ws_analyze(
    websocket: WebSocket,
    token: str | None = None,
) -> None:
    """
    Stream analysis progress over a WebSocket connection.

    The optional ``token`` query-parameter accepts a JWT so that
    submissions can be associated with an authenticated user account
    without requiring HTTP headers (which browsers do not support for
    the native WebSocket API).
    """
    await websocket.accept()

    try:
        # ------------------------------------------------------------------
        # 1. Read and validate the single incoming message
        # ------------------------------------------------------------------
        try:
            raw = await websocket.receive_text()
            body: dict[str, Any] = json.loads(raw)
        except (WebSocketDisconnect, json.JSONDecodeError) as exc:
            await _send(
                websocket,
                {"stage": "error", "message": "Invalid or missing request payload."},
            )
            await websocket.close(code=1003)
            return

        code: str = body.get("code", "")
        lang_raw: str = body.get("language", "")

        # Validate language
        try:
            language = SupportedLanguage(lang_raw)
        except ValueError:
            await _send(
                websocket,
                {
                    "stage": "error",
                    "message": (
                        f"Unsupported language '{lang_raw}'. "
                        "Must be 'python' or 'javascript'."
                    ),
                },
            )
            await websocket.close(code=1003)
            return

        # Validate code
        if not code.strip():
            await _send(
                websocket,
                {"stage": "error", "message": "Code must not be empty."},
            )
            await websocket.close(code=1003)
            return

        if len(code) > _MAX_CODE_CHARS:
            await _send(
                websocket,
                {
                    "stage": "error",
                    "message": (
                        f"Code exceeds the maximum allowed length of "
                        f"{_MAX_CODE_CHARS:,} characters."
                    ),
                },
            )
            await websocket.close(code=1003)
            return

        # ------------------------------------------------------------------
        # 2. Resolve optional authenticated user
        # ------------------------------------------------------------------
        user_id = await _resolve_user(token)

        # ------------------------------------------------------------------
        # 3. Stage 1 — SCANNING
        # ------------------------------------------------------------------
        await _send(
            websocket,
            {
                "stage": "scanning",
                "message": "Running security scanner…",
            },
        )

        async with get_db_session() as db:
            submission = await analyze_service.create_submission(
                db,
                language=language.value,
                raw_code=code,
                user_id=user_id,
            )

            try:
                scan_result = await analyze_service.run_scan(db, submission)
            except Exception as exc:
                logger.exception("Scanner error during WebSocket analysis")
                await _send(
                    websocket,
                    {
                        "stage": "error",
                        "message": "Scanner encountered an unexpected error.",
                    },
                )
                await websocket.close(code=1011)
                return

        # ------------------------------------------------------------------
        # 4. Stage 2 — ANALYZING (AI review, optional)
        # ------------------------------------------------------------------
        await _send(
            websocket,
            {
                "stage": "analyzing",
                "message": "Running AI security review…",
            },
        )

        ai_review = await get_ai_review(
            code,
            language.value,
            scan_result.issues,
        )

        # ------------------------------------------------------------------
        # 5. Stage 3 — COMPLETED
        # ------------------------------------------------------------------
        issue_count = len(scan_result.issues)
        result = AnalyzeResponse(
            submissionId=str(submission.id),
            language=language,
            status=ScanStatus(submission.status),
            submittedAt=submission.submitted_at,
            scanResult=scan_result,
            aiReview=ai_review,
            message=(
                f"Scan complete. {issue_count} issue(s) found."
                if issue_count
                else "Scan complete. No issues found."
            ),
        )

        await _send(
            websocket,
            {
                "stage": "completed",
                "message": result.message,
                "result": result.model_dump(mode="json", by_alias=True),
            },
        )

        await websocket.close(code=1000)

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected during analysis")
    except Exception as exc:
        logger.exception("Unexpected error in ws_analyze")
        await _send(
            websocket,
            {"stage": "error", "message": "An unexpected server error occurred."},
        )
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
