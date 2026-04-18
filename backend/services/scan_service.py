"""
Scan service – stub implementation for the analysis engine layer.

In subsequent prompts this will be replaced with real AI-powered analysis.
For now it returns a deterministic placeholder result so the API layer is
fully exercisable end-to-end.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.models.schemas import (
    ReportSummary,
    ScanReport,
    ScanStatus,
    Vulnerability,
    SeverityLevel,
)
from backend.services.scoring_service import compute_score
from backend.utils.constants import ACCEPTED_EXTENSIONS, SUPPORTED_LANGUAGES


def _detect_language(filename: str) -> str:
    """Map a file extension to a human-readable language name."""
    extension_map: dict[str, str] = {
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".py": "Python",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".go": "Go",
        ".rs": "Rust",
        ".php": "PHP",
        ".rb": "Ruby",
    }
    ext = Path(filename).suffix.lower()
    return extension_map.get(ext, "Unknown")


def validate_file_extension(filename: str) -> bool:
    """Return True if the file extension is in the accepted set."""
    ext = Path(filename).suffix.lower()
    return ext in ACCEPTED_EXTENSIONS


def create_pending_scan(filename: str) -> ScanReport:
    """
    Create a new ScanReport in PENDING state and add it to the in-memory store.
    Returns the created report.
    """
    scan_id = str(uuid.uuid4())
    report = ScanReport(
        id=scan_id,
        filename=filename,
        language=_detect_language(filename),
        scannedAt=datetime.now(timezone.utc).isoformat(),
        status=ScanStatus.PENDING,
        vulnerabilities=[],
        summary=ReportSummary(),
    )
    _store[scan_id] = report
    return report


def run_stub_scan(scan_id: str) -> Optional[ScanReport]:
    """
    Execute a stub scan for an existing report.

    This returns a placeholder result with one sample vulnerability of each
    major severity level.  It will be replaced by the real AI analysis engine
    in a later prompt.
    """
    report = _store.get(scan_id)
    if report is None:
        return None

    # Mark as in-progress
    report = report.model_copy(update={"status": ScanStatus.IN_PROGRESS})

    # Placeholder vulnerabilities
    vulns: list[Vulnerability] = [
        Vulnerability(
            id=str(uuid.uuid4()),
            title="SQL Injection (placeholder)",
            description="User-supplied input is concatenated directly into an SQL query.",
            severity=SeverityLevel.CRITICAL,
            line=42,
            column=8,
            codeSnippet='query = "SELECT * FROM users WHERE id = " + user_id',
            recommendation="Use parameterised queries or an ORM.",
        ),
        Vulnerability(
            id=str(uuid.uuid4()),
            title="Hardcoded Secret (placeholder)",
            description="A secret key is hardcoded in the source file.",
            severity=SeverityLevel.HIGH,
            line=7,
            recommendation="Move secrets to environment variables.",
        ),
        Vulnerability(
            id=str(uuid.uuid4()),
            title="Insecure Dependency (placeholder)",
            description="An outdated dependency with known CVEs is in use.",
            severity=SeverityLevel.MEDIUM,
            line=1,
            recommendation="Upgrade to the latest patched version.",
        ),
    ]

    summary = ReportSummary(
        total=len(vulns),
        critical=sum(1 for v in vulns if v.severity == SeverityLevel.CRITICAL),
        high=sum(1 for v in vulns if v.severity == SeverityLevel.HIGH),
        medium=sum(1 for v in vulns if v.severity == SeverityLevel.MEDIUM),
        low=sum(1 for v in vulns if v.severity == SeverityLevel.LOW),
        info=sum(1 for v in vulns if v.severity == SeverityLevel.INFO),
        securityScore=compute_score([v.severity.value for v in vulns])[0],
    )

    report = report.model_copy(
        update={
            "status": ScanStatus.COMPLETED,
            "vulnerabilities": vulns,
            "summary": summary,
            "scannedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    _store[scan_id] = report
    return report


def get_scan(scan_id: str) -> Optional[ScanReport]:
    """Return a report by ID, or None if not found."""
    return _store.get(scan_id)


def get_all_scans() -> list[ScanReport]:
    """Return all reports, newest first."""
    return sorted(_store.values(), key=lambda r: r.scanned_at, reverse=True)


def get_dashboard_stats() -> dict:
    """Return aggregated statistics for the dashboard overview."""
    reports = get_all_scans()
    total_vulns = sum(r.summary.total for r in reports)
    critical = sum(r.summary.critical for r in reports)
    resolved = sum(
        r.summary.total
        for r in reports
        if r.status == ScanStatus.COMPLETED and r.summary.critical == 0
    )
    return {
        "totalScans": len(reports),
        "totalVulnerabilities": total_vulns,
        "criticalIssues": critical,
        "resolvedIssues": resolved,
        "recentReports": [r.model_dump(by_alias=True) for r in reports[:5]],
    }


# ---------------------------------------------------------------------------
# In-memory store (replaced by a real database in a later step)
# ---------------------------------------------------------------------------

_store: dict[str, ScanReport] = {}
