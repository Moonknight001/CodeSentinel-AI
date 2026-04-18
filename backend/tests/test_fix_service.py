"""
Unit tests for backend.services.fix_service.

All tests mock the OpenAI client so no real network calls are made.
The openai module is injected via sys.modules patching (matching the
approach used by test_ai_review_service.py) because AsyncOpenAI is
imported lazily inside the service function.

Run with:
    python -m pytest backend/tests/test_fix_service.py -v
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import fix_service
from backend.services.fix_service import FixResult, get_fixed_code

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_API_KEY = "sk-test-0000000000000000000000000000000000000000000000"

_SAMPLE_CODE = """\
import os
password = "hunter2"
query = "SELECT * FROM users WHERE id = " + user_id
result = eval(user_input)
"""

_SAMPLE_FIXED = """\
import os
password = os.environ["PASSWORD"]  # SECURITY FIX: Hardcoded secret – moved to env var
query = "SELECT * FROM users WHERE id = %s"  # SECURITY FIX: SQL injection – parameterised query
result = None  # SECURITY FIX: Unsafe function – eval removed
"""

_SAMPLE_SUMMARY = (
    "- Line 2: Replaced hardcoded password with env var (Hardcoded Secret)\n"
    "- Line 3: Replaced string concat with parameterised query (SQL Injection)\n"
    "- Line 4: Removed eval() call (Unsafe Function)"
)


def _mock_openai_response(content: str) -> MagicMock:
    """Build a minimal fake ChatCompletion response."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_payload(fixed: str = _SAMPLE_FIXED, summary: str = _SAMPLE_SUMMARY) -> str:
    return json.dumps({"fixed_code": fixed, "summary": summary})


def _make_mock_module(response_content: str) -> MagicMock:
    """Return a fake openai module whose AsyncOpenAI client returns response_content."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(response_content)
    )
    mock_module = MagicMock()
    mock_module.AsyncOpenAI = MagicMock(return_value=mock_client)
    return mock_module, mock_client


# ---------------------------------------------------------------------------
# Returns None when API key is absent
# ---------------------------------------------------------------------------


class TestNoApiKey:
    def test_returns_none_when_api_key_not_set(self):
        with patch.object(fix_service, "_OPENAI_API_KEY", ""):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is None

    def test_returns_none_when_openai_not_installed(self):
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": None}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is None


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_returns_fix_result(self):
        mock_module, _ = _make_mock_module(_make_payload())
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert isinstance(result, FixResult)

    def test_fixed_code_populated(self):
        mock_module, _ = _make_mock_module(_make_payload())
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is not None
        assert result.fixed_code == _SAMPLE_FIXED

    def test_summary_populated(self):
        mock_module, _ = _make_mock_module(_make_payload())
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is not None
        assert result.summary == _SAMPLE_SUMMARY

    def test_javascript_language_accepted(self):
        mock_module, _ = _make_mock_module(_make_payload())
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            js_code = 'const q = `SELECT * FROM users WHERE id = ${userId}`;'
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(js_code, "javascript")
            )
        assert isinstance(result, FixResult)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_returns_none_on_api_exception(self):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))
        mock_module = MagicMock()
        mock_module.AsyncOpenAI = MagicMock(return_value=mock_client)
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is None

    def test_returns_none_on_invalid_json(self):
        mock_module, _ = _make_mock_module("not json at all")
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is None

    def test_returns_none_when_fixed_code_missing(self):
        mock_module, _ = _make_mock_module(json.dumps({"summary": "some summary"}))
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is None

    def test_returns_none_when_fixed_code_empty_string(self):
        mock_module, _ = _make_mock_module(json.dumps({"fixed_code": "   ", "summary": "x"}))
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is None

    def test_empty_summary_gets_default(self):
        mock_module, _ = _make_mock_module(
            json.dumps({"fixed_code": _SAMPLE_FIXED, "summary": ""})
        )
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is not None
        assert result.summary == "Changes applied."

    def test_returns_none_on_empty_response_content(self):
        mock_module, _ = _make_mock_module("")
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                get_fixed_code(_SAMPLE_CODE, "python")
            )
        assert result is None


# ---------------------------------------------------------------------------
# API call parameters
# ---------------------------------------------------------------------------


class TestApiCallParameters:
    def _run(self, code: str, language: str) -> tuple:
        mock_module, mock_client = _make_mock_module(_make_payload())
        with (
            patch.object(fix_service, "_OPENAI_API_KEY", _FAKE_API_KEY),
            patch.dict("sys.modules", {"openai": mock_module}),
        ):
            asyncio.get_event_loop().run_until_complete(get_fixed_code(code, language))
        return mock_client.chat.completions.create.call_args

    def test_json_mode_requested(self):
        call_args = self._run(_SAMPLE_CODE, "python")
        kwargs = call_args.kwargs
        assert kwargs.get("response_format") == {"type": "json_object"}

    def test_messages_include_system_and_user_roles(self):
        call_args = self._run(_SAMPLE_CODE, "python")
        messages = call_args.kwargs.get("messages", [])
        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert "user" in roles

    def test_user_message_includes_language(self):
        call_args = self._run(_SAMPLE_CODE, "python")
        messages = call_args.kwargs.get("messages", [])
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        assert "python" in user_msg.lower()

    def test_user_message_includes_code(self):
        call_args = self._run(_SAMPLE_CODE, "python")
        messages = call_args.kwargs.get("messages", [])
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        assert "hunter2" in user_msg

