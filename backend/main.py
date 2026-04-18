"""
CodeSentinel AI – FastAPI application entry point.

Run in development:
    uvicorn backend.main:app --reload --port 8000

Environment variables (all optional):
    CORS_ORIGINS   Comma-separated list of allowed frontend origins.
                   Defaults to http://localhost:3000.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import health, upload, scan, reports, settings, auth, analyze, fix, github, ws_analyze
from backend.utils.constants import API_PREFIX, APP_DESCRIPTION, APP_NAME, APP_VERSION
from backend.utils.helpers import get_cors_origins

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS – allow the Next.js frontend to communicate with the backend
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(upload.router, prefix=API_PREFIX)
app.include_router(scan.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(analyze.router, prefix=API_PREFIX)
app.include_router(fix.router, prefix=API_PREFIX)
app.include_router(github.router, prefix=API_PREFIX)
app.include_router(ws_analyze.router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Root redirect (convenience – navigating to / in the browser)
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "docs": f"{API_PREFIX}/docs",
        "health": f"{API_PREFIX}/health",
    }
