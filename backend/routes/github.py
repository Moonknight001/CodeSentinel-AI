"""
GitHub integration routes (Prompt 13).

GET  /api/github/repos                           – list authenticated user's repos
GET  /api/github/repos/{owner}/{repo}/tree       – list Python/JS files in a repo
GET  /api/github/repos/{owner}/{repo}/contents   – fetch & decode a single file

All endpoints require a valid Bearer JWT.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db
from backend.models.schemas import (
    ApiResponse,
    GitHubFileContent,
    GitHubFileEntry,
    GitHubRepo,
)
from backend.models.user import User
from backend.services import github_service
from backend.utils.security import get_current_user

router = APIRouter(prefix="/github", tags=["github"])


# ---------------------------------------------------------------------------
# List repositories
# ---------------------------------------------------------------------------


@router.get(
    "/repos",
    response_model=ApiResponse[list[GitHubRepo]],
    summary="List GitHub repositories",
    description=(
        "Returns up to 50 of the authenticated user's GitHub repositories "
        "sorted by the most recently pushed-to.  Requires a valid Bearer JWT. "
        "The OAuth token must have the ``public_repo`` scope (granted at login)."
    ),
)
async def list_repos(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[GitHubRepo]]:
    try:
        repos_raw = await github_service.fetch_user_repos(current_user.github_access_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    repos = [GitHubRepo(**r) for r in repos_raw]
    return ApiResponse(
        data=repos,
        message=f"{len(repos)} repositor{'ies' if len(repos) != 1 else 'y'} found.",
        success=True,
    )


# ---------------------------------------------------------------------------
# Repository file tree
# ---------------------------------------------------------------------------


@router.get(
    "/repos/{owner}/{repo}/tree",
    response_model=ApiResponse[list[GitHubFileEntry]],
    summary="List Python and JavaScript files in a repository",
    description=(
        "Returns a flat list of every ``.py`` and ``.js`` file in the "
        "repository's default branch (up to 200 files).  Uses the Git Trees "
        "API with ``recursive=1`` to fetch the full tree in one request."
    ),
)
async def list_repo_files(
    owner: str,
    repo: str,
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[GitHubFileEntry]]:
    try:
        files_raw = await github_service.fetch_repo_tree(
            current_user.github_access_token, owner, repo
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    files = [GitHubFileEntry(**f) for f in files_raw]
    return ApiResponse(
        data=files,
        message=f"{len(files)} file{'s' if len(files) != 1 else ''} found.",
        success=True,
    )


# ---------------------------------------------------------------------------
# File content
# ---------------------------------------------------------------------------


@router.get(
    "/repos/{owner}/{repo}/contents",
    response_model=ApiResponse[GitHubFileContent],
    summary="Fetch the content of a single file",
    description=(
        "Decodes and returns the content of a ``.py`` or ``.js`` file from "
        "the repository.  The ``path`` query parameter must be the full "
        "path as returned by the tree endpoint (e.g. ``src/app.py``)."
    ),
)
async def get_file_content(
    owner: str,
    repo: str,
    path: str = Query(..., description="Full file path within the repository"),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[GitHubFileContent]:
    try:
        file_raw = await github_service.fetch_file_content(
            current_user.github_access_token, owner, repo, path
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ApiResponse(
        data=GitHubFileContent(**file_raw),
        message="File content retrieved.",
        success=True,
    )
