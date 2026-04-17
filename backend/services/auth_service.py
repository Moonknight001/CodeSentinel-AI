"""
GitHub OAuth service.

Handles:
- Building the GitHub authorisation URL
- Exchanging the OAuth ``code`` for a GitHub access token
- Fetching the authenticated user's profile from the GitHub API
- Upserting the user record in PostgreSQL
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User

# ---------------------------------------------------------------------------
# GitHub OAuth configuration (read from environment)
# ---------------------------------------------------------------------------

GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")

# Where GitHub should redirect the user after authorisation
GITHUB_REDIRECT_URI: str = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:8000/api/auth/callback"
)

GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_USER_URL = "https://api.github.com/user"
GITHUB_API_EMAILS_URL = "https://api.github.com/user/emails"

# Scopes requested from GitHub
GITHUB_SCOPES = "read:user user:email"

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def build_github_auth_url(state: str | None = None) -> str:
    """
    Return the GitHub OAuth authorisation URL.

    The ``state`` parameter is optional but recommended for CSRF protection.
    """
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope={GITHUB_SCOPES.replace(' ', '%20')}"
    )
    if state:
        params += f"&state={state}"
    return f"{GITHUB_OAUTH_AUTHORIZE_URL}?{params}"


async def exchange_code_for_token(code: str) -> str:
    """
    Exchange a GitHub OAuth ``code`` for an access token.

    Raises ``ValueError`` if the exchange fails.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GITHUB_OAUTH_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
        )
        response.raise_for_status()
        payload = response.json()

    if "error" in payload:
        raise ValueError(f"GitHub OAuth error: {payload.get('error_description', payload['error'])}")

    access_token: str = payload.get("access_token", "")
    if not access_token:
        raise ValueError("GitHub did not return an access token.")
    return access_token


async def fetch_github_user(access_token: str) -> dict[str, Any]:
    """
    Fetch the authenticated user's profile from the GitHub API.

    If the primary email is not public, a second call is made to the
    ``/user/emails`` endpoint to retrieve it.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        user_resp = await client.get(GITHUB_API_USER_URL, headers=headers)
        user_resp.raise_for_status()
        user_data: dict[str, Any] = user_resp.json()

        # Resolve primary verified email if not exposed in the public profile
        if not user_data.get("email"):
            emails_resp = await client.get(GITHUB_API_EMAILS_URL, headers=headers)
            if emails_resp.status_code == 200:
                for entry in emails_resp.json():
                    if entry.get("primary") and entry.get("verified"):
                        user_data["email"] = entry["email"]
                        break

    return user_data


async def upsert_user(db: AsyncSession, github_user: dict[str, Any], access_token: str) -> User:
    """
    Insert a new ``User`` row or update an existing one (matched by ``github_id``).

    Returns the persisted ``User`` instance.
    """
    github_id: int = int(github_user["id"])

    result = await db.execute(select(User).where(User.github_id == github_id))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        user = User(
            github_id=github_id,
            username=github_user.get("login", ""),
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
            name=github_user.get("name"),
            github_access_token=access_token,
        )
        db.add(user)
    else:
        # Refresh mutable fields on every login
        user.username = github_user.get("login", user.username)
        user.email = github_user.get("email") or user.email
        user.avatar_url = github_user.get("avatar_url") or user.avatar_url
        user.name = github_user.get("name") or user.name
        user.github_access_token = access_token

    await db.commit()
    await db.refresh(user)
    return user
