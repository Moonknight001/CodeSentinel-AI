/**
 * GithubRepoSelector – three-step GitHub repo integration UI.
 *
 * Step 1 – Unauthenticated: show "Sign in with GitHub" button.
 * Step 2 – Authenticated, no repo selected: show searchable repo list.
 * Step 3 – Repo selected, no file selected: show file list with search.
 * Step 4 – File selected: show file preview + "Analyze" button → scan results.
 *
 * Auth is handled via a JWT stored in localStorage (set by /github?token=xxx).
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  analyzeCode,
  AnalyzeResponse,
  ApiResponse,
  GithubFileContent,
  GithubFileEntry,
  GithubRepo,
  getFileContent,
  getGithubRepos,
  getRepoFiles,
  ScoreResult,
} from '@/services/api';
import { API_BASE_URL } from '@/utils/constants';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Step = 'login' | 'repos' | 'files' | 'file' | 'result';

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

function scoreColorClasses(label: string): { bg: string; text: string; border: string } {
  switch (label) {
    case 'Excellent':
      return { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' };
    case 'Good':
      return { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' };
    case 'Fair':
      return { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' };
    default:
      return { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' };
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const Spinner: React.FC<{ label?: string }> = ({ label = 'Loading…' }) => (
  <div className="flex items-center gap-2 text-sm text-blue-700 py-4">
    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
    {label}
  </div>
);

const ErrorBanner: React.FC<{ message: string }> = ({ message }) => (
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
    {message}
  </div>
);

const ScoreCard: React.FC<{ scoreResult: ScoreResult }> = ({ scoreResult }) => {
  const { score, label } = scoreResult;
  const colors = scoreColorClasses(label);
  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} p-4 flex items-center gap-4`}>
      <div className="flex-shrink-0 text-center">
        <span className={`text-4xl font-extrabold ${colors.text}`}>{score}</span>
        <p className={`text-xs font-medium ${colors.text} mt-0.5`}>/ 100</p>
      </div>
      <div className={`w-px self-stretch ${colors.border} border-l`} />
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Security Score</p>
        <p className={`text-lg font-bold ${colors.text} mt-0.5`}>{label}</p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const GithubRepoSelector: React.FC = () => {
  const [token, setToken] = useState<string | null>(null);
  const [step, setStep] = useState<Step>('login');

  // Repos
  const [repos, setRepos] = useState<GithubRepo[]>([]);
  const [repoSearch, setRepoSearch] = useState('');
  const [selectedRepo, setSelectedRepo] = useState<GithubRepo | null>(null);

  // Files
  const [files, setFiles] = useState<GithubFileEntry[]>([]);
  const [fileSearch, setFileSearch] = useState('');
  const [selectedFile, setSelectedFile] = useState<GithubFileEntry | null>(null);
  const [fileContent, setFileContent] = useState<GithubFileContent | null>(null);

  // Analysis result
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeResponse | null>(null);

  // Loading/error
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ---------------------------------------------------------------------------
  // Bootstrap: pick up token from localStorage or URL param
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Check URL query param first (set by OAuth redirect)
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');
    if (urlToken) {
      localStorage.setItem('cs_token', urlToken);
      // Strip the token from the URL without a full navigation
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, '', cleanUrl);
      setToken(urlToken);
      return;
    }

    const stored = localStorage.getItem('cs_token');
    if (stored) {
      setToken(stored);
    }
  }, []);

  // When we get a token, load repos
  useEffect(() => {
    if (!token) {
      setStep('login');
      return;
    }
    loadRepos(token);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loadRepos = useCallback(async (jwt: string) => {
    setLoading(true);
    setError('');
    try {
      const resp: ApiResponse<GithubRepo[]> = await getGithubRepos(jwt);
      setRepos(resp.data);
      setStep('repos');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load repositories.';
      // Token may be expired
      if (msg.includes('401') || msg.includes('403')) {
        localStorage.removeItem('cs_token');
        setToken(null);
        setStep('login');
        setError('Session expired. Please sign in again.');
      } else {
        setError(msg);
        setStep('repos');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelectRepo = async (repo: GithubRepo) => {
    setSelectedRepo(repo);
    setFiles([]);
    setFileSearch('');
    setSelectedFile(null);
    setFileContent(null);
    setAnalyzeResult(null);
    setError('');
    setLoading(true);
    setStep('files');
    try {
      const resp: ApiResponse<GithubFileEntry[]> = await getRepoFiles(
        token!,
        repo.fullName.split('/')[0],
        repo.name
      );
      setFiles(resp.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load repository files.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectFile = async (file: GithubFileEntry) => {
    setSelectedFile(file);
    setFileContent(null);
    setAnalyzeResult(null);
    setError('');
    setLoading(true);
    setStep('file');
    try {
      const [owner, repo] = selectedRepo!.fullName.split('/');
      const resp: ApiResponse<GithubFileContent> = await getFileContent(
        token!,
        owner,
        repo,
        file.path
      );
      setFileContent(resp.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch file content.');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!fileContent) return;
    setLoading(true);
    setError('');
    setAnalyzeResult(null);
    try {
      const resp: ApiResponse<AnalyzeResponse> = await analyzeCode({
        code: fileContent.content,
        language: fileContent.language as 'python' | 'javascript',
      });
      setAnalyzeResult(resp.data);
      setStep('result');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem('cs_token');
    setToken(null);
    setStep('login');
    setRepos([]);
    setSelectedRepo(null);
    setFiles([]);
    setSelectedFile(null);
    setFileContent(null);
    setAnalyzeResult(null);
    setError('');
  };

  const handleBack = () => {
    if (step === 'result' || step === 'file') {
      setStep('files');
      setSelectedFile(null);
      setFileContent(null);
      setAnalyzeResult(null);
    } else if (step === 'files') {
      setStep('repos');
      setSelectedRepo(null);
      setFiles([]);
    }
    setError('');
  };

  // Filtered lists
  const filteredRepos = useMemo(() => {
    const q = repoSearch.toLowerCase();
    return q
      ? repos.filter(
          (r) =>
            r.name.toLowerCase().includes(q) ||
            (r.description ?? '').toLowerCase().includes(q)
        )
      : repos;
  }, [repos, repoSearch]);

  const filteredFiles = useMemo(() => {
    const q = fileSearch.toLowerCase();
    return q ? files.filter((f) => f.path.toLowerCase().includes(q)) : files;
  }, [files, fileSearch]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const loginUrl = `${API_BASE_URL}/auth/login`;

  if (step === 'login') {
    return (
      <div className="space-y-5">
        {error && <ErrorBanner message={error} />}
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center space-y-4">
          <div className="flex justify-center">
            <svg className="h-12 w-12 text-gray-700" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482
                   0-.237-.009-.868-.013-1.703-2.782.604-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.462-1.11-1.462
                   -.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831
                   .091-.646.35-1.087.636-1.337-2.22-.253-4.555-1.11-4.555-4.943
                   0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647
                   0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836a9.59 9.59 0 012.504.337
                   c1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.202 2.394.1 2.647
                   .64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935
                   .359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743
                   0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12
                   22 6.477 17.523 2 12 2z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Connect your GitHub account</h3>
            <p className="text-sm text-gray-500 mt-1">
              Sign in with GitHub to browse your repositories and send files for security analysis.
            </p>
          </div>
          <a
            href={loginUrl}
            className="btn-primary inline-flex items-center gap-2 px-5 py-2.5 text-sm"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482
                   0-.237-.009-.868-.013-1.703-2.782.604-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.462-1.11-1.462
                   -.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831
                   .091-.646.35-1.087.636-1.337-2.22-.253-4.555-1.11-4.555-4.943
                   0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647
                   0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836a9.59 9.59 0 012.504.337
                   c1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.202 2.394.1 2.647
                   .64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935
                   .359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743
                   0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12
                   22 6.477 17.523 2 12 2z"
              />
            </svg>
            Sign in with GitHub
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Breadcrumb + Sign out */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <nav className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => { setStep('repos'); setSelectedRepo(null); setFiles([]); setSelectedFile(null); setFileContent(null); setAnalyzeResult(null); setError(''); }}
            className="hover:text-blue-600 hover:underline"
          >
            Repositories
          </button>
          {selectedRepo && (
            <>
              <span>/</span>
              <button
                type="button"
                onClick={() => { setStep('files'); setSelectedFile(null); setFileContent(null); setAnalyzeResult(null); setError(''); }}
                className="hover:text-blue-600 hover:underline"
              >
                {selectedRepo.name}
              </button>
            </>
          )}
          {selectedFile && (
            <>
              <span>/</span>
              <span className="text-gray-700 truncate max-w-[200px]" title={selectedFile.path}>
                {selectedFile.name}
              </span>
            </>
          )}
        </nav>
        <button
          type="button"
          onClick={handleSignOut}
          className="text-xs text-gray-400 hover:text-red-500"
        >
          Sign out
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* STEP: Repos */}
      {step === 'repos' && (
        <div className="space-y-3">
          <input
            type="search"
            placeholder="Search repositories…"
            value={repoSearch}
            onChange={(e) => setRepoSearch(e.target.value)}
            className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm
              focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {loading ? (
            <Spinner label="Loading repositories…" />
          ) : filteredRepos.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-6">
              {repoSearch ? 'No repositories match your search.' : 'No repositories found.'}
            </p>
          ) : (
            <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white overflow-hidden">
              {filteredRepos.map((repo) => (
                <li key={repo.id}>
                  <button
                    type="button"
                    onClick={() => handleSelectRepo(repo)}
                    className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900 truncate">{repo.name}</p>
                        {repo.description && (
                          <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                            {repo.description}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 text-xs text-gray-400">
                        {repo.language && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                            {repo.language}
                          </span>
                        )}
                        {repo.private && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                            private
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* STEP: Files */}
      {(step === 'files' || step === 'file') && (
        <div className="space-y-3">
          {step === 'files' && (
            <>
              <input
                type="search"
                placeholder="Search files…"
                value={fileSearch}
                onChange={(e) => setFileSearch(e.target.value)}
                className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm
                  focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {loading ? (
                <Spinner label="Loading files…" />
              ) : filteredFiles.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-6">
                  {fileSearch
                    ? 'No files match your search.'
                    : 'No Python or JavaScript files found in this repository.'}
                </p>
              ) : (
                <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white overflow-hidden max-h-96 overflow-y-auto">
                  {filteredFiles.map((file) => (
                    <li key={file.path}>
                      <button
                        type="button"
                        onClick={() => handleSelectFile(file)}
                        className="w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center gap-3"
                      >
                        <span
                          className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono font-semibold flex-shrink-0 ${
                            file.language === 'python'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          {file.language === 'python' ? '.py' : '.js'}
                        </span>
                        <span className="text-sm text-gray-700 truncate" title={file.path}>
                          {file.path}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          {/* STEP: File preview */}
          {step === 'file' && (
            <div className="space-y-3">
              {loading ? (
                <Spinner label="Fetching file…" />
              ) : fileContent ? (
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                          fileContent.language === 'python'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {fileContent.language === 'python' ? 'Python' : 'JavaScript'}
                      </span>
                      <span className="text-xs text-gray-400">
                        {(fileContent.size / 1024).toFixed(1)} KB
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={handleBack}
                      className="text-xs text-gray-500 hover:text-blue-600"
                    >
                      ← Back to files
                    </button>
                  </div>

                  {/* Code preview */}
                  <div className="rounded-lg border border-gray-200 overflow-auto bg-gray-50" style={{ maxHeight: '40vh' }}>
                    <pre className="px-4 py-3 text-xs font-mono text-gray-800 whitespace-pre-wrap">
                      {fileContent.content.slice(0, 5000)}
                      {fileContent.content.length > 5000 && (
                        <span className="text-gray-400">{'\n\n… (truncated for preview)'}</span>
                      )}
                    </pre>
                  </div>

                  <button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={loading}
                    className="btn-primary w-full py-3"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2 justify-center">
                        <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Analyzing…
                      </span>
                    ) : (
                      '🔍 Analyze this file'
                    )}
                  </button>
                </>
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* STEP: Result */}
      {step === 'result' && analyzeResult && (
        <div className="space-y-4">
          {/* Score */}
          {analyzeResult.scanResult?.scoreResult && (
            <ScoreCard scoreResult={analyzeResult.scanResult.scoreResult} />
          )}

          {/* Issues */}
          {analyzeResult.scanResult?.issues && analyzeResult.scanResult.issues.length > 0 ? (
            <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
                <h4 className="text-sm font-semibold text-gray-900">
                  Detected Issues ({analyzeResult.scanResult.issues.length})
                </h4>
              </div>
              <ul className="divide-y divide-gray-100">
                {analyzeResult.scanResult.issues.map((issue, idx) => (
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
          ) : (
            <p className="text-sm text-green-700 font-medium text-center py-2">
              ✅ No issues detected — code looks clean!
            </p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setStep('file'); setAnalyzeResult(null); }}
              className="btn-secondary flex-1 text-xs"
            >
              ← Back to file
            </button>
            <button
              type="button"
              onClick={() => { setStep('repos'); setSelectedRepo(null); setFiles([]); setSelectedFile(null); setFileContent(null); setAnalyzeResult(null); setError(''); }}
              className="btn-secondary flex-1 text-xs"
            >
              Browse another repo
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GithubRepoSelector;
