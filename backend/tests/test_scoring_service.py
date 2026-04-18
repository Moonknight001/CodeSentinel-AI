"""
Unit tests for backend.services.scoring_service.

Run with:
    python -m pytest backend/tests/test_scoring_service.py -v
"""

from __future__ import annotations

import pytest

from backend.services.scoring_service import compute_score


# ===========================================================================
# Clean code (no issues)
# ===========================================================================


class TestNoIssues:
    def test_empty_list_returns_100_excellent(self):
        score, label = compute_score([])
        assert score == 100
        assert label == "Excellent"


# ===========================================================================
# Per-severity deductions
# ===========================================================================


class TestSingleSeverityDeductions:
    def test_critical_deducts_20(self):
        score, _ = compute_score(["CRITICAL"])
        assert score == 80

    def test_high_deducts_20(self):
        score, _ = compute_score(["HIGH"])
        assert score == 80

    def test_medium_deducts_10(self):
        score, _ = compute_score(["MEDIUM"])
        assert score == 90

    def test_low_deducts_5(self):
        score, _ = compute_score(["LOW"])
        assert score == 95

    def test_info_deducts_nothing(self):
        score, _ = compute_score(["INFO"])
        assert score == 100

    def test_unknown_severity_deducts_nothing(self):
        score, _ = compute_score(["UNKNOWN"])
        assert score == 100


# ===========================================================================
# Case-insensitivity
# ===========================================================================


class TestCaseInsensitivity:
    def test_lowercase_severities_accepted(self):
        score, _ = compute_score(["high", "medium", "low"])
        assert score == 100 - 20 - 10 - 5

    def test_mixed_case_severity(self):
        score, _ = compute_score(["High", "Medium"])
        assert score == 100 - 20 - 10

    def test_uppercase_critical(self):
        score, _ = compute_score(["CRITICAL"])
        assert score == 80

    def test_lowercase_critical(self):
        score, _ = compute_score(["critical"])
        assert score == 80


# ===========================================================================
# Accumulation across multiple issues
# ===========================================================================


class TestAccumulation:
    def test_two_highs(self):
        score, _ = compute_score(["HIGH", "HIGH"])
        assert score == 60

    def test_three_highs(self):
        score, _ = compute_score(["HIGH", "HIGH", "HIGH"])
        assert score == 40

    def test_mixed_severities(self):
        # 1 high (20) + 2 medium (20) + 3 low (15) = 55 → 45
        score, _ = compute_score(["HIGH", "MEDIUM", "MEDIUM", "LOW", "LOW", "LOW"])
        assert score == 45

    def test_all_severity_levels(self):
        # critical(20) + high(20) + medium(10) + low(5) + info(0) = 55 → 45
        score, _ = compute_score(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
        assert score == 45


# ===========================================================================
# Floor clamping – score must never go below zero
# ===========================================================================


class TestFloorClamping:
    def test_many_highs_clamps_to_zero(self):
        score, _ = compute_score(["HIGH"] * 10)
        assert score == 0

    def test_many_criticals_clamps_to_zero(self):
        score, _ = compute_score(["CRITICAL"] * 20)
        assert score == 0

    def test_exact_floor(self):
        # 5 HIGH × 20 = 100 deduction → 0
        score, _ = compute_score(["HIGH"] * 5)
        assert score == 0


# ===========================================================================
# Score labels
# ===========================================================================


class TestLabels:
    def test_excellent_at_100(self):
        _, label = compute_score([])
        assert label == "Excellent"

    def test_excellent_lower_boundary(self):
        # score = 90  (2 LOW × 5 = 10 deduction)
        _, label = compute_score(["LOW", "LOW"])
        assert label == "Excellent"

    def test_good_just_below_excellent(self):
        # score = 85  (3 LOW × 5 = 15 deduction)
        _, label = compute_score(["LOW", "LOW", "LOW"])
        assert label == "Good"

    def test_good_lower_boundary(self):
        # score = 70  (1 HIGH + 1 MEDIUM = 30 deduction)
        _, label = compute_score(["HIGH", "MEDIUM"])
        assert label == "Good"

    def test_fair_just_below_good(self):
        # score = 65  (1 HIGH + 1 MEDIUM + 1 LOW = 35 deduction)
        _, label = compute_score(["HIGH", "MEDIUM", "LOW"])
        assert label == "Fair"

    def test_fair_lower_boundary(self):
        # score = 50  (1 HIGH + 3 MEDIUM = 50 deduction)
        _, label = compute_score(["HIGH", "MEDIUM", "MEDIUM", "MEDIUM"])
        assert label == "Fair"

    def test_danger_just_below_fair(self):
        # score = 45  (1 HIGH + 1 MEDIUM + 1 MEDIUM + 1 LOW = 55 deduction → capped at 0? no: 45)
        # 1 high(20) + 2 medium(20) + 3 low(15) = 55 → 45
        _, label = compute_score(["HIGH", "MEDIUM", "MEDIUM", "LOW", "LOW", "LOW"])
        assert label == "خطر"

    def test_danger_at_zero(self):
        _, label = compute_score(["HIGH"] * 10)
        assert label == "خطر"

    @pytest.mark.parametrize("score_severities,expected_label", [
        ([], "Excellent"),
        (["LOW", "LOW"], "Excellent"),          # score 90
        (["MEDIUM"], "Excellent"),              # score 90
        (["HIGH"], "Good"),                     # score 80
        (["HIGH", "MEDIUM"], "Good"),           # score 70
        (["HIGH", "MEDIUM", "LOW"], "Fair"),    # score 65
        (["HIGH", "HIGH", "HIGH", "MEDIUM"], "خطر"),  # score 30
    ])
    def test_label_parametrized(self, score_severities: list[str], expected_label: str):
        _, label = compute_score(score_severities)
        assert label == expected_label
