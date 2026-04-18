import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts';
import DashboardLayout from '@/components/DashboardLayout';
import { getDashboardStats, DashboardStats, ScanReport } from '@/services/api';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SEVERITY_COLORS: Record<string, string> = {
  Critical: '#ef4444',
  High: '#f97316',
  Medium: '#eab308',
  Low: '#22c55e',
};

// Placeholder data shown while loading or when the backend is unavailable.
const PLACEHOLDER_STATS: DashboardStats = {
  totalScans: 24,
  totalVulnerabilities: 137,
  criticalIssues: 12,
  resolvedIssues: 89,
  recentReports: [
    {
      id: '1',
      filename: 'auth.py',
      language: 'Python',
      scannedAt: '2026-04-17T10:00:00Z',
      status: 'completed',
      vulnerabilities: [],
      summary: { total: 5, critical: 2, high: 3, medium: 0, low: 0, info: 0, securityScore: 62 },
    },
    {
      id: '2',
      filename: 'api_handler.js',
      language: 'JavaScript',
      scannedAt: '2026-04-16T14:30:00Z',
      status: 'completed',
      vulnerabilities: [],
      summary: { total: 2, critical: 0, high: 1, medium: 1, low: 0, info: 0, securityScore: 88 },
    },
    {
      id: '3',
      filename: 'UserController.java',
      language: 'Java',
      scannedAt: '2026-04-15T09:15:00Z',
      status: 'completed',
      vulnerabilities: [],
      summary: { total: 7, critical: 1, high: 4, medium: 2, low: 0, info: 0, securityScore: 71 },
    },
    {
      id: '4',
      filename: 'database.py',
      language: 'Python',
      scannedAt: '2026-04-14T08:00:00Z',
      status: 'completed',
      vulnerabilities: [],
      summary: { total: 3, critical: 0, high: 0, medium: 2, low: 1, info: 0, securityScore: 91 },
    },
    {
      id: '5',
      filename: 'routes.js',
      language: 'JavaScript',
      scannedAt: '2026-04-13T11:45:00Z',
      status: 'completed',
      vulnerabilities: [],
      summary: { total: 4, critical: 1, high: 2, medium: 1, low: 0, info: 0, securityScore: 74 },
    },
  ],
};

// ---------------------------------------------------------------------------
// Helper: derive severity breakdown from a list of reports
// ---------------------------------------------------------------------------

interface SeverityBreakdown {
  name: string;
  value: number;
}

function deriveSeverityBreakdown(reports: ScanReport[]): SeverityBreakdown[] {
  const totals = reports.reduce(
    (acc, r) => ({
      critical: acc.critical + (r.summary?.critical ?? 0),
      high: acc.high + (r.summary?.high ?? 0),
      medium: acc.medium + (r.summary?.medium ?? 0),
      low: acc.low + (r.summary?.low ?? 0),
    }),
    { critical: 0, high: 0, medium: 0, low: 0 }
  );

  return [
    { name: 'Critical', value: totals.critical },
    { name: 'High', value: totals.high },
    { name: 'Medium', value: totals.medium },
    { name: 'Low', value: totals.low },
  ].filter((entry) => entry.value > 0);
}

// ---------------------------------------------------------------------------
// Helper: build per-scan bar chart data
// ---------------------------------------------------------------------------

interface BarEntry {
  name: string;
  Critical: number;
  High: number;
  Medium: number;
  Low: number;
}

function deriveBarData(reports: ScanReport[]): BarEntry[] {
  return reports.map((r) => ({
    // Truncate long filenames for the chart axis
    name: r.filename.length > 14 ? `${r.filename.slice(0, 12)}…` : r.filename,
    Critical: r.summary?.critical ?? 0,
    High: r.summary?.high ?? 0,
    Medium: r.summary?.medium ?? 0,
    Low: r.summary?.low ?? 0,
  }));
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

interface StatCardProps {
  label: string;
  value: string | number;
  description: string;
  color: string;
  icon: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, description, color, icon }) => (
  <div className="card flex items-start gap-4">
    <div className={`flex items-center justify-center w-12 h-12 rounded-xl ${color} flex-shrink-0`}>
      {icon}
    </div>
    <div className="min-w-0">
      <p className="text-sm text-gray-500 truncate">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
      <p className="text-xs text-gray-400 mt-0.5">{description}</p>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Skeleton loader for stat cards
// ---------------------------------------------------------------------------

const StatCardSkeleton: React.FC = () => (
  <div className="card flex items-start gap-4 animate-pulse">
    <div className="w-12 h-12 rounded-xl bg-gray-200 flex-shrink-0" />
    <div className="flex-1 space-y-2 py-1">
      <div className="h-3 bg-gray-200 rounded w-3/4" />
      <div className="h-6 bg-gray-200 rounded w-1/2" />
      <div className="h-2 bg-gray-100 rounded w-5/6" />
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number): string {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Dashboard page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getDashboardStats()
      .then((res) => {
        if (!cancelled) setStats(res.data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          // Fall back to placeholder data so the UI is always useful
          setStats(PLACEHOLDER_STATS);
          setError(
            err instanceof Error
              ? err.message
              : 'Could not reach the backend – showing sample data.'
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const display = stats ?? PLACEHOLDER_STATS;
  const recentReports = display.recentReports ?? [];
  const severityData = deriveSeverityBreakdown(recentReports);
  const barData = deriveBarData(recentReports);

  return (
    <DashboardLayout pageTitle="Dashboard">
      <div className="space-y-6">

        {/* Page heading */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Security Overview</h2>
          <p className="text-sm text-gray-500 mt-1">
            Monitor your code security posture at a glance.
          </p>
        </div>

        {/* Backend error banner */}
        {error && (
          <div className="flex items-center gap-3 px-4 py-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
            <svg className="w-4 h-4 flex-shrink-0 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)
          ) : (
            <>
              <StatCard
                label="Total Scans"
                value={display.totalScans}
                description="All-time scans"
                color="bg-blue-100"
                icon={
                  <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                }
              />
              <StatCard
                label="Vulnerabilities"
                value={display.totalVulnerabilities}
                description="Across all scans"
                color="bg-red-100"
                icon={
                  <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                }
              />
              <StatCard
                label="Critical Issues"
                value={display.criticalIssues}
                description="Need immediate attention"
                color="bg-orange-100"
                icon={
                  <svg className="w-6 h-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  </svg>
                }
              />
              <StatCard
                label="Resolved"
                value={display.resolvedIssues}
                description="Issues fixed"
                color="bg-green-100"
                icon={
                  <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              />
            </>
          )}
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Severity breakdown donut chart */}
          <div className="card">
            <h3 className="text-base font-semibold text-gray-900 mb-4">
              Severity Breakdown
            </h3>
            {loading ? (
              <div className="flex items-center justify-center h-56 animate-pulse">
                <div className="w-40 h-40 rounded-full bg-gray-200" />
              </div>
            ) : severityData.length === 0 ? (
              <div className="flex items-center justify-center h-56 text-sm text-gray-400">
                No vulnerability data yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {severityData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={SEVERITY_COLORS[entry.name] ?? '#94a3b8'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => [value, '']}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={10}
                    wrapperStyle={{ fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Vulnerabilities per scan bar chart */}
          <div className="card">
            <h3 className="text-base font-semibold text-gray-900 mb-4">
              Vulnerabilities per Scan
            </h3>
            {loading ? (
              <div className="flex items-end justify-around h-56 gap-3 px-4 animate-pulse">
                {[80, 50, 70, 40, 60].map((h, i) => (
                  <div key={i} className="flex-1 bg-gray-200 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            ) : barData.length === 0 ? (
              <div className="flex items-center justify-center h-56 text-sm text-gray-400">
                No scan data yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={barData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: '#6b7280' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: '#6b7280' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    cursor={{ fill: '#f8fafc' }}
                  />
                  <Legend
                    iconType="square"
                    iconSize={10}
                    wrapperStyle={{ fontSize: 12 }}
                  />
                  <Bar dataKey="Critical" stackId="a" fill={SEVERITY_COLORS['Critical']} radius={0} />
                  <Bar dataKey="High" stackId="a" fill={SEVERITY_COLORS['High']} radius={0} />
                  <Bar dataKey="Medium" stackId="a" fill={SEVERITY_COLORS['Medium']} radius={0} />
                  <Bar dataKey="Low" stackId="a" fill={SEVERITY_COLORS['Low']} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Recent scans table */}
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-gray-900">Recent Scans</h3>
            <Link href="/reports" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
              View all →
            </Link>
          </div>

          <div className="overflow-x-auto -mx-6 px-6">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="pb-3 text-left font-medium text-gray-500">File</th>
                  <th className="pb-3 text-left font-medium text-gray-500">Language</th>
                  <th className="pb-3 text-left font-medium text-gray-500">Date</th>
                  <th className="pb-3 text-center font-medium text-gray-500">Critical</th>
                  <th className="pb-3 text-center font-medium text-gray-500">High</th>
                  <th className="pb-3 text-center font-medium text-gray-500">Medium</th>
                  <th className="pb-3 text-center font-medium text-gray-500">Low</th>
                  <th className="pb-3 text-center font-medium text-gray-500">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {loading
                  ? Array.from({ length: 3 }).map((_, i) => (
                      <tr key={i} className="animate-pulse">
                        {Array.from({ length: 8 }).map((__, j) => (
                          <td key={j} className="py-3 px-1">
                            <div className="h-3 bg-gray-100 rounded w-full" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : recentReports.map((scan) => {
                      const score = scan.summary?.securityScore ?? 0;
                      return (
                        <tr key={scan.id} className="hover:bg-gray-50 transition-colors">
                          <td className="py-3 font-mono font-medium text-gray-900">
                            {scan.filename}
                          </td>
                          <td className="py-3 text-gray-600">{scan.language}</td>
                          <td className="py-3 text-gray-500">{formatDate(scan.scannedAt)}</td>
                          <td className="py-3 text-center">
                            <span className={`badge ${(scan.summary?.critical ?? 0) > 0 ? 'badge-error' : 'bg-gray-100 text-gray-600'}`}>
                              {scan.summary?.critical ?? 0}
                            </span>
                          </td>
                          <td className="py-3 text-center">
                            <span className={`badge ${(scan.summary?.high ?? 0) > 0 ? 'badge-warning' : 'bg-gray-100 text-gray-600'}`}>
                              {scan.summary?.high ?? 0}
                            </span>
                          </td>
                          <td className="py-3 text-center">
                            <span className={`badge ${(scan.summary?.medium ?? 0) > 0 ? 'badge-info' : 'bg-gray-100 text-gray-600'}`}>
                              {scan.summary?.medium ?? 0}
                            </span>
                          </td>
                          <td className="py-3 text-center">
                            <span className={`badge ${(scan.summary?.low ?? 0) > 0 ? 'badge-success' : 'bg-gray-100 text-gray-600'}`}>
                              {scan.summary?.low ?? 0}
                            </span>
                          </td>
                          <td className={`py-3 text-center font-bold ${scoreColor(score)}`}>
                            {score}
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </DashboardLayout>
  );
}
