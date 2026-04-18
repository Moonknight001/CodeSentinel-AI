import React from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import CodeAnalysisForm from '@/components/CodeAnalysisForm';

export default function AnalyzePage() {
  return (
    <DashboardLayout pageTitle="Analyze Code">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Page heading */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Analyze Code</h2>
          <p className="text-sm text-gray-500 mt-1">
            Paste your source code below, choose a language and click{' '}
            <strong>Analyze</strong> to run an AI-powered security scan.
          </p>
        </div>

        {/* Form card */}
        <div className="card">
          <CodeAnalysisForm />
        </div>
      </div>
    </DashboardLayout>
  );
}
