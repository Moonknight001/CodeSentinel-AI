import React, { useState } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
type ScanStatus = 'completed' | 'in_progress' | 'failed';

interface Report {
  id: string;
  filename: string;
  language: string;
  scannedAt: string;
  status: ScanStatus;
  critical: number;
  high: number;
  medium: number;
  low: number;
  score: number;
}

// ---------------------------------------------------------------------------
// Placeholder data
// ---------------------------------------------------------------------------

const PLACEHOLDER_REPORTS: Report[] = [
  {
    id: '1',
    filename: 'auth.py',
    language: 'Python',
    scannedAt: '2026-04-17 14:32',
    status: 'completed',
    critical: 2,
    high: 3,
    medium: 5,
    low: 8,
    score: 62,
  },
  {
    id: '2',
    filename: 'api_handler.js',
    language: 'JavaScript',
    scannedAt: '2026-04-16 09:15',
    status: 'completed',
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
    score: 88,
  },
  {
    id: '3',
    filename: 'UserController.java',
    language: 'Java',
    scannedAt: '2026-04-15 16:48',
    status: 'completed',
    critical: 1,
    high: 4,
    medium: 6,
    low: 7,
    score: 71,
  },
  {
    id: '4',
    filename: 'database.go',
    language: 'Go',
    scannedAt: '2026-04-14 11:23',
    status: 'completed',
    critical: 0,
    high: 0,
    medium: 1,
    low: 4,
    score: 95,
  },
  {
    id: '5',
    filename: 'payment.php',
    language: 'PHP',
    scannedAt: '2026-04-14 08:05',
    status: 'failed',
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    score: 0,
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreBadge(score: number): string {
  if (score >= 80) return 'badge-success';
  if (score >= 60) return 'badge-warning';
  return 'badge-error';
}

function statusBadge(status: ScanStatus): { cls: string; label: string } {
  switch (status) {
    case 'completed': return { cls: 'badge-success', label: 'Completed' };
    case 'in_progress': return { cls: 'badge-info', label: 'In Progress' };
    case 'failed': return { cls: 'badge-error', label: 'Failed' };
  }
}

const SEVERITY_FILTERS: { label: string; value: Severity | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Critical', value: 'critical' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
];

// ---------------------------------------------------------------------------
// Reports page
// ---------------------------------------------------------------------------

export default function ReportsPage() {
  const [filter, setFilter] = useState<Severity | 'all'>('all');

  const filtered = PLACEHOLDER_REPORTS.filter((r) => {
    if (filter === 'all') return true;
    if (filter === 'critical') return r.critical > 0;
    if (filter === 'high') return r.high > 0;
    if (filter === 'medium') return r.medium > 0;
    if (filter === 'low') return r.low > 0;
    return true;
  });

  return (
    <DashboardLayout pageTitle="Reports">
      <div className="space-y-6">
        {/* Page heading */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Scan Reports</h2>
            <p className="text-sm text-gray-500 mt-1">
              Review all historical security scan results.
            </p>
          </div>
          <Link href="/upload" className="btn-primary self-start">
            + New Scan
          </Link>
        </div>

        {/* Severity filter pills */}
        <div className="flex flex-wrap gap-2">
          {SEVERITY_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setFilter(f.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors duration-150 ${
                filter === f.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Reports table */}
        <div className="card overflow-hidden">
          <div className="overflow-x-auto -mx-6 px-6">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="pb-3 text-left font-medium text-gray-500">File</th>
                  <th className="pb-3 text-left font-medium text-gray-500">Language</th>
                  <th className="pb-3 text-left font-medium text-gray-500">Scanned</th>
                  <th className="pb-3 text-center font-medium text-gray-500">Status</th>
                  <th className="pb-3 text-center font-medium text-gray-500">Critical</th>
                  <th className="pb-3 text-center font-medium text-gray-500">High</th>
                  <th className="pb-3 text-center font-medium text-gray-500">Score</th>
                  <th className="pb-3 text-right font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-10 text-center text-gray-400 text-sm">
                      No reports match the selected filter.
                    </td>
                  </tr>
                ) : (
                  filtered.map((report) => {
                    const status = statusBadge(report.status);
                    return (
                      <tr key={report.id} className="hover:bg-gray-50 transition-colors">
                        <td className="py-3 font-mono font-medium text-gray-900">
                          {report.filename}
                        </td>
                        <td className="py-3 text-gray-600">{report.language}</td>
                        <td className="py-3 text-gray-500 whitespace-nowrap">
                          {report.scannedAt}
                        </td>
                        <td className="py-3 text-center">
                          <span className={`badge ${status.cls}`}>{status.label}</span>
                        </td>
                        <td className="py-3 text-center">
                          <span className={`badge ${report.critical > 0 ? 'badge-error' : 'bg-gray-100 text-gray-500'}`}>
                            {report.critical}
                          </span>
                        </td>
                        <td className="py-3 text-center">
                          <span className={`badge ${report.high > 0 ? 'badge-warning' : 'bg-gray-100 text-gray-500'}`}>
                            {report.high}
                          </span>
                        </td>
                        <td className="py-3 text-center">
                          {report.status === 'completed' ? (
                            <span className={`badge ${scoreBadge(report.score)}`}>
                              {report.score}
                            </span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="py-3 text-right">
                          <button
                            type="button"
                            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                            aria-label={`View report for ${report.filename}`}
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
