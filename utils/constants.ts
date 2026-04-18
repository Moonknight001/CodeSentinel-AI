// App-wide constants for CodeSentinel AI

export const APP_NAME = 'CodeSentinel AI';
export const APP_VERSION = '0.1.0';
export const APP_DESCRIPTION =
  'AI-powered code security analysis and vulnerability detection platform';

// Navigation routes
export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  UPLOAD: '/upload',
  ANALYZE: '/analyze',
  REPORTS: '/reports',
  SETTINGS: '/settings',
} as const;

// API base URL – override via NEXT_PUBLIC_API_URL environment variable
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api';

// API endpoints
export const API_ENDPOINTS = {
  UPLOAD: '/upload',
  ANALYZE: '/analyze',
  SCAN: '/scan',
  REPORTS: '/reports',
  REPORT_DETAIL: (id: string) => `/reports/${id}`,
  SETTINGS: '/settings',
  HEALTH: '/health',
} as const;

// Severity levels for vulnerability findings
export const SEVERITY_LEVELS = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
  INFO: 'info',
} as const;

export type SeverityLevel = (typeof SEVERITY_LEVELS)[keyof typeof SEVERITY_LEVELS];

// Supported programming languages for analysis
export const SUPPORTED_LANGUAGES = [
  'JavaScript',
  'TypeScript',
  'Python',
  'Java',
  'C',
  'C++',
  'Go',
  'Rust',
  'PHP',
  'Ruby',
] as const;

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

// Accepted file extensions for code upload
export const ACCEPTED_FILE_EXTENSIONS = [
  '.js',
  '.ts',
  '.jsx',
  '.tsx',
  '.py',
  '.java',
  '.c',
  '.cpp',
  '.go',
  '.rs',
  '.php',
  '.rb',
] as const;

// Max upload file size in bytes (10 MB)
export const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024;

// Pagination defaults
export const DEFAULT_PAGE_SIZE = 10;
export const MAX_PAGE_SIZE = 100;

// Sidebar navigation items
export const NAV_ITEMS = [
  {
    label: 'Dashboard',
    href: ROUTES.DASHBOARD,
    icon: 'dashboard',
  },
  {
    label: 'Upload Code',
    href: ROUTES.UPLOAD,
    icon: 'upload',
  },
  {
    label: 'Analyze',
    href: ROUTES.ANALYZE,
    icon: 'analyze',
  },
  {
    label: 'Reports',
    href: ROUTES.REPORTS,
    icon: 'reports',
  },
  {
    label: 'Settings',
    href: ROUTES.SETTINGS,
    icon: 'settings',
  },
] as const;

export type NavItem = (typeof NAV_ITEMS)[number];
