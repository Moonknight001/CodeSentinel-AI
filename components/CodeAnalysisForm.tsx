import React, { useState } from 'react';
import {
  fixCode,
  AnalyzeLanguage,
  AnalyzeResponse,
  FixResponse,
  ApiResponse,
  ScoreResult,
} from '@/services/api';
import DiffViewer from '@/components/DiffViewer';
import { useAnalysisWebSocket } from '@/hooks/useAnalysisWebSocket';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FixStatus = 'idle' | 'loading' | 'success' | 'error';

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
// Progress indicator sub-component
// ---------------------------------------------------------------------------

type ProgressStep = 'scanning' | 'analyzing' | 'completed';

const PROGRESS_STEPS: { key: ProgressStep; label: string; desc: string }[] = [
  { key: 'scanning', label: 'Scanning', desc: 'Running security scanner' },
  { key: 'analyzing', label: 'Analyzing', desc: 'Running AI review' },
  { key: 'completed', label: 'Complete', desc: 'Results ready' },
];

const ProgressTracker: React.FC<{
  currentStage: 'scanning' | 'analyzing' | 'completed' | 'error';
  statusMessage: string;
}> = ({ currentStage, statusMessage }) => {
  const stepOrder: ProgressStep[] = ['scanning', 'analyzing', 'completed'];
  const activeIdx = stepOrder.indexOf(currentStage as ProgressStep);

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm text-blue-700 font-medium">
        {currentStage !== 'completed' && (
          <svg className="h-4 w-4 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        {currentStage === 'completed' && (
          <svg className="h-4 w-4 flex-shrink-0 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        <span>{statusMessage}</span>
      </div>

      {/* Step track */}
      <ol className="flex items-center gap-0" aria-label="Analysis progress">
        {PROGRESS_STEPS.map((step, idx) => {
          const done = activeIdx > idx || currentStage === 'completed';
          const active = step.key === currentStage && currentStage !== 'completed';
          return (
            <React.Fragment key={step.key}>
              <li className="flex flex-col items-center gap-1 flex-shrink-0">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors
                    ${done ? 'bg-green-500 text-white' : active ? 'bg-blue-600 text-white ring-2 ring-blue-300 ring-offset-1' : 'bg-gray-200 text-gray-500'}`}
                  aria-current={active ? 'step' : undefined}
                >
                  {done ? (
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3} aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </div>
                <span className={`text-xs ${done ? 'text-green-700 font-medium' : active ? 'text-blue-700 font-medium' : 'text-gray-400'}`}>
                  {step.label}
                </span>
              </li>
              {idx < PROGRESS_STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 mt-[-1rem] mx-1 transition-colors ${done ? 'bg-green-400' : 'bg-gray-200'}`} aria-hidden="true" />
              )}
            </React.Fragment>
          );
        })}
      </ol>
    </div>
  );
};

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
  const [inputError, setInputError] = useState('');

  // Auto-fix state
  const [fixStatus, setFixStatus] = useState<FixStatus>('idle');
  const [fixResult, setFixResult] = useState<FixResponse | null>(null);
  const [fixError, setFixError] = useState('');

  // WebSocket-based real-time analysis
  const { stage, statusMessage, result, errorMessage, analyze, reset } = useAnalysisWebSocket();

  const isAnalyzing = stage === 'scanning' || stage === 'analyzing';
  const isSuccess = stage === 'completed';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!code.trim()) {
      setInputError('Please enter some code before submitting.');
      return;
    }
    if (code.length > MAX_CODE_CHARS) {
      setInputError(
        `Code exceeds the maximum allowed length of ${MAX_CODE_CHARS.toLocaleString()} characters.`
      );
      return;
    }

    setInputError('');
    setFixStatus('idle');
    setFixResult(null);
    setFixError('');

    // Retrieve JWT from localStorage (set by GitHub OAuth flow)
    const token =
      typeof window !== 'undefined' ? localStorage.getItem('cs_token') ?? undefined : undefined;

    analyze(code, language, token);
  };

  const handleFix = async () => {
    if (!code.trim()) return;
    setFixStatus('loading');
    setFixResult(null);
    setFixError('');
    try {
      const response: ApiResponse<FixResponse> = await fixCode({ code, language });
      setFixResult(response.data);
      setFixStatus('success');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred while fixing the code.';
      setFixError(message);
      setFixStatus('error');
    }
  };

  const handleReset = () => {
    setCode('');
    setLanguage('python');
    setInputError('');
    setFixStatus('idle');
    setFixResult(null);
    setFixError('');
    reset();
  };

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
          disabled={isAnalyzing}
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
            if (inputError) setInputError('');
          }}
          disabled={isAnalyzing}
          placeholder={`Paste your ${language === 'python' ? 'Python' : 'JavaScript'} code here…`}
          rows={18}
          spellCheck={false}
          aria-describedby={inputError ? 'code-error' : undefined}
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

      {/* Input validation error */}
      {inputError && (
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
          {inputError}
        </div>
      )}

      {/* Real-time progress tracker */}
      {(isAnalyzing || isSuccess) && (
        <ProgressTracker
          currentStage={stage as 'scanning' | 'analyzing' | 'completed'}
          statusMessage={statusMessage}
        />
      )}

      {/* WebSocket error */}
      {stage === 'error' && errorMessage && (
        <div
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
      {isSuccess && result && (
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

          {/* Fix Code button */}
          {fixStatus === 'idle' && (
            <button
              type="button"
              onClick={handleFix}
              className="btn-primary w-full"
            >
              🔧 Fix Code
            </button>
          )}

          {/* Fix loading */}
          {fixStatus === 'loading' && (
            <div className="flex items-center justify-center gap-2 py-3 text-sm text-blue-700">
              <svg
                className="h-4 w-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generating fix…
            </div>
          )}

          {/* Fix error */}
          {fixStatus === 'error' && fixError && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              <svg
                className="mt-0.5 h-4 w-4 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {fixError}
            </div>
          )}

          {/* Diff viewer */}
          {fixStatus === 'success' && fixResult && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-gray-900">Code Diff</h4>
              <DiffViewer
                original={fixResult.originalCode}
                fixed={fixResult.fixedCode}
                summary={fixResult.summary}
                filename={`code.${language === 'python' ? 'py' : 'js'}`}
              />
            </div>
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

      {/* Submit button – hidden while analyzing or after success */}
      {!isSuccess && !isAnalyzing && (
        <button
          type="submit"
          className="btn-primary w-full py-3"
        >
          Analyze
        </button>
      )}
    </form>
  );
};

export default CodeAnalysisForm;
