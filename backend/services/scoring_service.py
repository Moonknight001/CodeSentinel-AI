"""
Code quality scoring service for CodeSentinel AI.

Scoring algorithm
-----------------
Start at 100 points.  For each detected issue, subtract:

  * 20 points – CRITICAL or HIGH severity
  * 10 points – MEDIUM severity
  *  5 points – LOW severity

INFO-level findings carry no point deduction.
The final score is clamped to the range [0, 100].

Score labels
------------
  >= 90  →  "Excellent"
  >= 70  →  "Good"
  >= 50  →  "Fair"
  <  50  →  "خطر"   (Critical / Danger)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Per-severity deduction table
# ---------------------------------------------------------------------------

_DEDUCTIONS: dict[str, int] = {
    "critical": 20,
    "high": 20,
    "medium": 10,
    "low": 5,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_score(severities: list[str]) -> tuple[int, str]:
    """
    Compute a code quality score and its descriptive label.

    Parameters
    ----------
    severities:
        A list of severity strings (e.g. ``["HIGH", "MEDIUM", "LOW"]``).
        Values are normalised to lower-case before lookup so the caller
        may pass any casing.  Unrecognised values (including ``"info"``)
        contribute zero deduction.

    Returns
    -------
    tuple[int, str]
        ``(score, label)`` where *score* is an integer in ``[0, 100]``
        and *label* is one of ``"Excellent"``, ``"Good"``, ``"Fair"``,
        or ``"خطر"``.
    """
    deduction = sum(_DEDUCTIONS.get(s.lower(), 0) for s in severities)
    score = max(0, 100 - deduction)
    return score, _label(score)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _label(score: int) -> str:
    """Map a numeric score to its human-readable label."""
    if score >= 90:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Fair"
    return "خطر"
