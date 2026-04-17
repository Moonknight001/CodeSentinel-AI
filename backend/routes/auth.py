"""
Auth routes.

GET  /api/auth/login     – redirect the browser to the GitHub OAuth consent page
GET  /api/auth/callback  – receive the OAuth code, exchange it, store the user,
                           return a JWT
GET  /api/auth/me        – return the profile of the currently authenticated user
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db
from backend.models.schemas import ApiResponse, TokenResponse, UserResponse
from backend.models.user import User
from backend.services import auth_service
from backend.utils.security import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# /login
# ---------------------------------------------------------------------------


@router.get(
    "/login",
    summary="Initiate GitHub OAuth login",
    description=(
        "Redirects the user's browser to the GitHub OAuth authorisation page. "
        "A random ``state`` value is generated for CSRF protection."
    ),
    status_code=status.HTTP_302_FOUND,
)
def login() -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    auth_url = auth_service.build_github_auth_url(state=state)
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


# ---------------------------------------------------------------------------
# /callback
# ---------------------------------------------------------------------------


@router.get(
    "/callback",
    response_model=ApiResponse[TokenResponse],
    summary="GitHub OAuth callback",
    description=(
        "GitHub redirects here after the user authorises the app. "
        "The ``code`` is exchanged for an access token, the user is fetched "
        "from the GitHub API, upserted in PostgreSQL, and a JWT is returned."
    ),
)
async def callback(
    code: str = Query(..., description="OAuth authorisation code from GitHub"),
    state: str | None = Query(None, description="CSRF state parameter"),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth error: {error}",
        )

    try:
        github_token = await auth_service.exchange_code_for_token(code)
        github_user = await auth_service.fetch_github_user(github_token)
        user = await auth_service.upsert_user(db, github_user, github_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to complete GitHub authentication.",
        ) from exc

    jwt_token = create_access_token({"sub": str(user.id)})
    user_response = UserResponse.model_validate(user)

    return ApiResponse(
        data=TokenResponse(
            accessToken=jwt_token,
            tokenType="bearer",
            user=user_response,
        ),
        message="Authentication successful",
        success=True,
    )


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user. Requires a valid Bearer JWT.",
)
async def me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    return ApiResponse(
        data=UserResponse.model_validate(current_user),
        message="User profile retrieved",
        success=True,
    )
