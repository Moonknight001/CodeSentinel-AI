"""
Reports routes.

GET  /api/reports       →  list all scan reports (newest first)
GET  /api/reports/{id}  →  retrieve a single report
GET  /api/dashboard/stats → aggregated stats for the dashboard overview
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import ApiResponse, DashboardStats, ScanReport
from backend.services import report_service, scan_service

router = APIRouter(tags=["reports"])


@router.get(
    "/reports",
    response_model=ApiResponse[List[ScanReport]],
    summary="List all scan reports",
)
def list_reports() -> ApiResponse[List[ScanReport]]:
    reports = report_service.list_reports()
    return ApiResponse(
        data=reports,
        message=f"{len(reports)} report(s) found",
        success=True,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ApiResponse[ScanReport],
    summary="Get a single scan report",
)
def get_report(report_id: str) -> ApiResponse[ScanReport]:
    report = report_service.get_report(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )
    return ApiResponse(data=report, success=True)


@router.get(
    "/dashboard/stats",
    response_model=ApiResponse[DashboardStats],
    summary="Get dashboard statistics",
)
def dashboard_stats() -> ApiResponse[DashboardStats]:
    raw = scan_service.get_dashboard_stats()
    stats = DashboardStats(
        totalScans=raw["totalScans"],
        totalVulnerabilities=raw["totalVulnerabilities"],
        criticalIssues=raw["criticalIssues"],
        resolvedIssues=raw["resolvedIssues"],
        recentReports=raw["recentReports"],
    )
    return ApiResponse(data=stats, success=True)
