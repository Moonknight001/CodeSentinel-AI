"""
Shared utility helpers for the CodeSentinel AI backend.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_file_extension(filename: str) -> str:
    """Return the lowercase file extension including the leading dot."""
    return Path(filename).suffix.lower()


def get_cors_origins() -> list[str]:
    """
    Return the list of allowed CORS origins.

    If the environment variable ``CORS_ORIGINS`` is set (comma-separated),
    those values are used.  Otherwise the default localhost origins are returned.
    """
    from backend.utils.constants import DEFAULT_CORS_ORIGINS

    raw = os.getenv("CORS_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return DEFAULT_CORS_ORIGINS


def build_api_response(data: object, message: str = "Success", success: bool = True) -> dict:
    """
    Build a standardised API response envelope that matches the frontend
    ``ApiResponse<T>`` TypeScript interface.
    """
    return {
        "data": data,
        "message": message,
        "success": success,
    }
