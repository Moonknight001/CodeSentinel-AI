import React from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import GithubRepoSelector from '@/components/GithubRepoSelector';

export default function GithubPage() {
  return (
    <DashboardLayout pageTitle="GitHub Repositories">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Page heading */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900">GitHub Repository Analysis</h2>
          <p className="text-sm text-gray-500 mt-1">
            Connect your GitHub account to browse repositories, select a Python or JavaScript file,
            and run an AI-powered security scan — all without copying and pasting code.
          </p>
        </div>

        {/* Card */}
        <div className="card">
          <GithubRepoSelector />
        </div>
      </div>
    </DashboardLayout>
  );
}
