"""
GitHub integration service for CodeSentinel AI (Prompt 13).

Provides helpers that call the GitHub REST API v3 on behalf of an
authenticated user, using the OAuth access token stored in the ``User``
ORM model:

* :func:`fetch_user_repos`  — list the user's repositories (up to 50,
  sorted by most recently updated).
* :func:`fetch_repo_tree`   — return all Python and JavaScript files in a
  repository's default branch as a flat list, using the Git Trees API.
* :func:`fetch_file_content` — decode and return the content of a single
  file using the Contents API.

Design principles
-----------------
* **Resilient** — network errors and unexpected API responses are caught
  and re-raised as ``ValueError`` so the caller (FastAPI endpoint) can
  convert them to friendly HTTP error responses.
* **Focused** — the tree is filtered to only ``*.py`` and ``*.js`` files
  and capped at ``_MAX_TREE_FILES`` entries so responses remain small.
* **No new dependencies** — uses ``httpx``, which is already in the
  requirements (needed by ``auth_service``).
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

# Maximum number of filtered files returned from the tree endpoint
_MAX_TREE_FILES = 200

# File extensions that the scanner supports
_SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
}


def _github_headers(token: str) -> dict[str, str]:
    """Standard GitHub API v3 headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def fetch_user_repos(token: str) -> list[dict[str, Any]]:
    """
    Return a list of the authenticated user's repositories.

    Fetches up to 50 repositories sorted by the most recently pushed to.
    Both personal and organisation repos that the token has access to are
    returned.

    Parameters
    ----------
    token:
        The user's GitHub OAuth access token.

    Returns
    -------
    list of dicts with keys: id, name, full_name, description, private,
    html_url, language, default_branch, updated_at, stargazers_count.

    Raises
    ------
    ValueError
        On HTTP error or unexpected response shape.
    """
    url = f"{GITHUB_API_BASE}/user/repos"
    params = {"sort": "pushed", "per_page": 50, "type": "owner"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_github_headers(token), params=params)
            response.raise_for_status()
            repos: list[dict[str, Any]] = response.json()
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            f"GitHub API returned {exc.response.status_code} when listing repositories."
        ) from exc
    except httpx.RequestError as exc:
        raise ValueError(f"Network error fetching repositories: {exc}") from exc

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "fullName": r["full_name"],
            "description": r.get("description"),
            "private": r.get("private", False),
            "htmlUrl": r["html_url"],
            "language": r.get("language"),
            "defaultBranch": r.get("default_branch", "main"),
            "updatedAt": r.get("updated_at"),
            "stargazersCount": r.get("stargazers_count", 0),
        }
        for r in repos
    ]


async def fetch_repo_tree(
    token: str, owner: str, repo: str
) -> list[dict[str, str]]:
    """
    Return all Python and JavaScript source files in a repository.

    Uses the Git Trees API with ``recursive=1`` to fetch the full file
    tree in a single request.  The result is filtered to ``.py`` and
    ``.js`` files only and capped at :data:`_MAX_TREE_FILES`.

    Parameters
    ----------
    token:
        The user's GitHub OAuth access token.
    owner:
        Repository owner (username or organisation login).
    repo:
        Repository name (without the owner prefix).

    Returns
    -------
    list of dicts with keys: ``path``, ``name``, ``language``.

    Raises
    ------
    ValueError
        On HTTP error, missing tree, or unexpected response shape.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/HEAD"
    params = {"recursive": "1"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=_github_headers(token), params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            f"GitHub API returned {exc.response.status_code} fetching tree for {owner}/{repo}."
        ) from exc
    except httpx.RequestError as exc:
        raise ValueError(f"Network error fetching repository tree: {exc}") from exc

    tree_items: list[dict[str, Any]] = data.get("tree", [])

    files: list[dict[str, str]] = []
    for item in tree_items:
        if item.get("type") != "blob":
            continue
        path: str = item.get("path", "")
        ext = _file_extension(path)
        lang = _SUPPORTED_EXTENSIONS.get(ext)
        if lang is None:
            continue
        files.append(
            {
                "path": path,
                "name": path.rsplit("/", 1)[-1],
                "language": lang,
            }
        )
        if len(files) >= _MAX_TREE_FILES:
            break

    return files


async def fetch_file_content(
    token: str, owner: str, repo: str, path: str
) -> dict[str, Any]:
    """
    Fetch and decode the content of a single file from a repository.

    Uses the Contents API.  Only files whose extension is ``.py`` or
    ``.js`` are accepted; others raise ``ValueError``.

    Parameters
    ----------
    token:
        The user's GitHub OAuth access token.
    owner:
        Repository owner (username or organisation login).
    repo:
        Repository name.
    path:
        File path within the repository (e.g. ``src/app.py``).

    Returns
    -------
    dict with keys: ``path``, ``content`` (decoded string),
    ``language``, ``size`` (bytes).

    Raises
    ------
    ValueError
        If the file extension is unsupported, the file is too large, or
        an HTTP / network error occurs.
    """
    ext = _file_extension(path)
    language = _SUPPORTED_EXTENSIONS.get(ext)
    if language is None:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            "Only .py (Python) and .js (JavaScript) files are supported."
        )

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_github_headers(token))
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            f"GitHub API returned {exc.response.status_code} fetching {path}."
        ) from exc
    except httpx.RequestError as exc:
        raise ValueError(f"Network error fetching file content: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Unexpected response shape for {path}.")

    encoding: str = data.get("encoding", "")
    raw_content: str = data.get("content", "")
    size: int = data.get("size", 0)

    # GitHub returns base64-encoded content with newlines for the Contents API
    if encoding == "base64":
        try:
            decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
        except Exception as exc:
            raise ValueError(f"Failed to decode base64 content for {path}: {exc}") from exc
    elif encoding == "":
        # Large files are not inlined; GitHub returns a download_url instead.
        raise ValueError(
            f"File '{path}' is too large to be fetched inline via the Contents API. "
            "Try a smaller file."
        )
    else:
        raise ValueError(f"Unsupported encoding '{encoding}' for file '{path}'.")

    return {
        "path": path,
        "content": decoded,
        "language": language,
        "size": size,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _file_extension(path: str) -> str:
    """Return the lowercase file extension including the dot, e.g. '.py'."""
    dot_idx = path.rfind(".")
    if dot_idx == -1:
        return ""
    return path[dot_idx:].lower()
