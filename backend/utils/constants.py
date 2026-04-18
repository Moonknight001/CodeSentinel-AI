"""
App-wide constants for the CodeSentinel AI backend.
"""

APP_NAME = "CodeSentinel AI"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "AI-powered code security analysis and vulnerability detection platform"

API_PREFIX = "/api"

# Allowed origins for CORS – extend this list in production via environment variables
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Supported programming languages for analysis
SUPPORTED_LANGUAGES = [
    "JavaScript",
    "TypeScript",
    "Python",
    "Java",
    "C",
    "C++",
    "Go",
    "Rust",
    "PHP",
    "Ruby",
]

# Accepted source-code file extensions
ACCEPTED_EXTENSIONS = {
    ".js", ".ts", ".jsx", ".tsx",
    ".py",
    ".java",
    ".c", ".cpp",
    ".go",
    ".rs",
    ".php",
    ".rb",
}

# Maximum upload size: 10 MB
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

# GitHub OAuth
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE_URL = "https://api.github.com"
