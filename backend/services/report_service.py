"""
Report service – thin wrapper around the scan service's in-memory store.

Provides the data-access layer for the /reports routes.
"""

from __future__ import annotations

from typing import Optional

from backend.models.schemas import ScanReport
from backend.services import scan_service


def list_reports() -> list[ScanReport]:
    """Return all scan reports ordered newest-first."""
    return scan_service.get_all_scans()


def get_report(report_id: str) -> Optional[ScanReport]:
    """Return a single report by ID, or None if not found."""
    return scan_service.get_scan(report_id)
