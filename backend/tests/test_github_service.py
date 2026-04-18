"""
Unit tests for backend.services.github_service.

All tests mock httpx.AsyncClient so no real network calls are made.

Run with:
    python -m pytest backend/tests/test_github_service.py -v
"""

from __future__ import annotations

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import github_service
from backend.services.github_service import (
    _file_extension,
    fetch_file_content,
    fetch_repo_tree,
    fetch_user_repos,
)

_FAKE_TOKEN = "gho_test_0000000000000000000000000000000000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status_code: int, body: object) -> MagicMock:
    """Build a minimal fake httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=body)
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        resp.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                f"{status_code}",
                request=MagicMock(),
                response=resp,
            )
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


def _make_client_ctx(response: MagicMock) -> MagicMock:
    """Build a fake async context manager that returns *response* from client.get/post."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# _file_extension helper
# ---------------------------------------------------------------------------


class TestFileExtension:
    def test_py_file(self):
        assert _file_extension("src/app.py") == ".py"

    def test_js_file(self):
        assert _file_extension("lib/index.js") == ".js"

    def test_no_extension(self):
        assert _file_extension("Makefile") == ""

    def test_dotfile(self):
        assert _file_extension(".gitignore") == ".gitignore"

    def test_uppercase_normalised(self):
        assert _file_extension("App.PY") == ".py"


# ---------------------------------------------------------------------------
# fetch_user_repos
# ---------------------------------------------------------------------------


class TestFetchUserRepos:
    _REPOS = [
        {
            "id": 1,
            "name": "myrepo",
            "full_name": "alice/myrepo",
            "description": "A test repo",
            "private": False,
            "html_url": "https://github.com/alice/myrepo",
            "language": "Python",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
            "stargazers_count": 5,
        }
    ]

    def test_returns_list(self):
        ctx = _make_client_ctx(_make_response(200, self._REPOS))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_user_repos(_FAKE_TOKEN)
            )
        assert isinstance(result, list)
        assert len(result) == 1

    def test_repo_fields_mapped(self):
        ctx = _make_client_ctx(_make_response(200, self._REPOS))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_user_repos(_FAKE_TOKEN)
            )
        repo = result[0]
        assert repo["name"] == "myrepo"
        assert repo["fullName"] == "alice/myrepo"
        assert repo["htmlUrl"] == "https://github.com/alice/myrepo"
        assert repo["language"] == "Python"
        assert repo["stargazersCount"] == 5

    def test_raises_on_http_error(self):
        ctx = _make_client_ctx(_make_response(403, {}))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            with pytest.raises(ValueError, match="403"):
                asyncio.get_event_loop().run_until_complete(
                    fetch_user_repos(_FAKE_TOKEN)
                )

    def test_empty_list_ok(self):
        ctx = _make_client_ctx(_make_response(200, []))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_user_repos(_FAKE_TOKEN)
            )
        assert result == []


# ---------------------------------------------------------------------------
# fetch_repo_tree
# ---------------------------------------------------------------------------


class TestFetchRepoTree:
    _TREE_RESPONSE = {
        "tree": [
            {"type": "tree", "path": "src"},
            {"type": "blob", "path": "src/app.py"},
            {"type": "blob", "path": "src/utils.py"},
            {"type": "blob", "path": "src/index.js"},
            {"type": "blob", "path": "README.md"},
            {"type": "blob", "path": "Makefile"},
        ]
    }

    def test_filters_to_py_and_js(self):
        ctx = _make_client_ctx(_make_response(200, self._TREE_RESPONSE))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_repo_tree(_FAKE_TOKEN, "alice", "myrepo")
            )
        paths = [f["path"] for f in result]
        assert "src/app.py" in paths
        assert "src/utils.py" in paths
        assert "src/index.js" in paths
        assert "README.md" not in paths
        assert "Makefile" not in paths

    def test_language_field_set(self):
        ctx = _make_client_ctx(_make_response(200, self._TREE_RESPONSE))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_repo_tree(_FAKE_TOKEN, "alice", "myrepo")
            )
        py_files = [f for f in result if f["path"].endswith(".py")]
        js_files = [f for f in result if f["path"].endswith(".js")]
        assert all(f["language"] == "python" for f in py_files)
        assert all(f["language"] == "javascript" for f in js_files)

    def test_name_field_is_basename(self):
        ctx = _make_client_ctx(_make_response(200, self._TREE_RESPONSE))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_repo_tree(_FAKE_TOKEN, "alice", "myrepo")
            )
        entry = next(f for f in result if f["path"] == "src/app.py")
        assert entry["name"] == "app.py"

    def test_excludes_tree_entries(self):
        ctx = _make_client_ctx(_make_response(200, self._TREE_RESPONSE))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_repo_tree(_FAKE_TOKEN, "alice", "myrepo")
            )
        assert all(f["path"] != "src" for f in result)

    def test_raises_on_http_error(self):
        ctx = _make_client_ctx(_make_response(404, {}))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            with pytest.raises(ValueError, match="404"):
                asyncio.get_event_loop().run_until_complete(
                    fetch_repo_tree(_FAKE_TOKEN, "alice", "myrepo")
                )

    def test_empty_tree_returns_empty_list(self):
        ctx = _make_client_ctx(_make_response(200, {"tree": []}))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_repo_tree(_FAKE_TOKEN, "alice", "myrepo")
            )
        assert result == []


# ---------------------------------------------------------------------------
# fetch_file_content
# ---------------------------------------------------------------------------


class TestFetchFileContent:
    def _make_contents_response(self, content_str: str, size: int = 0) -> MagicMock:
        encoded = base64.b64encode(content_str.encode()).decode()
        # GitHub adds newlines in the base64 payload
        encoded_with_newlines = "\n".join(encoded[i:i+60] for i in range(0, len(encoded), 60))
        return _make_response(
            200,
            {
                "encoding": "base64",
                "content": encoded_with_newlines + "\n",
                "size": size or len(content_str),
                "path": "src/app.py",
            },
        )

    def test_returns_decoded_python_content(self):
        code = "import os\nprint(os.getenv('KEY'))\n"
        ctx = _make_client_ctx(self._make_contents_response(code))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_file_content(_FAKE_TOKEN, "alice", "myrepo", "src/app.py")
            )
        assert result["content"] == code
        assert result["language"] == "python"
        assert result["path"] == "src/app.py"

    def test_returns_decoded_js_content(self):
        code = "const x = 1;\nconsole.log(x);\n"
        ctx = _make_client_ctx(self._make_contents_response(code))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_file_content(_FAKE_TOKEN, "alice", "myrepo", "lib/index.js")
            )
        assert result["language"] == "javascript"

    def test_raises_for_unsupported_extension(self):
        with pytest.raises(ValueError, match="Unsupported file extension"):
            asyncio.get_event_loop().run_until_complete(
                fetch_file_content(_FAKE_TOKEN, "alice", "myrepo", "README.md")
            )

    def test_raises_on_http_error(self):
        ctx = _make_client_ctx(_make_response(404, {}))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            with pytest.raises(ValueError, match="404"):
                asyncio.get_event_loop().run_until_complete(
                    fetch_file_content(_FAKE_TOKEN, "alice", "myrepo", "src/app.py")
                )

    def test_raises_for_empty_encoding(self):
        resp = _make_response(200, {"encoding": "", "content": "", "size": 999999, "path": "big.py"})
        ctx = _make_client_ctx(resp)
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            with pytest.raises(ValueError, match="too large"):
                asyncio.get_event_loop().run_until_complete(
                    fetch_file_content(_FAKE_TOKEN, "alice", "myrepo", "big.py")
                )

    def test_size_field_in_result(self):
        code = "x = 1\n"
        ctx = _make_client_ctx(self._make_contents_response(code, size=6))
        with patch("backend.services.github_service.httpx.AsyncClient", return_value=ctx):
            result = asyncio.get_event_loop().run_until_complete(
                fetch_file_content(_FAKE_TOKEN, "alice", "myrepo", "src/app.py")
            )
        assert result["size"] == 6
