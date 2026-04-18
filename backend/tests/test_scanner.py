"""
Unit tests for backend.services.scanner.

These tests are pure-Python (no FastAPI, no database) and verify that the
regex-based scanner detects the three vulnerability categories:
  - SQL Injection
  - Hardcoded Secret
  - Unsafe Function

Run with:
    python -m pytest backend/tests/test_scanner.py -v
"""

from __future__ import annotations

import pytest

from backend.services.scanner import ScanResult, scan_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def issues_of_type(result: ScanResult, issue_type: str) -> list:
    return [i for i in result.issues if i.type == issue_type]


def lines_of_type(result: ScanResult, issue_type: str) -> list[int]:
    return [i.line for i in issues_of_type(result, issue_type)]


# ===========================================================================
# SQL Injection – Python
# ===========================================================================


class TestSQLInjectionPython:
    def test_string_concatenation(self):
        code = 'query = "SELECT * FROM users WHERE id = " + user_id'
        result = scan_code(code, "python")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_percent_formatting(self):
        code = 'query = "SELECT * FROM users WHERE name = \'%s\'" % name'
        result = scan_code(code, "python")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_fstring(self):
        code = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
        result = scan_code(code, "python")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_fstring_insert(self):
        code = "sql = f'INSERT INTO logs VALUES ({log_entry})'"
        result = scan_code(code, "python")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_concat_delete(self):
        code = '"DELETE FROM sessions WHERE token = " + token'
        result = scan_code(code, "python")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_safe_parameterised_query_not_flagged(self):
        code = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
        result = scan_code(code, "python")
        sql_issues = issues_of_type(result, "SQL Injection")
        assert sql_issues == []

    def test_comment_line_skipped(self):
        code = '# query = "SELECT * FROM users WHERE id = " + user_id'
        result = scan_code(code, "python")
        assert result.issues == []

    def test_line_number_reported_correctly(self):
        code = "x = 1\nquery = \"SELECT * FROM t WHERE id = \" + uid\ny = 2"
        result = scan_code(code, "python")
        sqli_lines = lines_of_type(result, "SQL Injection")
        assert 2 in sqli_lines


# ===========================================================================
# SQL Injection – JavaScript
# ===========================================================================


class TestSQLInjectionJavaScript:
    def test_template_literal(self):
        code = "const q = `SELECT * FROM users WHERE id = ${userId}`;"
        result = scan_code(code, "javascript")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_template_literal_insert(self):
        code = "db.query(`INSERT INTO logs (msg) VALUES ('${msg}')`)"
        result = scan_code(code, "javascript")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_string_concatenation(self):
        code = "var q = \"SELECT * FROM orders WHERE user_id = \" + userId;"
        result = scan_code(code, "javascript")
        assert any(i.type == "SQL Injection" for i in result.issues)

    def test_comment_line_skipped(self):
        code = "// const q = `SELECT * FROM users WHERE id = ${userId}`;"
        result = scan_code(code, "javascript")
        assert result.issues == []

    def test_safe_placeholder_not_flagged(self):
        code = "db.query('SELECT * FROM users WHERE id = ?', [userId]);"
        result = scan_code(code, "javascript")
        sql_issues = issues_of_type(result, "SQL Injection")
        assert sql_issues == []


# ===========================================================================
# Hardcoded Secrets
# ===========================================================================


class TestHardcodedSecrets:
    @pytest.mark.parametrize(
        "line",
        [
            'api_key = "abc123def456"',
            'password = "MyPassword123"',
            'SECRET_KEY = "supersecret-value"',
            'token = "eyJhbGciOiJIUzI1NiJ9abcdef"',
            'API_KEY: "some_api_key_value_here"',
            'private_key = "-----BEGIN RSA PRIVATE"',
        ],
    )
    def test_secret_variable_assignment(self, line: str):
        result = scan_code(line, "python")
        assert any(i.type == "Hardcoded Secret" for i in result.issues), (
            f"Expected Hardcoded Secret for: {line!r}"
        )

    def test_aws_access_key_id(self):
        # Real AWS Access Key ID format: AKIA + 16 uppercase alphanumeric = 20 chars
        code = 'key = "AKIAIOSFODNN7EXAMPLE"'
        result = scan_code(code, "python")
        assert any(i.type == "Hardcoded Secret" for i in result.issues)

    def test_google_api_key(self):
        # Real Google API key format: AIza + 35 alphanumeric/dash/underscore = 39 chars
        code = 'creds = "AIzaSyB0ExAmPlE_1234567890ABCDE12345XYZ"'
        result = scan_code(code, "python")
        assert any(i.type == "Hardcoded Secret" for i in result.issues)

    def test_empty_string_not_flagged(self):
        code = 'password = ""'
        result = scan_code(code, "python")
        secret_issues = issues_of_type(result, "Hardcoded Secret")
        assert secret_issues == []

    def test_env_var_not_flagged(self):
        code = 'api_key = os.environ["API_KEY"]'
        result = scan_code(code, "python")
        secret_issues = issues_of_type(result, "Hardcoded Secret")
        assert secret_issues == []

    def test_severity_is_high(self):
        code = 'password = "hunter2"'
        result = scan_code(code, "python")
        secrets = issues_of_type(result, "Hardcoded Secret")
        assert secrets and all(s.severity == "HIGH" for s in secrets)


# ===========================================================================
# Unsafe Functions
# ===========================================================================


class TestUnsafeFunctions:
    def test_eval_python(self):
        code = "result = eval(user_input)"
        result = scan_code(code, "python")
        assert any(i.type == "Unsafe Function" for i in result.issues)

    def test_eval_javascript(self):
        code = "const result = eval(userInput);"
        result = scan_code(code, "javascript")
        assert any(i.type == "Unsafe Function" for i in result.issues)

    def test_exec_python(self):
        code = "exec(user_code)"
        result = scan_code(code, "python")
        assert any(i.type == "Unsafe Function" for i in result.issues)

    def test_exec_not_flagged_in_javascript(self):
        # exec is not a function call of concern in JavaScript
        code = "exec(command);"
        result = scan_code(code, "javascript")
        unsafe = issues_of_type(result, "Unsafe Function")
        # eval inside exec() name would not match; exec alone should not flag
        assert not any(i.message and "exec()" in i.message for i in unsafe)

    def test_os_system(self):
        code = 'os.system("ls " + user_input)'
        result = scan_code(code, "python")
        assert any(i.type == "Unsafe Function" for i in result.issues)

    def test_subprocess_shell_true(self):
        code = "subprocess.call(cmd, shell=True)"
        result = scan_code(code, "python")
        assert any(i.type == "Unsafe Function" for i in result.issues)

    def test_subprocess_shell_false_not_flagged(self):
        code = "subprocess.call(['ls', '-la'], shell=False)"
        result = scan_code(code, "python")
        unsafe = issues_of_type(result, "Unsafe Function")
        subprocess_issues = [
            i for i in unsafe if "subprocess" in i.message.lower()
        ]
        assert subprocess_issues == []

    def test_exec_comment_skipped_python(self):
        code = "# exec(user_code)"
        result = scan_code(code, "python")
        assert result.issues == []

    def test_severity_high_for_eval(self):
        code = "x = eval(expr)"
        result = scan_code(code, "python")
        evals = [i for i in result.issues if i.type == "Unsafe Function"]
        assert evals and all(e.severity == "HIGH" for e in evals)


# ===========================================================================
# Multiple issues in one snippet
# ===========================================================================


class TestMultipleIssues:
    VULNERABLE_PYTHON = """\
import os
SECRET_KEY = "abc123supersecret"
db_password = "hardcoded_pass"

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)

def run_arbitrary(code_str):
    eval(code_str)
    exec(code_str)
    os.system("ls " + code_str)
"""

    def test_all_categories_detected(self):
        result = scan_code(self.VULNERABLE_PYTHON, "python")
        types_found = {i.type for i in result.issues}
        assert "SQL Injection" in types_found
        assert "Hardcoded Secret" in types_found
        assert "Unsafe Function" in types_found

    def test_to_dict_structure(self):
        result = scan_code(self.VULNERABLE_PYTHON, "python")
        d = result.to_dict()
        assert "issues" in d
        assert isinstance(d["issues"], list)
        for issue in d["issues"]:
            assert {"type", "line", "severity", "message"} <= issue.keys()

    def test_clean_code_returns_no_issues(self):
        clean = """\
import os

def get_user(db, user_id: int):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()

API_KEY = os.environ.get("API_KEY")
"""
        result = scan_code(clean, "python")
        assert result.issues == []
