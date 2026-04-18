"""
AI review layer for CodeSentinel AI (Prompt 8).

This module calls the OpenAI Chat Completions API to produce a structured
security review of submitted source code.  It augments the deterministic
regex + AST scanner findings with:

* A plain-English **explanation** of every detected vulnerability —
  what makes it dangerous and how an attacker could exploit it.
* A **secure rewrite** of the code with inline comments explaining each fix.
* A **risk score** (integer 1–10) that reflects overall severity and
  exploitability.

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

_SYSTEM_PROMPT = """\
You are an expert application-security engineer performing a code review.
You will be given source code and a list of security issues that an automated
scanner has already detected.

Your job is to return a JSON object with EXACTLY these three keys:

{
  "explanation": "<string>",
  "secure_version": "<string>",
  "risk_score": <integer 1-10>
}

Rules:
- "explanation": A clear, thorough, plain-English explanation of every
  detected security problem.  For each issue explain: (a) what the
  vulnerability is, (b) why it is dangerous, and (c) how an attacker
  could exploit it.  If there are no issues, state that the code looks
  secure and briefly explain why.
- "secure_version": A corrected, security-hardened version of the ENTIRE
  submitted source code.  Add concise inline comments (prefixed with
  "# SECURITY FIX:" or "// SECURITY FIX:") next to every change to explain
  what was fixed and why.  Do not remove unrelated original functionality.
- "risk_score": A single integer from 1 (negligible risk) to 10 (critical,
  immediately exploitable).  Base this on the highest-severity issue found,
  the exploitability, and the potential impact.  1 means no real risk;
  10 means an attacker can trivially take full control of the system.

Return ONLY the JSON object — no markdown fences, no extra text.
"""


def _build_user_message(code: str, language: str, issues: List[ScanIssue]) -> str:
    """Construct the user-turn message sent to the model."""
    if issues:
        issues_text_lines = [
            f"  - Line {i.line} [{i.severity}] {i.type}: {i.message}"
            for i in issues
        ]
        issues_text = "\n".join(issues_text_lines)
    else:
        issues_text = "  (none detected by the automated scanner)"

    return (
        f"Language: {language}\n\n"
        f"Detected issues:\n{issues_text}\n\n"
        f"Source code:\n```{language}\n{code}\n```"
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
