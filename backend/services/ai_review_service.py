"""
AI review layer for CodeSentinel AI (Prompts 8 & 9).

This module calls the OpenAI Chat Completions API to produce a structured
security review of submitted source code.  It augments the deterministic
regex + AST scanner findings with:

* A plain-English **explanation** of every detected vulnerability —
  written from the perspective of a senior security engineer, referencing
  the exact lines, variable names, and API calls in the submitted code.
* A **secure rewrite** of the code using the language's idiomatic safe APIs,
  with inline ``# SECURITY FIX:`` / ``// SECURITY FIX:`` comments on every
  changed line that name both the vulnerability class and the fix applied.
* A **risk score** (integer 1–10) calibrated against real-world exploitability,
  attack surface, and business impact — not merely theoretical severity.

Prompt engineering (Prompt 9)
------------------------------
The system prompt encodes a senior-security-engineer persona and enforces:

* **Specificity** — every finding must reference exact line numbers, variable
  names, and API calls from the submitted code; generic CWE-definition-style
  text is explicitly forbidden.
* **Hidden chain-of-thought** — the model is instructed to reason through a
  four-step process (triage → exploit scenario → fix strategy → risk
  calibration) before writing the JSON, anchoring conclusions to the code.
* **Idiomatic fixes** — the secure rewrite must use the language's recommended
  safe API (e.g. parameterised queries, ``ast.literal_eval``, subprocess list
  args), not superficial wrappers.
* **Calibrated risk scoring** — explicit reference points across the 1–10 scale
  prevent the model from clustering every score around 5–7.

Design principles
-----------------
* **Optional** — if ``OPENAI_API_KEY`` is absent the function returns
  ``None`` immediately; the rest of the scan result is unaffected.
* **Resilient** — any API error (network, quota, invalid JSON, unexpected
  schema) is caught and logged; the function returns ``None`` so the caller
  always receives a usable scan result even when the AI layer is unavailable.
* **Structured output** — the model is instructed to reply with a strict JSON
  object that maps directly onto the :class:`~backend.models.schemas.AiReview`
  Pydantic model.  The ``response_format`` parameter enforces JSON mode on
  models that support it.

Usage
-----
    from backend.services.ai_review_service import get_ai_review

    review = await get_ai_review(code, "python", issues)
    if review:
        print(review.risk_score, review.explanation)
"""

from __future__ import annotations

import json
import logging
import os
from typing import List, Optional

from backend.models.schemas import AiReview, ScanIssue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Model to use – gpt-4o-mini gives an excellent quality/cost ratio for this
# task; override via environment variable if needed.
_OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Maximum tokens for the completion (the secure rewrite can be lengthy).
_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "2048"))

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

# The system prompt defines the model's persona, reasoning discipline, and
# strict output contract.  It is intentionally detailed to prevent generic,
# copy-paste security advice and to force the model to reason about the
# *specific* code it receives.
#
# Design goals (Prompt 9):
#   1. Persona       — senior security engineer with 10+ years of AppSec / pen-test
#                      experience; no generic CWE definitions, only issue-specific insight.
#   2. Specificity   — every finding must reference the exact line, variable name, or
#                      API call from the submitted code; generic statements are forbidden.
#   3. Chain-of-thought (hidden) — the model is instructed to reason step-by-step
#                      internally before writing the JSON so conclusions are grounded.
#   4. Secure fix quality — the rewrite must use the language's idiomatic safe API,
#                      not just wrap the insecure call in a try/except.
#   5. Risk calibration — the score must account for real-world exploitability
#                      (e.g. unauthenticated path vs. admin-only), not just theoretical severity.

_SYSTEM_PROMPT = """\
You are a senior application-security engineer with more than ten years of \
hands-on experience in penetration testing, secure code review, threat \
modelling (STRIDE / DREAD), and OWASP Top 10 / CWE remediation across \
Python, JavaScript, Java, Go, and Rust codebases.

You have been asked to review source code that an automated scanner has \
already analysed.  Your review must be precise, actionable, and code-specific \
— it must read as though you wrote it after personally reading every line of \
the submitted code.

──────────────────────────────────────────────────────────────
INTERNAL REASONING (do NOT include in output)
──────────────────────────────────────────────────────────────
Before writing the JSON, silently reason through the following steps:

Step 1 — Triage
  For every scanner finding, identify: the exact line and construct at fault, \
the root cause (e.g. missing input validation, use of deprecated API, \
hardcoded secret), and the attack surface (local, network, authenticated, \
unauthenticated).

Step 2 — Exploit scenario
  Describe, in concrete terms, how a real attacker would exploit each issue \
in THIS codebase — not a hypothetical application.  Name the specific variable \
or function call that is the entry point.

Step 3 — Fix strategy
  For each issue, identify the idiomatic safe alternative for the language \
(e.g. parameterised queries instead of f-string SQL; ast.literal_eval instead \
of eval(); subprocess with a list argument instead of shell=True).  Verify \
your fix does not break the surrounding logic.

Step 4 — Risk calibration
  Assign a risk score by weighing:
    • Severity of impact (data exfiltration, RCE, auth bypass, DoS …)
    • Exploitability (unauthenticated one-click vs. admin-only edge-case)
    • Breadth (affects all users vs. a single endpoint)
  Use the full 1–10 scale — do not cluster scores around 5–7.

──────────────────────────────────────────────────────────────
OUTPUT CONTRACT
──────────────────────────────────────────────────────────────
Return a single JSON object with EXACTLY these three keys and NO other text:

{
  "explanation": "<string>",
  "secure_version": "<string>",
  "risk_score": <integer 1-10>
}

Key rules — read carefully:

"explanation"
  • Write one paragraph per detected issue.
  • Open each paragraph with the issue label and exact location, e.g.:
      "[SQL Injection – line 14] The query is built by concatenating the
       user-supplied `username` parameter directly into an f-string …"
  • Explain the specific variable / API that is dangerous, why that construct
    is exploitable, and give a realistic attack payload or scenario for THIS
    code (not a textbook example).
  • Conclude each paragraph with one sentence summarising the business impact
    (data breach, account takeover, full server compromise, etc.).
  • If the scanner found NO issues, confirm the code is clean and name the
    specific constructs that make it safe (e.g. "parameterised query on line 9",
    "no use of eval/exec", etc.).
  • FORBIDDEN: do not write "this is a common vulnerability", "always validate
    input", or any other generic advice that could apply to any codebase.

"secure_version"
  • Return the ENTIRE source file with every vulnerability fixed.
  • Mark each changed line with an inline comment using the prefix
    "# SECURITY FIX:" (Python) or "// SECURITY FIX:" (JS/TS/Java/C/Go/Rust).
  • The comment must name the vulnerability class and the safe API used, e.g.:
      "# SECURITY FIX: SQL injection – replaced f-string with parameterised query"
  • Use the language's idiomatic safe API, not a band-aid wrapper.
  • Preserve all original logic, variable names, and formatting outside the
    changed lines.
  • Do NOT add unrelated refactoring or style changes.

"risk_score"
  • Integer from 1 (no meaningful risk) to 10 (critical, unauthenticated RCE
    or equivalent).
  • Score must reflect the WORST issue in this specific code.
  • Reference points:
      1–2  Informational / best-practice concerns only
      3–4  Low: exploitable only under unusual conditions or requires auth
      5–6  Medium: exploitable by an authenticated user in a typical deployment
      7–8  High: exploitable by any user, significant data or system impact
      9–10 Critical: unauthenticated, trivial to exploit, catastrophic impact

Return ONLY the JSON object — no markdown fences, no preamble, no trailing text.
"""


def _build_user_message(code: str, language: str, issues: List[ScanIssue]) -> str:
    """
    Construct the user-turn message sent to the model.

    The message is structured so the model sees:
    1. The language (for language-specific safe-API selection).
    2. A numbered table of scanner findings with line, severity, type, and
       message — giving the model precise anchors to reference in its review.
    3. The full source code in a fenced block so the model can cross-reference
       findings with the actual code context.
    """
    if issues:
        header = f"{'#':<4}{'Line':<8}{'Severity':<12}{'Type':<30}Message"
        separator = "-" * len(header)
        rows = [
            f"{idx:<4}{i.line:<8}{i.severity:<12}{i.type:<30}{i.message}"
            for idx, i in enumerate(issues, start=1)
        ]
        issues_section = "\n".join([header, separator, *rows])
    else:
        issues_section = "(none — the automated scanner found no issues)"

    return (
        f"Language: {language}\n\n"
        f"Scanner findings ({len(issues)} total):\n"
        f"{issues_section}\n\n"
        f"Source code to review:\n"
        f"```{language}\n{code}\n```\n\n"
        f"Perform your internal reasoning steps, then return the JSON review."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_ai_review(
    code: str,
    language: str,
    issues: List[ScanIssue],
) -> Optional[AiReview]:
    """
    Request an AI-powered security review from OpenAI.

    Parameters
    ----------
    code:
        Raw source code string.
    language:
        Programming language (e.g. ``"python"`` or ``"javascript"``).
    issues:
        Findings already detected by the regex + AST scanner.

    Returns
    -------
    AiReview | None
        Structured review object, or ``None`` if the API key is not
        configured or if any error occurs during the API call.
    """
    if not _OPENAI_API_KEY:
        logger.debug(
            "OPENAI_API_KEY is not set – skipping AI review."
        )
        return None

    # Import here so the module can be imported in test environments that
    # don't have the openai package installed (the package is optional at
    # import time; the test suite mocks it at the function level).
    try:
        from openai import AsyncOpenAI  # noqa: PLC0415
    except ImportError:
        logger.warning(
            "openai package is not installed – AI review is unavailable. "
            "Run: pip install openai"
        )
        return None

    client = AsyncOpenAI(api_key=_OPENAI_API_KEY)

    user_message = _build_user_message(code, language, issues)

    try:
        response = await client.chat.completions.create(
            model=_OPENAI_MODEL,
            response_format={"type": "json_object"},
            max_tokens=_MAX_TOKENS,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as exc:
        logger.warning("OpenAI API call failed: %s", exc)
        return None

    raw_content = (response.choices[0].message.content or "").strip()

    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.warning(
            "AI review response was not valid JSON: %s – raw: %.200s",
            exc,
            raw_content,
        )
        return None

    # Validate and coerce via Pydantic.
    try:
        # Normalise risk_score: accept both "risk_score" and "riskScore" keys.
        if "riskScore" in payload and "risk_score" not in payload:
            payload["risk_score"] = payload.pop("riskScore")
        return AiReview(
            explanation=str(payload.get("explanation", "")),
            secure_version=str(payload.get("secure_version", "")),
            risk_score=int(payload.get("risk_score", 1)),
        )
    except Exception as exc:
        logger.warning(
            "Failed to parse AI review payload into AiReview model: %s – payload: %.200s",
            exc,
            payload,
        )
        return None
