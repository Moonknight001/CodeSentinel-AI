"""
Unit tests for backend.services.ast_scanner.

Tests cover the three detection categories:
  - Unsafe Function  (eval / exec / __import__)
  - Insecure Import  (pickle, marshal, shelve, ctypes, cPickle)
  - Unsanitized Input (input() passed directly to dangerous sinks)

Edge-case tests verify:
  - eval(input(...)) is escalated to CRITICAL
  - syntax errors are handled gracefully (returns empty list)
  - clean code returns no issues
  - integration with scan_code() (AST + regex combined)

Run with:
    python -m pytest backend/tests/test_ast_scanner.py -v
"""

from __future__ import annotations

import pytest

from backend.services.ast_scanner import ast_scan_python
from backend.services.scanner import scan_code, ScanResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def issues_of_type(issues, issue_type: str) -> list:
    return [i for i in issues if i.type == issue_type]


def assert_issue(issues, issue_type: str, *, min_count: int = 1) -> None:
    found = issues_of_type(issues, issue_type)
    assert len(found) >= min_count, (
        f"Expected at least {min_count} '{issue_type}' issue(s), "
        f"got {len(found)}.  All issues: {issues}"
    )


# ===========================================================================
# Unsafe Function – eval()
# ===========================================================================


class TestEvalDetection:
    def test_simple_eval(self):
        code = "result = eval(expr)"
        issues = ast_scan_python(code)
        assert_issue(issues, "Unsafe Function")

    def test_eval_in_function(self):
        code = """\
def process(user_expr):
    return eval(user_expr)
"""
        issues = ast_scan_python(code)
        assert_issue(issues, "Unsafe Function")
        # Line number should point at the eval() call (line 2)
        unsafe = issues_of_type(issues, "Unsafe Function")
        assert any(i.line == 2 for i in unsafe)

    def test_eval_in_class_method(self):
        code = """\
class Calc:
    def run(self, expr):
        eval(expr)
"""
        issues = ast_scan_python(code)
        assert_issue(issues, "Unsafe Function")

    def test_eval_with_input_is_critical(self):
        code = 'eval(input("Enter expression: "))'
        issues = ast_scan_python(code)
        unsafe = issues_of_type(issues, "Unsafe Function")
        assert any(i.severity == "CRITICAL" for i in unsafe), (
            "eval(input()) must be CRITICAL"
        )

    def test_eval_without_input_is_high(self):
        code = "eval(expr)"
        issues = ast_scan_python(code)
        unsafe = issues_of_type(issues, "Unsafe Function")
        assert any(i.severity == "HIGH" for i in unsafe)

    def test_eval_in_list_comprehension(self):
        code = "[eval(x) for x in expressions]"
        issues = ast_scan_python(code)
        assert_issue(issues, "Unsafe Function")

    def test_eval_line_number_correct(self):
        code = "x = 1\ny = 2\nz = eval(expr)\n"
        issues = ast_scan_python(code)
        unsafe = issues_of_type(issues, "Unsafe Function")
        assert any(i.line == 3 for i in unsafe)


# ===========================================================================
# Unsafe Function – exec()
# ===========================================================================


class TestExecDetection:
    def test_simple_exec(self):
        code = "exec(code_string)"
        issues = ast_scan_python(code)
        assert_issue(issues, "Unsafe Function")

    def test_exec_with_input_is_critical(self):
        code = 'exec(input("Enter code: "))'
        issues = ast_scan_python(code)
        unsafe = issues_of_type(issues, "Unsafe Function")
        assert any(i.severity == "CRITICAL" for i in unsafe)

    def test_exec_without_input_is_high(self):
        code = "exec(some_var)"
        issues = ast_scan_python(code)
        unsafe = issues_of_type(issues, "Unsafe Function")
        assert any(i.severity == "HIGH" for i in unsafe)


# ===========================================================================
# Unsafe Function – __import__()
# ===========================================================================


class TestDunderImport:
    def test_dunder_import(self):
        code = '__import__("os")'
        issues = ast_scan_python(code)
        assert_issue(issues, "Unsafe Function")

    def test_dunder_import_severity(self):
        code = 'mod = __import__(user_module)'
        issues = ast_scan_python(code)
        unsafe = issues_of_type(issues, "Unsafe Function")
        assert any(i.severity == "HIGH" for i in unsafe)


# ===========================================================================
# Insecure Import – pickle / marshal / shelve / ctypes / cPickle
# ===========================================================================


class TestInsecureImports:
    @pytest.mark.parametrize(
        "stmt,expected_module_fragment",
        [
            ("import pickle", "pickle"),
            ("import cPickle", "cPickle"),
            ("import marshal", "marshal"),
            ("import shelve", "shelve"),
            ("import ctypes", "ctypes"),
            ("from pickle import loads", "pickle"),
            ("from marshal import loads", "marshal"),
            ("from shelve import open", "shelve"),
            ("from ctypes import CDLL", "ctypes"),
        ],
    )
    def test_insecure_import_detected(self, stmt: str, expected_module_fragment: str):
        issues = ast_scan_python(stmt)
        insecure = issues_of_type(issues, "Insecure Import")
        assert insecure, f"Expected Insecure Import for: {stmt!r}"
        assert any(expected_module_fragment in i.message for i in insecure)

    def test_pickle_severity_is_high(self):
        issues = ast_scan_python("import pickle")
        insecure = issues_of_type(issues, "Insecure Import")
        assert all(i.severity == "HIGH" for i in insecure)

    def test_ctypes_severity_is_medium(self):
        issues = ast_scan_python("import ctypes")
        insecure = issues_of_type(issues, "Insecure Import")
        assert all(i.severity == "MEDIUM" for i in insecure)

    def test_safe_imports_not_flagged(self):
        code = """\
import os
import json
import sys
import re
from pathlib import Path
from typing import List
"""
        issues = ast_scan_python(code)
        insecure = issues_of_type(issues, "Insecure Import")
        assert insecure == [], f"Unexpected insecure import findings: {insecure}"

    def test_insecure_import_line_number(self):
        code = "import os\nimport json\nimport pickle\n"
        issues = ast_scan_python(code)
        insecure = issues_of_type(issues, "Insecure Import")
        assert any(i.line == 3 for i in insecure)

    def test_submodule_import_detected(self):
        # e.g.  import pickle.pickletools
        code = "import pickle.pickletools"
        issues = ast_scan_python(code)
        insecure = issues_of_type(issues, "Insecure Import")
        assert insecure


# ===========================================================================
# Unsanitized Input
# ===========================================================================


class TestUnsanitizedInput:
    @pytest.mark.parametrize(
        "code,sink_fragment",
        [
            ('os.system(input("cmd: "))', "os.system()"),
            ('os.popen(input("cmd: "))', "os.popen()"),
            ('open(input("path: "))', "open()"),
            ('subprocess.call(input("cmd: "))', "subprocess.call()"),
            ('subprocess.run(input("cmd: "))', "subprocess.run()"),
            ('subprocess.Popen(input("cmd: "))', "subprocess.Popen()"),
            ('subprocess.check_output(input("cmd: "))', "subprocess.check_output()"),
            ('subprocess.check_call(input("cmd: "))', "subprocess.check_call()"),
            ('compile(input("src: "), "<>", "exec")', "compile()"),
        ],
    )
    def test_unsanitized_input_to_sink(self, code: str, sink_fragment: str):
        issues = ast_scan_python(code)
        unsanitized = issues_of_type(issues, "Unsanitized Input")
        assert unsanitized, (
            f"Expected 'Unsanitized Input' for {code!r}, got: {issues}"
        )
        assert any(sink_fragment in i.message for i in unsanitized), (
            f"Message should reference {sink_fragment!r}: {unsanitized}"
        )

    def test_input_to_os_system_is_critical(self):
        code = 'os.system(input("command: "))'
        issues = ast_scan_python(code)
        unsanitized = issues_of_type(issues, "Unsanitized Input")
        assert any(i.severity == "CRITICAL" for i in unsanitized)

    def test_input_to_open_is_medium(self):
        code = 'open(input("filename: "))'
        issues = ast_scan_python(code)
        unsanitized = issues_of_type(issues, "Unsanitized Input")
        assert any(i.severity == "MEDIUM" for i in unsanitized)

    def test_validated_input_not_flagged_as_unsanitized(self):
        # int(input()) – input is converted to int; not a direct pass to a sink
        code = 'x = int(input("number: "))'
        issues = ast_scan_python(code)
        unsanitized = issues_of_type(issues, "Unsanitized Input")
        assert unsanitized == []

    def test_input_to_print_not_flagged(self):
        code = 'print(input("name: "))'
        issues = ast_scan_python(code)
        unsanitized = issues_of_type(issues, "Unsanitized Input")
        assert unsanitized == []


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_syntax_error_returns_empty_list(self):
        code = "def broken(:"
        issues = ast_scan_python(code)
        assert issues == []

    def test_empty_string_returns_empty_list(self):
        issues = ast_scan_python("")
        assert issues == []

    def test_clean_code_returns_no_issues(self):
        clean = """\
import json
import os

def get_value(data: dict, key: str) -> str:
    raw = os.environ.get(key, "")
    return json.loads(data).get(key, raw)

def safe_query(db, user_id: int):
    db.execute("SELECT * FROM t WHERE id = %s", (user_id,))
"""
        issues = ast_scan_python(clean)
        assert issues == [], f"Unexpected issues in clean code: {issues}"

    def test_multiple_issues_in_one_snippet(self):
        code = """\
import pickle
import ctypes

def dangerous(user_code, user_path):
    eval(user_code)
    exec(input("enter code: "))
    os.system(input("enter cmd: "))
    open(input("enter path: "))
"""
        issues = ast_scan_python(code)
        types_found = {i.type for i in issues}
        assert "Insecure Import" in types_found
        assert "Unsafe Function" in types_found
        assert "Unsanitized Input" in types_found

    def test_issues_sorted_by_line(self):
        code = """\
import pickle
x = 1
eval(expr)
"""
        issues = ast_scan_python(code)
        lines = [i.line for i in issues]
        assert lines == sorted(lines), "Issues should be sorted by line number"


# ===========================================================================
# Integration: scan_code() merges regex + AST for Python
# ===========================================================================


class TestScanCodeIntegration:
    def test_ast_findings_appear_in_scan_code(self):
        """Insecure Import is AST-only – must appear via scan_code() too."""
        code = "import pickle\n"
        result = scan_code(code, "python")
        insecure = [i for i in result.issues if i.type == "Insecure Import"]
        assert insecure

    def test_no_duplicate_eval_findings(self):
        """eval() is detected by both regex and AST; dedup by (line, type)."""
        code = "eval(expr)\n"
        result = scan_code(code, "python")
        eval_issues = [
            i for i in result.issues
            if i.type == "Unsafe Function" and i.line == 1
        ]
        assert len(eval_issues) == 1, (
            "eval() on one line should produce exactly one Unsafe Function finding"
        )

    def test_javascript_not_ast_scanned(self):
        """AST scan is Python-only; JS code with 'import pickle' must not crash."""
        code = "import pickle from 'pickle';"
        result = scan_code(code, "javascript")
        # No crash; Insecure Import should NOT appear (AST is not run on JS)
        insecure = [i for i in result.issues if i.type == "Insecure Import"]
        assert insecure == []

    def test_combined_categories_detected(self):
        code = """\
import marshal
SECRET = "hunter2"
query = "SELECT * FROM t WHERE id = " + uid
eval(user_expr)
"""
        result = scan_code(code, "python")
        types_found = {i.type for i in result.issues}
        assert "Insecure Import" in types_found
        assert "Hardcoded Secret" in types_found
        assert "SQL Injection" in types_found
        assert "Unsafe Function" in types_found

    def test_result_issues_sorted_by_line(self):
        code = """\
import shelve
password = "s3cr3t"
eval(expr)
"""
        result = scan_code(code, "python")
        lines = [i.line for i in result.issues]
        assert lines == sorted(lines)
