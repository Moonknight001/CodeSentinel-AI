"""
Auto-fix service for CodeSentinel AI (Prompt 12).

Sends the user's source code to the OpenAI API and asks it to return a
security-hardened rewrite together with a plain-English summary of every
change made.

Design principles
-----------------
* **Optional** – returns ``None`` immediately when ``OPENAI_API_KEY`` is
  absent; the caller must handle that case gracefully.
* **Resilient** – any API / JSON / validation error is caught and logged;
  the function always returns ``None`` on failure so the endpoint can
  present a friendly message rather than an unhandled exception.
* **Focused prompt** – the system prompt asks *only* for a fix, not a full
  security review, so the model can concentrate on producing correct,
  idiomatic code changes.
* **Structured output** – JSON mode is requested so the response is always
  parseable.

Usage
-----
    from backend.services.fix_service import get_fixed_code

    result = await get_fixed_code(code, "python")
    if result:
        print(result.fixed_code)
        print(result.summary)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
_OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert software security engineer.
Your task is to fix ALL security vulnerabilities in the source code supplied \
by the user and to return ONLY a JSON object — no markdown, no extra text.

JSON schema (return exactly these two keys):

{
  "fixed_code": "<the complete, corrected source file as a single string>",
  "summary": "<a concise bullet-point list of every change made and why>"
}

Rules for "fixed_code":
  • Return the ENTIRE source file with every security issue remediated.
  • Mark each changed line with an inline comment:
      "# SECURITY FIX: <vulnerability class> – <safe API used>"   (Python)
      "// SECURITY FIX: <vulnerability class> – <safe API used>"  (JS/TS)
  • Use the language's idiomatic safe API (parameterised queries, \
ast.literal_eval, subprocess with a list, etc.).
  • Preserve all original logic, variable names, and formatting outside \
the changed lines.
  • Do NOT add unrelated refactoring or style changes.
  • If the code has NO security issues, return it unchanged.

Rules for "summary":
  • List each fix as a short bullet point, e.g.:
      "- Line 14: Replaced f-string SQL query with parameterised query \
(SQL injection)"
  • If nothing was changed, say: "No security issues found — code is clean."
"""


def _build_user_message(code: str, language: str) -> str:
    return (
        f"Language: {language}\n\n"
        f"Source code to fix:\n"
        f"```{language}\n{code}\n```\n\n"
        "Return the JSON object described in the system prompt."
    )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class FixResult:
    """Container for the auto-fix response."""

    fixed_code: str
    summary: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_fixed_code(code: str, language: str) -> FixResult | None:
    """
    Ask the OpenAI API to return a security-hardened version of *code*.

    Parameters
    ----------
    code:
        Raw source code string to fix.
    language:
        Programming language, e.g. ``"python"`` or ``"javascript"``.

    Returns
    -------
    FixResult | None
        Dataclass with ``fixed_code`` and ``summary``, or ``None`` if the
        API key is not configured or if any error occurs.
    """
    if not _OPENAI_API_KEY:
        logger.debug("OPENAI_API_KEY is not set – skipping auto-fix.")
        return None

    try:
        from openai import AsyncOpenAI  # noqa: PLC0415
    except ImportError:
        logger.warning(
            "openai package is not installed – auto-fix is unavailable. "
            "Run: pip install openai"
        )
        return None

    client = AsyncOpenAI(api_key=_OPENAI_API_KEY)
    user_message = _build_user_message(code, language)

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
        logger.warning("OpenAI API call failed (fix): %s", exc)
        return None

    raw_content = (response.choices[0].message.content or "").strip()

    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Auto-fix response was not valid JSON: %s – raw: %.200s",
            exc,
            raw_content,
        )
        return None

    fixed_code = payload.get("fixed_code", "")
    summary = payload.get("summary", "")

    if not isinstance(fixed_code, str) or not fixed_code.strip():
        logger.warning("Auto-fix response missing 'fixed_code' – payload: %.200s", payload)
        return None

    return FixResult(
        fixed_code=fixed_code,
        summary=str(summary) if summary else "Changes applied.",
    )
