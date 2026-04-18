/**
 * API service layer for CodeSentinel AI.
 * All backend communication is centralised here so pages and components
 * only need to import from this module.
 */

import { API_BASE_URL, API_ENDPOINTS } from '@/utils/constants';

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}

export interface ScanReport {
  id: string;
  filename: string;
  language: string;
  scannedAt: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  vulnerabilities: Vulnerability[];
  summary: ReportSummary;
}

export interface Vulnerability {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  line: number;
  column?: number;
  codeSnippet?: string;
  recommendation: string;
}

export interface ReportSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  securityScore: number;
}

export interface DashboardStats {
  totalScans: number;
  totalVulnerabilities: number;
  criticalIssues: number;
  resolvedIssues: number;
  recentReports: ScanReport[];
}

export interface UploadResponse {
  scanId: string;
  filename: string;
  status: 'pending' | 'in_progress';
  message: string;
}

export type AnalyzeLanguage = 'python' | 'javascript';

export interface AnalyzeRequest {
  code: string;
  language: AnalyzeLanguage;
}

export interface ScoreResult {
  score: number;
  label: string;
}

export interface ScanIssueResult {
  type: string;
  line: number;
  severity: string;
  message: string;
}

export interface ScanResult {
  issues: ScanIssueResult[];
  scoreResult: ScoreResult;
}

export interface AiReview {
  explanation: string;
  secureVersion: string;
  riskScore: number;
}

export interface AnalyzeResponse {
  submissionId: string;
  language: AnalyzeLanguage;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  submittedAt: string;
  message: string;
  scanResult: ScanResult;
  aiReview?: AiReview;
}

export interface FixRequest {
  code: string;
  language: AnalyzeLanguage;
}

export interface FixResponse {
  originalCode: string;
  fixedCode: string;
  summary: string;
}

export interface GithubRepo {
  id: number;
  name: string;
  fullName: string;
  description: string | null;
  private: boolean;
  htmlUrl: string;
  language: string | null;
  defaultBranch: string;
  updatedAt: string | null;
  stargazersCount: number;
}

export interface GithubFileEntry {
  path: string;
  name: string;
  language: 'python' | 'javascript';
}

export interface GithubFileContent {
  path: string;
  content: string;
  language: 'python' | 'javascript';
  size: number;
}

export interface AppSettings {
  autoScan: boolean;
  reportFormat: 'pdf' | 'json' | 'csv';
  theme: 'light' | 'dark' | 'system';
  apiKey?: string;
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `API error ${response.status}: ${errorBody || response.statusText}`
    );
  }
  return response.json() as Promise<ApiResponse<T>>;
}

function buildUrl(endpoint: string): string {
  return `${API_BASE_URL}${endpoint}`;
}

// ---------------------------------------------------------------------------
// Upload API
// ---------------------------------------------------------------------------

/**
 * Upload a code file for security analysis.
 */
export async function uploadCode(file: File): Promise<ApiResponse<UploadResponse>> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(buildUrl(API_ENDPOINTS.UPLOAD), {
    method: 'POST',
    body: formData,
  });

  return handleResponse<UploadResponse>(response);
}

// ---------------------------------------------------------------------------
// Reports API
// ---------------------------------------------------------------------------

/**
 * Fetch all scan reports for the current user.
 */
export async function getReports(): Promise<ApiResponse<ScanReport[]>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.REPORTS), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse<ScanReport[]>(response);
}

/**
 * Fetch a single scan report by its ID.
 */
export async function getReport(id: string): Promise<ApiResponse<ScanReport>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.REPORT_DETAIL(id)), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse<ScanReport>(response);
}

// ---------------------------------------------------------------------------
// Dashboard API
// ---------------------------------------------------------------------------

/**
 * Fetch aggregated statistics for the dashboard overview.
 */
export async function getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
  const response = await fetch(buildUrl('/dashboard/stats'), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse<DashboardStats>(response);
}

// ---------------------------------------------------------------------------
// Settings API
// ---------------------------------------------------------------------------

/**
 * Retrieve the current application settings.
 */
export async function getSettings(): Promise<ApiResponse<AppSettings>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.SETTINGS), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  return handleResponse<AppSettings>(response);
}

/**
 * Save updated application settings.
 */
export async function saveSettings(
  settings: Partial<AppSettings>
): Promise<ApiResponse<AppSettings>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.SETTINGS), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });

  return handleResponse<AppSettings>(response);
}

// ---------------------------------------------------------------------------
// Analyze API
// ---------------------------------------------------------------------------

/**
 * Submit raw source code for security analysis.
 */
export async function analyzeCode(
  payload: AnalyzeRequest
): Promise<ApiResponse<AnalyzeResponse>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.ANALYZE), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  return handleResponse<AnalyzeResponse>(response);
}

/**
 * Submit raw source code to the AI auto-fix engine.
 * Returns the original code alongside a security-hardened rewrite.
 */
export async function fixCode(
  payload: FixRequest
): Promise<ApiResponse<FixResponse>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.FIX), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  return handleResponse<FixResponse>(response);
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

/**
 * Ping the backend to check service availability.
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(buildUrl(API_ENDPOINTS.HEALTH));
    return response.ok;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// GitHub integration API
// ---------------------------------------------------------------------------

/**
 * Fetch the authenticated user's GitHub repositories.
 * Requires a valid JWT passed as the Bearer token.
 */
export async function getGithubRepos(token: string): Promise<ApiResponse<GithubRepo[]>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.GITHUB_REPOS), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<GithubRepo[]>(response);
}

/**
 * List Python and JavaScript files in a specific repository.
 * Requires a valid JWT passed as the Bearer token.
 */
export async function getRepoFiles(
  token: string,
  owner: string,
  repo: string
): Promise<ApiResponse<GithubFileEntry[]>> {
  const response = await fetch(buildUrl(API_ENDPOINTS.GITHUB_REPO_TREE(owner, repo)), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<GithubFileEntry[]>(response);
}

/**
 * Fetch the decoded content of a single file from a repository.
 * Requires a valid JWT passed as the Bearer token.
 */
export async function getFileContent(
  token: string,
  owner: string,
  repo: string,
  path: string
): Promise<ApiResponse<GithubFileContent>> {
  const url =
    buildUrl(API_ENDPOINTS.GITHUB_REPO_CONTENTS(owner, repo)) +
    `?path=${encodeURIComponent(path)}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<GithubFileContent>(response);
}
