"""
JWT security utilities and the ``get_current_user`` FastAPI dependency.

Environment variables required:
    JWT_SECRET_KEY   A long, random secret used to sign tokens.
    JWT_ALGORITHM    Signing algorithm (default: HS256).
    JWT_EXPIRE_MINUTES  Token lifetime in minutes (default: 60 * 24 = 1440 / 24 h).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db

# ---------------------------------------------------------------------------
# Configuration (read from environment, sensible defaults for development)
# ---------------------------------------------------------------------------

JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-a-long-random-string")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

_bearer_scheme = HTTPBearer(auto_error=True)
_bearer_scheme_optional = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def create_access_token(payload: dict[str, Any]) -> str:
    """
    Encode a JWT access token.

    Adds an ``exp`` claim based on ``JWT_EXPIRE_MINUTES`` unless the caller
    already includes one.
    """
    data = payload.copy()
    if "exp" not in data:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
        data["exp"] = expire
    return jwt.encode(data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT access token.

    Raises ``HTTPException 401`` on any validation failure.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Shared core logic
# ---------------------------------------------------------------------------


async def _resolve_user_from_credentials(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
):
    """
    Validate *credentials* and return the corresponding ``User`` ORM instance.

    Raises ``HTTPException 401`` on any failure.  Extracted so that both
    ``get_current_user`` and ``get_optional_user`` can share the same logic.
    """
    from sqlalchemy import select
    from backend.models.user import User

    payload = decode_access_token(credentials.credentials)

    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing 'sub'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency that validates the Bearer JWT and returns the
    authenticated ``User`` ORM instance.

    Usage::

        @router.get("/protected")
        async def protected(user = Depends(get_current_user)):
            ...
    """
    return await _resolve_user_from_credentials(credentials, db)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Like ``get_current_user`` but returns ``None`` instead of raising 401
    when no Bearer token is provided.

    Use this for endpoints that work for both anonymous and authenticated callers.
    """
    if credentials is None:
        return None
    try:
        return await _resolve_user_from_credentials(credentials, db)
    except HTTPException:
        return None
