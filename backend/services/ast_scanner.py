"""
AST-based security scanner for Python code.

This module uses Python's built-in ``ast`` module to parse source code into
an abstract syntax tree and then walks the tree looking for security issues
that are difficult or impossible to detect reliably with simple regex patterns.

Detected vulnerability categories
-----------------------------------
Unsafe Function (eval / exec / __import__)
    ``eval()`` and ``exec()`` are detected wherever they appear in the AST,
    including inside functions, classes, and comprehensions.  Calling either
    directly with the return value of ``input()`` is escalated to CRITICAL
    severity.

Insecure Import
    Certain standard-library modules are inherently risky:

    * ``pickle`` / ``cPickle`` – deserialising untrusted data can execute
      arbitrary code.
    * ``marshal`` – same risk as pickle for bytecode objects.
    * ``shelve`` – backed by pickle; inherits its code-execution risk.
    * ``ctypes`` – direct memory manipulation; can subvert Python's type
      safety guarantees.

Unsanitized Input
    When the return value of ``input()`` is passed *directly* (without an
    intermediate validation or conversion step) as an argument to a dangerous
    sink function, the finding is raised.  Detected sinks:

    * ``eval()``, ``exec()``, ``compile()``
    * ``os.system()``, ``os.popen()``
    * ``subprocess.call()``, ``subprocess.run()``, ``subprocess.Popen()``,
      ``subprocess.check_output()``, ``subprocess.check_call()``
    * ``open()`` (path-traversal risk)

Usage
-----
    from backend.services.ast_scanner import ast_scan_python

    issues = ast_scan_python(code)   # list of ScanIssue (scanner.py dataclass)
    for issue in issues:
        print(issue)
"""

from __future__ import annotations

import ast
from typing import Optional

from backend.services.scanner import ScanIssue

# ---------------------------------------------------------------------------
# Insecure-import registry
# ---------------------------------------------------------------------------

_INSECURE_IMPORTS: dict[str, tuple[str, str]] = {
    "pickle": (
        "HIGH",
        "pickle deserialises arbitrary Python objects; unpickling untrusted data "
        "executes the object's __reduce__ method and can run arbitrary code. "
        "Use json or another format that cannot encode executable objects.",
    ),
    "cPickle": (
        "HIGH",
        "cPickle is the C-accelerated pickle and carries the same code-execution "
        "risk when deserialising untrusted data. Use json instead.",
    ),
    "marshal": (
        "HIGH",
        "marshal serialises Python bytecode objects; loading marshalled data from "
        "an untrusted source can execute arbitrary bytecode. "
        "Avoid unmarshalling untrusted input.",
    ),
    "shelve": (
        "HIGH",
        "shelve stores objects using pickle internally; opening a shelve database "
        "from an untrusted source carries the same code-execution risk as pickle. "
        "Use a safer storage format for untrusted data.",
    ),
    "ctypes": (
        "MEDIUM",
        "ctypes allows direct manipulation of memory and can bypass Python's type "
        "safety guarantees. Ensure all pointer arithmetic and foreign-function calls "
        "are performed on trusted, validated data.",
    ),
}

# ---------------------------------------------------------------------------
# Dangerous sinks for unsanitized-input detection
# ---------------------------------------------------------------------------

# Maps a normalised call name to a human-readable label and severity used in
# the "Unsanitized Input" message.
_INPUT_SINKS: dict[str, tuple[str, str]] = {
    "eval": ("eval()", "CRITICAL"),
    "exec": ("exec()", "CRITICAL"),
    "compile": ("compile()", "HIGH"),
    "open": ("open()", "MEDIUM"),
    "os.system": ("os.system()", "CRITICAL"),
    "os.popen": ("os.popen()", "CRITICAL"),
    "subprocess.call": ("subprocess.call()", "HIGH"),
    "subprocess.run": ("subprocess.run()", "HIGH"),
    "subprocess.Popen": ("subprocess.Popen()", "HIGH"),
    "subprocess.check_output": ("subprocess.check_output()", "HIGH"),
    "subprocess.check_call": ("subprocess.check_call()", "HIGH"),
}

# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------


class _SecurityVisitor(ast.NodeVisitor):
    """Walks a Python AST and records security findings."""

    def __init__(self) -> None:
        self._issues: list[ScanIssue] = []
        self._seen: set[tuple[int, str]] = set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add(
        self,
        node: ast.AST,
        issue_type: str,
        severity: str,
        message: str,
    ) -> None:
        lineno: int = getattr(node, "lineno", 0)
        key = (lineno, issue_type)
        if key not in self._seen:
            self._seen.add(key)
            self._issues.append(
                ScanIssue(
                    type=issue_type,
                    line=lineno,
                    severity=severity,
                    message=message,
                )
            )

    @staticmethod
    def _call_name(node: ast.Call) -> str:
        """Return a dotted string name for a Call node's func, e.g. 'os.system'."""
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            prefix = _SecurityVisitor._attr_chain(func)
            return prefix
        return ""

    @staticmethod
    def _attr_chain(node: ast.Attribute) -> str:
        """Recursively build 'a.b.c' from nested Attribute nodes."""
        value = node.value
        if isinstance(value, ast.Name):
            return f"{value.id}.{node.attr}"
        if isinstance(value, ast.Attribute):
            return f"{_SecurityVisitor._attr_chain(value)}.{node.attr}"
        return node.attr

    @staticmethod
    def _is_input_call(node: ast.expr) -> bool:
        """Return True if *node* is a bare ``input(...)`` call."""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "input"
        )

    # ------------------------------------------------------------------
    # Visitor methods
    # ------------------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top_level = alias.name.split(".")[0]
            if top_level in _INSECURE_IMPORTS:
                severity, detail = _INSECURE_IMPORTS[top_level]
                self._add(
                    node,
                    "Insecure Import",
                    severity,
                    f"Importing '{alias.name}' is a security risk. {detail}",
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            top_level = node.module.split(".")[0]
            if top_level in _INSECURE_IMPORTS:
                severity, detail = _INSECURE_IMPORTS[top_level]
                self._add(
                    node,
                    "Insecure Import",
                    severity,
                    f"Importing from '{node.module}' is a security risk. {detail}",
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node)

        # ---- eval() -------------------------------------------------------
        if name == "eval":
            # Check whether the first argument is a direct input() call.
            if node.args and self._is_input_call(node.args[0]):
                self._add(
                    node,
                    "Unsafe Function",
                    "CRITICAL",
                    "eval() is called directly with user input from input(); "
                    "this allows an attacker to execute arbitrary Python code. "
                    "Never pass user-supplied strings to eval().",
                )
            else:
                self._add(
                    node,
                    "Unsafe Function",
                    "HIGH",
                    "eval() executes an arbitrary Python expression from a string. "
                    "If the string contains any user-controlled data the application "
                    "is vulnerable to arbitrary code execution. "
                    "Replace eval() with a safe parser or explicit type conversion.",
                )

        # ---- exec() -------------------------------------------------------
        elif name == "exec":
            if node.args and self._is_input_call(node.args[0]):
                self._add(
                    node,
                    "Unsafe Function",
                    "CRITICAL",
                    "exec() is called directly with user input from input(); "
                    "this allows an attacker to execute arbitrary Python statements. "
                    "Never pass user-supplied strings to exec().",
                )
            else:
                self._add(
                    node,
                    "Unsafe Function",
                    "HIGH",
                    "exec() executes arbitrary Python statements from a string. "
                    "Any user-controlled data in the string leads to code execution. "
                    "Prefer explicit logic over exec()-based dynamic execution.",
                )

        # ---- __import__() -------------------------------------------------
        elif name == "__import__":
            self._add(
                node,
                "Unsafe Function",
                "HIGH",
                "__import__() loads a module by name at runtime. "
                "If the module name is derived from user input an attacker can "
                "load arbitrary modules. Validate the module name against an "
                "explicit allowlist before calling __import__().",
            )

        # ---- Unsanitized input() passed to other dangerous sinks ----------
        else:
            for arg in node.args:
                if self._is_input_call(arg) and name in _INPUT_SINKS:
                    label, severity = _INPUT_SINKS[name]
                    self._add(
                        node,
                        "Unsanitized Input",
                        severity,
                        f"The return value of input() is passed directly to {label} "
                        "without any validation or sanitization. "
                        "Validate and sanitize all user input before passing it to "
                        "potentially dangerous functions.",
                    )
                    break  # one finding per call site is enough

        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ast_scan_python(code: str) -> list[ScanIssue]:
    """
    Parse *code* as Python source and return a list of security findings.

    If the source cannot be parsed (syntax error) an empty list is returned
    so that the overall scan can still return the regex-based findings.

    Parameters
    ----------
    code:
        Raw Python source code.

    Returns
    -------
    list[ScanIssue]
        Zero or more :class:`~backend.services.scanner.ScanIssue` dataclass
        instances, sorted by line number.
    """
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError:
        # Unparseable code – fall back gracefully; regex scanner still runs.
        return []

    visitor = _SecurityVisitor()
    visitor.visit(tree)
    return sorted(visitor._issues, key=lambda i: i.line)
