import React, { useState } from 'react';
import { analyzeCode, AnalyzeLanguage, AnalyzeResponse, ApiResponse, ScoreResult } from '@/services/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SubmitStatus = 'idle' | 'loading' | 'success' | 'error';

const LANGUAGES: { value: AnalyzeLanguage; label: string }[] = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
];

const MAX_CODE_CHARS = 100_000;

// ---------------------------------------------------------------------------
// Score display helpers
// ---------------------------------------------------------------------------

function scoreColorClasses(label: string): { bg: string; text: string; border: string } {
  switch (label) {
    case 'Excellent':
      return { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' };
    case 'Good':
      return { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' };
    case 'Fair':
      return { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' };
    default: // خطر
      return { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' };
  }
}

function severityBadgeClass(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'CRITICAL':
    case 'HIGH':
      return 'bg-red-100 text-red-800';
    case 'MEDIUM':
      return 'bg-yellow-100 text-yellow-800';
    case 'LOW':
      return 'bg-green-100 text-green-800';
    default:
      return 'bg-gray-100 text-gray-600';
  }
}

// ---------------------------------------------------------------------------
// ScoreCard sub-component
// ---------------------------------------------------------------------------

const ScoreCard: React.FC<{ scoreResult: ScoreResult }> = ({ scoreResult }) => {
  const { score, label } = scoreResult;
  const colors = scoreColorClasses(label);

  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} p-4 flex items-center gap-4`}>
      {/* Numeric score */}
      <div className="flex-shrink-0 text-center">
        <span className={`text-4xl font-extrabold ${colors.text}`}>{score}</span>
        <p className={`text-xs font-medium ${colors.text} mt-0.5`}>/ 100</p>
      </div>
      {/* Divider */}
      <div className={`w-px self-stretch ${colors.border} border-l`} />
      {/* Label */}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Security Score</p>
        <p className={`text-lg font-bold ${colors.text} mt-0.5`}>{label}</p>
        <p className="text-xs text-gray-500 mt-0.5">
          {score >= 90
            ? 'No significant issues detected.'
            : score >= 70
            ? 'Minor issues found — review recommended.'
            : score >= 50
            ? 'Several issues detected — action advised.'
            : 'Critical issues detected — immediate action required.'}
        </p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const CodeAnalysisForm: React.FC = () => {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState<AnalyzeLanguage>('python');
  const [status, setStatus] = useState<SubmitStatus>('idle');
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Client-side validation
    if (!code.trim()) {
      setErrorMessage('Please enter some code before submitting.');
      return;
    }
    if (code.length > MAX_CODE_CHARS) {
      setErrorMessage(
        `Code exceeds the maximum allowed length of ${MAX_CODE_CHARS.toLocaleString()} characters.`
      );
      return;
    }

    setStatus('loading');
    setErrorMessage('');
    setResult(null);

    try {
      const response: ApiResponse<AnalyzeResponse> = await analyzeCode({ code, language });
      setResult(response.data);
      setStatus('success');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred. Please try again.';
      setErrorMessage(message);
      setStatus('error');
    }
  };

  const handleReset = () => {
    setCode('');
    setLanguage('python');
    setStatus('idle');
    setResult(null);
    setErrorMessage('');
  };

  const isLoading = status === 'loading';

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {/* Language selector */}
      <div>
        <label
          htmlFor="language-select"
          className="block text-sm font-medium text-gray-700 mb-1.5"
        >
          Language
        </label>
        <select
          id="language-select"
          value={language}
          onChange={(e) => setLanguage(e.target.value as AnalyzeLanguage)}
          disabled={isLoading}
          className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm
            text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2
            focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {LANGUAGES.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Code textarea */}
      <div>
        <label
          htmlFor="code-textarea"
          className="block text-sm font-medium text-gray-700 mb-1.5"
        >
          Source Code
        </label>
        <textarea
          id="code-textarea"
          value={code}
          onChange={(e) => {
            setCode(e.target.value);
            if (errorMessage) setErrorMessage('');
          }}
          disabled={isLoading}
          placeholder={`Paste your ${language === 'python' ? 'Python' : 'JavaScript'} code here…`}
          rows={18}
          spellCheck={false}
          aria-describedby={errorMessage ? 'code-error' : undefined}
          className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5
            font-mono text-sm text-gray-900 shadow-sm placeholder-gray-400 resize-y
            focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500
            disabled:cursor-not-allowed disabled:opacity-50"
        />
        {/* Character counter */}
        <p className="mt-1 text-right text-xs text-gray-400">
          {code.length.toLocaleString()} / {MAX_CODE_CHARS.toLocaleString()} characters
        </p>
      </div>

      {/* Error message */}
      {errorMessage && (
        <div
          id="code-error"
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3
            text-sm text-red-700"
        >
          <svg
            className="mt-0.5 h-4 w-4 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {errorMessage}
        </div>
      )}

      {/* Success result */}
      {status === 'success' && result && (
        <div role="status" aria-live="polite" className="space-y-4">

          {/* Score card */}
          {result.scanResult?.scoreResult && (
            <ScoreCard scoreResult={result.scanResult.scoreResult} />
          )}

          {/* Submission metadata */}
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 space-y-2">
            <div className="flex items-center gap-2 text-green-700">
              <svg
                className="h-5 w-5 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="font-semibold text-sm">Scan complete!</span>
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600">
              <dt className="font-medium text-gray-500">Submission ID</dt>
              <dd className="font-mono truncate" title={result.submissionId}>
                {result.submissionId}
              </dd>
              <dt className="font-medium text-gray-500">Language</dt>
              <dd className="capitalize">{result.language}</dd>
              <dt className="font-medium text-gray-500">Status</dt>
              <dd className="capitalize">{result.status.replace('_', ' ')}</dd>
              <dt className="font-medium text-gray-500">Submitted at</dt>
              <dd>{new Date(result.submittedAt).toLocaleString()}</dd>
              {result.scanResult && (
                <>
                  <dt className="font-medium text-gray-500">Issues found</dt>
                  <dd>{result.scanResult.issues.length}</dd>
                </>
              )}
            </dl>
          </div>

          {/* Issue list */}
          {result.scanResult?.issues && result.scanResult.issues.length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
                <h4 className="text-sm font-semibold text-gray-900">
                  Detected Issues ({result.scanResult.issues.length})
                </h4>
              </div>
              <ul className="divide-y divide-gray-100">
                {result.scanResult.issues.map((issue, idx) => (
                  <li key={idx} className="px-4 py-3 flex items-start gap-3">
                    <span
                      className={`mt-0.5 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${severityBadgeClass(issue.severity)}`}
                    >
                      {issue.severity}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-gray-800">{issue.type}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{issue.message}</p>
                      <p className="text-xs text-gray-400 mt-0.5">Line {issue.line}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.scanResult?.issues && result.scanResult.issues.length === 0 && (
            <p className="text-sm text-green-700 font-medium text-center py-2">
              ✅ No issues detected — code looks clean!
            </p>
          )}

          <button
            type="button"
            onClick={handleReset}
            className="btn-secondary w-full text-xs"
          >
            Analyze another snippet
          </button>
        </div>
      )}

      {/* Submit button – hidden after success */}
      {status !== 'success' && (
        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full py-3"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg
                className="h-4 w-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Analyzing…
            </span>
          ) : (
            'Analyze'
          )}
        </button>
      )}
    </form>
  );
};

export default CodeAnalysisForm;
