"""
Unit tests for backend.routes.ws_analyze.

Tests cover:
- WebSocket connection acceptance
- Progress frame sequence (scanning → analyzing → completed)
- Error frames for bad input (empty code, unsupported language, too-long code)
- Optional JWT token resolution (_resolve_user helper)

All database and service calls are mocked so no real DB or OpenAI connection
is required.

Run with:
    python -m pytest backend/tests/test_ws_analyze.py -v
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from backend.routes.ws_analyze import _resolve_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _FakeSubmission:
    id = str(uuid.uuid4())
    status = "completed"
    submitted_at = _now()
    language = "python"
    raw_code = "x = 1"


def _make_scan_result():
    from backend.models.schemas import ScanResult, ScoreResult
    return ScanResult(issues=[], scoreResult=ScoreResult(score=100, label="Excellent"))


def _mock_db_ctx():
    """Return a async-context-manager mock that yields a fake session."""
    fake_db = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=fake_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _collect_frames(ws, max_frames: int = 10) -> list:
    """Receive frames until disconnect or max_frames reached."""
    frames = []
    for _ in range(max_frames):
        try:
            frames.append(json.loads(ws.receive_text()))
        except WebSocketDisconnect:
            break
    return frames


# ---------------------------------------------------------------------------
# _resolve_user helper
# ---------------------------------------------------------------------------


class TestResolveUser:
    def test_none_token_returns_none(self):
        result = asyncio.get_event_loop().run_until_complete(_resolve_user(None))
        assert result is None

    def test_empty_string_returns_none(self):
        result = asyncio.get_event_loop().run_until_complete(_resolve_user(""))
        assert result is None

    def test_invalid_jwt_returns_none(self):
        result = asyncio.get_event_loop().run_until_complete(_resolve_user("not.a.jwt"))
        assert result is None

    def test_valid_jwt_decoded(self):
        from backend.utils.security import create_access_token
        token = create_access_token({"sub": "42"})
        result = asyncio.get_event_loop().run_until_complete(_resolve_user(token))
        assert result == 42

    def test_jwt_missing_sub_returns_none(self):
        from backend.utils.security import create_access_token
        token = create_access_token({"foo": "bar"})
        result = asyncio.get_event_loop().run_until_complete(_resolve_user(token))
        assert result is None


# ---------------------------------------------------------------------------
# WebSocket endpoint (integration-style, using FastAPI TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture
def ws_client():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


@patch("backend.routes.ws_analyze.get_ai_review", new_callable=AsyncMock, return_value=None)
@patch("backend.routes.ws_analyze.analyze_service.run_scan", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.analyze_service.create_submission", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.get_db_session")
def test_ws_full_happy_path(mock_db_ctx, mock_create, mock_run, mock_ai, ws_client):
    mock_db_ctx.return_value = _mock_db_ctx()
    mock_create.return_value = _FakeSubmission()
    mock_run.return_value = _make_scan_result()

    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "x = 1", "language": "python"}))
        frames = _collect_frames(ws)

    stages = [f["stage"] for f in frames]
    assert stages == ["scanning", "analyzing", "completed"]


@patch("backend.routes.ws_analyze.get_ai_review", new_callable=AsyncMock, return_value=None)
@patch("backend.routes.ws_analyze.analyze_service.run_scan", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.analyze_service.create_submission", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.get_db_session")
def test_ws_completed_contains_result(mock_db_ctx, mock_create, mock_run, mock_ai, ws_client):
    mock_db_ctx.return_value = _mock_db_ctx()
    mock_create.return_value = _FakeSubmission()
    mock_run.return_value = _make_scan_result()

    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "x = 1", "language": "python"}))
        frames = _collect_frames(ws)

    completed = next(f for f in frames if f["stage"] == "completed")
    assert "result" in completed
    assert completed["result"]["language"] == "python"


@patch("backend.routes.ws_analyze.get_ai_review", new_callable=AsyncMock, return_value=None)
@patch("backend.routes.ws_analyze.analyze_service.run_scan", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.analyze_service.create_submission", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.get_db_session")
def test_ws_javascript_language(mock_db_ctx, mock_create, mock_run, mock_ai, ws_client):
    mock_db_ctx.return_value = _mock_db_ctx()
    sub = _FakeSubmission()
    sub.language = "javascript"
    mock_create.return_value = sub
    mock_run.return_value = _make_scan_result()

    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "var x = 1;", "language": "javascript"}))
        frames = _collect_frames(ws)

    stages = [f["stage"] for f in frames]
    assert "completed" in stages


def test_ws_empty_code_returns_error(ws_client):
    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "", "language": "python"}))
        frames = _collect_frames(ws)
    assert frames[0]["stage"] == "error"
    assert "empty" in frames[0]["message"].lower()


def test_ws_whitespace_only_code_returns_error(ws_client):
    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "   \n\t  ", "language": "python"}))
        frames = _collect_frames(ws)
    assert frames[0]["stage"] == "error"


def test_ws_unsupported_language_returns_error(ws_client):
    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "select 1", "language": "sql"}))
        frames = _collect_frames(ws)
    assert frames[0]["stage"] == "error"
    msg = frames[0]["message"].lower()
    assert "sql" in msg or "language" in msg


def test_ws_code_too_long_returns_error(ws_client):
    long_code = "x = 1\n" * 20_000  # > 100_000 chars
    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": long_code, "language": "python"}))
        frames = _collect_frames(ws)
    assert frames[0]["stage"] == "error"
    assert "maximum" in frames[0]["message"].lower()


def test_ws_invalid_json_returns_error(ws_client):
    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text("this is not json {{{")
        frames = _collect_frames(ws)
    assert frames[0]["stage"] == "error"


@patch("backend.routes.ws_analyze.get_ai_review", new_callable=AsyncMock, return_value=None)
@patch(
    "backend.routes.ws_analyze.analyze_service.run_scan",
    new_callable=AsyncMock,
    side_effect=RuntimeError("scanner boom"),
)
@patch("backend.routes.ws_analyze.analyze_service.create_submission", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.get_db_session")
def test_ws_scanner_error_returns_error_frame(mock_db_ctx, mock_create, mock_run, mock_ai, ws_client):
    mock_db_ctx.return_value = _mock_db_ctx()
    mock_create.return_value = _FakeSubmission()

    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "x = 1", "language": "python"}))
        frames = _collect_frames(ws)

    stages = [f["stage"] for f in frames]
    assert "error" in stages


@patch("backend.routes.ws_analyze.get_ai_review", new_callable=AsyncMock, return_value=None)
@patch("backend.routes.ws_analyze.analyze_service.run_scan", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.analyze_service.create_submission", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.get_db_session")
def test_ws_scanning_frame_has_message(mock_db_ctx, mock_create, mock_run, mock_ai, ws_client):
    mock_db_ctx.return_value = _mock_db_ctx()
    mock_create.return_value = _FakeSubmission()
    mock_run.return_value = _make_scan_result()

    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "x = 1", "language": "python"}))
        frames = _collect_frames(ws)

    scanning = next(f for f in frames if f["stage"] == "scanning")
    assert "message" in scanning
    assert scanning["message"]


@patch("backend.routes.ws_analyze.get_ai_review", new_callable=AsyncMock, return_value=None)
@patch("backend.routes.ws_analyze.analyze_service.run_scan", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.analyze_service.create_submission", new_callable=AsyncMock)
@patch("backend.routes.ws_analyze.get_db_session")
def test_ws_analyzing_frame_has_message(mock_db_ctx, mock_create, mock_run, mock_ai, ws_client):
    mock_db_ctx.return_value = _mock_db_ctx()
    mock_create.return_value = _FakeSubmission()
    mock_run.return_value = _make_scan_result()

    with ws_client.websocket_connect("/api/ws/analyze") as ws:
        ws.send_text(json.dumps({"code": "x = 1", "language": "python"}))
        frames = _collect_frames(ws)

    analyzing = next(f for f in frames if f["stage"] == "analyzing")
    assert "message" in analyzing
    assert analyzing["message"]
