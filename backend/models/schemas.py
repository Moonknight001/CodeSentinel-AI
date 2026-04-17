"""
Pydantic schemas (request/response models) for CodeSentinel AI.

These mirror the TypeScript interfaces defined in the frontend's
``services/api.ts`` so that the two layers remain in sync.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Generic envelope
# ---------------------------------------------------------------------------

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """Standard response envelope – matches frontend ``ApiResponse<T>``."""

    data: DataT
    message: str = "Success"
    success: bool = True


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportFormat(str, Enum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Vulnerability
# ---------------------------------------------------------------------------


class Vulnerability(BaseModel):
    id: str
    title: str
    description: str
    severity: SeverityLevel
    line: int
    column: Optional[int] = None
    code_snippet: Optional[str] = Field(None, alias="codeSnippet")
    recommendation: str

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Report summary
# ---------------------------------------------------------------------------


class ReportSummary(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    security_score: int = Field(100, alias="securityScore")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Scan report
# ---------------------------------------------------------------------------


class ScanReport(BaseModel):
    id: str
    filename: str
    language: str
    scanned_at: str = Field(..., alias="scannedAt")
    status: ScanStatus
    vulnerabilities: List[Vulnerability] = []
    summary: ReportSummary = Field(default_factory=ReportSummary)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    scan_id: str = Field(..., alias="scanId")
    filename: str
    status: ScanStatus = ScanStatus.PENDING
    message: str = "File uploaded successfully. Analysis is queued."

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


class DashboardStats(BaseModel):
    total_scans: int = Field(0, alias="totalScans")
    total_vulnerabilities: int = Field(0, alias="totalVulnerabilities")
    critical_issues: int = Field(0, alias="criticalIssues")
    resolved_issues: int = Field(0, alias="resolvedIssues")
    recent_reports: List[ScanReport] = Field([], alias="recentReports")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class AppSettings(BaseModel):
    notifications: bool = True
    auto_scan: bool = Field(False, alias="autoScan")
    report_format: ReportFormat = Field(ReportFormat.PDF, alias="reportFormat")
    theme: Theme = Theme.LIGHT
    api_key: Optional[str] = Field(None, alias="apiKey")

    model_config = {"populate_by_name": True}


class AppSettingsUpdate(BaseModel):
    """Partial settings update – all fields are optional."""

    notifications: Optional[bool] = None
    auto_scan: Optional[bool] = Field(None, alias="autoScan")
    report_format: Optional[ReportFormat] = Field(None, alias="reportFormat")
    theme: Optional[Theme] = None
    api_key: Optional[str] = Field(None, alias="apiKey")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    timestamp: str


# ---------------------------------------------------------------------------
# Auth / User
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    """Public user profile returned by /api/auth/me."""

    id: int
    github_id: int = Field(..., alias="githubId")
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    name: Optional[str] = None
    created_at: datetime = Field(..., alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class TokenResponse(BaseModel):
    """JWT token envelope returned after a successful OAuth callback."""

    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field("bearer", alias="tokenType")
    user: UserResponse

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Code analysis
# ---------------------------------------------------------------------------


class SupportedLanguage(str, Enum):
    """Languages accepted by the /analyze endpoint."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=100_000,
        description="Raw source code to analyse (max 100 000 characters).",
        alias="code",
    )
    language: SupportedLanguage = Field(
        ...,
        description="Programming language of the submitted code.",
    )

    model_config = {"populate_by_name": True}


class AnalyzeResponse(BaseModel):
    """Response returned by POST /api/analyze."""

    submission_id: str = Field(..., alias="submissionId")
    language: SupportedLanguage
    status: ScanStatus
    submitted_at: datetime = Field(..., alias="submittedAt")
    message: str = "Code submission accepted. Analysis is queued."

    model_config = {"populate_by_name": True, "from_attributes": True}

