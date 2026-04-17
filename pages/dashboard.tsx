import React from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';

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

const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  description,
  color,
  icon,
}) => (
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
// Placeholder recent-scans row
// ---------------------------------------------------------------------------

interface RecentScan {
  id: string;
  filename: string;
  language: string;
  date: string;
  critical: number;
  high: number;
  score: number;
}

const PLACEHOLDER_SCANS: RecentScan[] = [
  {
    id: '1',
    filename: 'auth.py',
    language: 'Python',
    date: '2026-04-17',
    critical: 2,
    high: 3,
    score: 62,
  },
  {
    id: '2',
    filename: 'api_handler.js',
    language: 'JavaScript',
    date: '2026-04-16',
    critical: 0,
    high: 1,
    score: 88,
  },
  {
    id: '3',
    filename: 'UserController.java',
    language: 'Java',
    date: '2026-04-15',
    critical: 1,
    high: 4,
    score: 71,
  },
];

function scoreColor(score: number): string {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}

// ---------------------------------------------------------------------------
// Dashboard page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  return (
    <DashboardLayout pageTitle="Dashboard">
      <div className="space-y-6">
        {/* Page heading */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Security Overview
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Monitor your code security posture at a glance.
          </p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Scans"
            value="24"
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
            value="137"
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
            value="12"
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
            value="89"
            description="Issues fixed"
            color="bg-green-100"
            icon={
              <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
        </div>

        {/* Recent scans table */}
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-gray-900">
              Recent Scans
            </h3>
            <Link
              href="/reports"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
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
                  <th className="pb-3 text-center font-medium text-gray-500">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {PLACEHOLDER_SCANS.map((scan) => (
                  <tr key={scan.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 font-mono font-medium text-gray-900">
                      {scan.filename}
                    </td>
                    <td className="py-3 text-gray-600">{scan.language}</td>
                    <td className="py-3 text-gray-500">{scan.date}</td>
                    <td className="py-3 text-center">
                      <span className={`badge ${scan.critical > 0 ? 'badge-error' : 'bg-gray-100 text-gray-600'}`}>
                        {scan.critical}
                      </span>
                    </td>
                    <td className="py-3 text-center">
                      <span className={`badge ${scan.high > 0 ? 'badge-warning' : 'bg-gray-100 text-gray-600'}`}>
                        {scan.high}
                      </span>
                    </td>
                    <td className={`py-3 text-center font-bold ${scoreColor(scan.score)}`}>
                      {scan.score}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
