"""
Regex-based vulnerability scanner for CodeSentinel AI.

This module scans raw source code line-by-line for common security
vulnerability patterns.  It has **no external dependencies** and can be
used independently of the FastAPI app or database layer.

Detected vulnerability categories
-----------------------------------
SQL Injection
    String concatenation, %-formatting, Python f-strings, or JavaScript
    template literals used to build a SQL query.

Hardcoded Secret
    Variable names that suggest credentials (password, api_key, secret,
    token, etc.) assigned to a hard-coded string literal.  Also matches
    well-known high-entropy formats such as AWS Access Key IDs and Google
    API keys.

Unsafe Function
    Calls to ``eval()`` or ``exec()`` (both Python and JavaScript),
    ``os.system()``, or ``subprocess`` invoked with ``shell=True``.

Usage
-----
    from backend.services.scanner import scan_code

    result = scan_code(code="print('hello')", language="python")
    print(result.to_dict())
    # {"issues": []}
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScanIssue:
    """A single vulnerability finding."""

    type: str       # e.g. "SQL Injection"
    line: int       # 1-based line number
    severity: str   # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    message: str    # Human-readable description


@dataclass
class ScanResult:
    """Container for all findings from a single scan."""

    issues: List[ScanIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialise to the canonical JSON structure."""
        return {
            "issues": [
                {
                    "type": issue.type,
                    "line": issue.line,
                    "severity": issue.severity,
                    "message": issue.message,
                }
                for issue in self.issues
            ]
        }


# ---------------------------------------------------------------------------
# Helper: SQL keyword group used across multiple patterns
# ---------------------------------------------------------------------------

_SQL_KW = r"(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|FROM|WHERE|INTO)"

# ---------------------------------------------------------------------------
# SQL Injection – compiled patterns
# ---------------------------------------------------------------------------

# "SELECT ..." + var  |  'SELECT ...' + var  (string concatenation)
_RE_SQL_CONCAT = re.compile(
    rf"""(?:["'])[^"']*\b{_SQL_KW}\b[^"']*(?:["'])\s*\+""",
    re.IGNORECASE,
)

# "SELECT ... %s" % var  |  "SELECT ..." % (var,)
_RE_SQL_PERCENT = re.compile(
    rf"""(?:["'])[^"']*\b{_SQL_KW}\b[^"']*(?:["'])\s*%\s*\w""",
    re.IGNORECASE,
)

# Python f-strings: f"SELECT ... {var}"  |  f'...{var}...'
_RE_SQL_FSTRING = re.compile(
    rf"""f(?:["'])[^"']*\b{_SQL_KW}\b[^"']*\{{""",
    re.IGNORECASE,
)

# JavaScript / TypeScript template literals: `SELECT ... ${var}`
_RE_SQL_TEMPLATE = re.compile(
    rf"""`[^`]*\b{_SQL_KW}\b[^`]*\$\{{""",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Hardcoded secrets – compiled patterns
# ---------------------------------------------------------------------------

# Variable name containing a secret-like word assigned to a string literal
_RE_SECRET_ASSIGN = re.compile(
    r"""\b(?:password|passwd|pwd|api[_-]?key|secret[_-]?key|secret|"""
    r"""access[_-]?key|private[_-]?key|auth[_-]?token|token|"""
    r"""credentials?)\s*[=:]\s*["'][^"']{4,}["']""",
    re.IGNORECASE,
)

# Well-known high-entropy credential formats
# AWS Access Key ID: AKIA… (20 chars)
# Google API key:    AIza… (39 chars)
# Generic hex token: 32–64 lowercase hex chars
# Generic base64 bearer token: 40+ alphanumeric+/= chars
_RE_SECRET_VALUE = re.compile(
    r"""["'](?:AKIA[0-9A-Z]{16}"""
    r"""|AIza[0-9A-Za-z\-_]{35}"""
    r"""|[0-9a-fA-F]{32,64}"""
    r"""|[a-zA-Z0-9+/]{40,}={0,2})["']"""
)

# ---------------------------------------------------------------------------
# Unsafe functions – compiled patterns
# ---------------------------------------------------------------------------

# eval() – dangerous in both Python and JavaScript
_RE_EVAL = re.compile(r"""\beval\s*\(""")

# exec() – Python only (exec is not a function in legacy JS)
_RE_EXEC = re.compile(r"""\bexec\s*\(""")

# os.system() – leads to command injection if user input is included
_RE_OS_SYSTEM = re.compile(r"""\bos\.system\s*\(""")

# subprocess called with shell=True on the *same line*
_RE_SUBPROCESS_SHELL = re.compile(
    r"""\bsubprocess\.\w+\s*\(.*?\bshell\s*=\s*True"""
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_code(code: str, language: str) -> ScanResult:
    """
    Scan *code* for security vulnerabilities and return a :class:`ScanResult`.

    Parameters
    ----------
    code:
        Raw source code string (Python or JavaScript).
    language:
        ``"python"`` or ``"javascript"`` (case-insensitive).

    Returns
    -------
    ScanResult
        Contains a list of :class:`ScanIssue` objects, one per finding.
        Empty list means no issues were detected.
    """
    lang = language.strip().lower()
    issues: list[ScanIssue] = []
    # Track (line, type) to avoid reporting the same category twice on one line.
    seen: set[tuple[int, str]] = set()

    def _add(lineno: int, issue_type: str, severity: str, message: str) -> None:
        key = (lineno, issue_type)
        if key not in seen:
            seen.add(key)
            issues.append(ScanIssue(type=issue_type, line=lineno, severity=severity, message=message))

    for lineno, raw_line in enumerate(code.splitlines(), start=1):
        line = raw_line

        # Skip pure comment lines to reduce false positives
        stripped = line.lstrip()
        if lang == "python" and stripped.startswith("#"):
            continue
        if lang == "javascript" and (
            stripped.startswith("//") or stripped.startswith("*")
        ):
            continue

        # ----------------------------------------------------------------
        # SQL Injection checks
        # ----------------------------------------------------------------
        if _RE_SQL_CONCAT.search(line):
            _add(
                lineno,
                "SQL Injection",
                "HIGH",
                "String concatenation used to build a SQL query; "
                "use parameterised queries instead.",
            )

        if _RE_SQL_PERCENT.search(line):
            _add(
                lineno,
                "SQL Injection",
                "HIGH",
                "%-formatting used to build a SQL query; "
                "use parameterised queries instead.",
            )

        if _RE_SQL_FSTRING.search(line):
            _add(
                lineno,
                "SQL Injection",
                "HIGH",
                "f-string interpolation used in a SQL query; "
                "use parameterised queries instead.",
            )

        if lang == "javascript" and _RE_SQL_TEMPLATE.search(line):
            _add(
                lineno,
                "SQL Injection",
                "HIGH",
                "Template literal interpolation used in a SQL query; "
                "use parameterised queries instead.",
            )

        # ----------------------------------------------------------------
        # Hardcoded secrets checks
        # ----------------------------------------------------------------
        if _RE_SECRET_ASSIGN.search(line):
            _add(
                lineno,
                "Hardcoded Secret",
                "HIGH",
                "Potential hardcoded credential detected; "
                "move secrets to environment variables.",
            )

        if _RE_SECRET_VALUE.search(line):
            _add(
                lineno,
                "Hardcoded Secret",
                "HIGH",
                "Hardcoded API key or token detected; "
                "store secrets securely in environment variables.",
            )

        # ----------------------------------------------------------------
        # Unsafe function checks
        # ----------------------------------------------------------------
        if _RE_EVAL.search(line):
            _add(
                lineno,
                "Unsafe Function",
                "HIGH",
                "eval() executes arbitrary code and must not be used "
                "with untrusted input.",
            )

        if lang == "python" and _RE_EXEC.search(line):
            _add(
                lineno,
                "Unsafe Function",
                "HIGH",
                "exec() executes arbitrary Python code; "
                "prefer safer alternatives.",
            )

        if lang == "python" and _RE_OS_SYSTEM.search(line):
            _add(
                lineno,
                "Unsafe Function",
                "HIGH",
                "os.system() can lead to command injection; "
                "use subprocess with a list of arguments and shell=False.",
            )

        if lang == "python" and _RE_SUBPROCESS_SHELL.search(line):
            _add(
                lineno,
                "Unsafe Function",
                "MEDIUM",
                "subprocess called with shell=True; "
                "pass a list of arguments with shell=False to prevent injection.",
            )

    return ScanResult(issues=issues)
