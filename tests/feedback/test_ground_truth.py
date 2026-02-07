"""Tests for the independent ground truth computer.

Cross-validates against the existing GROUND_TRUTH_PERIODS from
test_complex_temporal_ground_truth.py to ensure consistency.
"""

import pytest
from datetime import date

from date_agent.feedback.ground_truth import GroundTruthComputer


# Reference date: July 15, 2024 (Monday) - same as test suite
REFERENCE_DATE = date(2024, 7, 15)

# Known ground truth from test_complex_temporal_ground_truth.py
EXISTING_GROUND_TRUTH = {
    "today": ("2024-07-15", "2024-07-15", 1),
    "yesterday": ("2024-07-14", "2024-07-14", 1),
    "last_week": ("2024-07-08", "2024-07-14", 7),
    "week_before_last": ("2024-07-01", "2024-07-07", 7),
    "this_month": ("2024-07-01", "2024-07-31", 31),
    "last_month": ("2024-06-01", "2024-06-30", 30),
    "this_quarter": ("2024-07-01", "2024-09-30", 92),
    "last_quarter": ("2024-04-01", "2024-06-30", 91),
    "this_year": ("2024-01-01", "2024-12-31", 366),  # Leap year
    "last_year": ("2023-01-01", "2023-12-31", 365),
    "ytd": ("2024-01-01", "2024-07-15", 197),
}


class TestGroundTruthComputer:
    """Validate the ground truth computer against known values."""

    @pytest.fixture
    def gt(self):
        return GroundTruthComputer(REFERENCE_DATE)

    @pytest.mark.parametrize(
        "period_type,expected",
        list(EXISTING_GROUND_TRUTH.items()),
        ids=list(EXISTING_GROUND_TRUTH.keys()),
    )
    def test_matches_existing_ground_truth(self, gt, period_type, expected):
        """Each period must match the existing test suite's ground truth."""
        start, end, days = gt.compute_period(period_type)
        exp_start, exp_end, exp_days = expected
        assert start == exp_start, f"{period_type}: start {start} != {exp_start}"
        assert end == exp_end, f"{period_type}: end {end} != {exp_end}"
        assert days == exp_days, f"{period_type}: days {days} != {exp_days}"

    def test_named_quarter_q1_2024_leap_year(self, gt):
        """Q1 2024 has 91 days (Jan 31 + Feb 29 + Mar 31)."""
        start, end, days = gt.compute_period(
            "named_quarter", {"quarter": 1, "year": 2024}
        )
        assert start == "2024-01-01"
        assert end == "2024-03-31"
        assert days == 91  # Leap year

    def test_named_quarter_q3_2024(self, gt):
        """Q3 2024: Jul 1 - Sep 30 = 92 days."""
        start, end, days = gt.compute_period(
            "named_quarter", {"quarter": 3, "year": 2024}
        )
        assert start == "2024-07-01"
        assert end == "2024-09-30"
        assert days == 92

    def test_named_month_february_2024(self, gt):
        """February 2024 has 29 days (leap year)."""
        start, end, days = gt.compute_period(
            "named_month", {"month": 2, "year": 2024}
        )
        assert start == "2024-02-01"
        assert end == "2024-02-29"
        assert days == 29

    def test_named_month_june_2024(self, gt):
        """June 2024 has 30 days."""
        start, end, days = gt.compute_period(
            "named_month", {"month": 6, "year": 2024}
        )
        assert start == "2024-06-01"
        assert end == "2024-06-30"
        assert days == 30

    def test_named_year_2023(self, gt):
        """2023 is not a leap year: 365 days."""
        start, end, days = gt.compute_period("named_year", {"year": 2023})
        assert start == "2023-01-01"
        assert end == "2023-12-31"
        assert days == 365

    def test_named_year_2024(self, gt):
        """2024 is a leap year: 366 days."""
        start, end, days = gt.compute_period("named_year", {"year": 2024})
        assert start == "2024-01-01"
        assert end == "2024-12-31"
        assert days == 366

    def test_last_3_days(self, gt):
        """Last 3 days (rolling window, includes today)."""
        start, end, days = gt.compute_period("last_3_days")
        assert start == "2024-07-12"
        assert end == "2024-07-15"  # Includes ref date
        assert days == 4  # ref-3 to ref inclusive

    def test_last_2_weeks(self, gt):
        """Last 2 weeks (rolling window, includes today)."""
        start, end, days = gt.compute_period("last_2_weeks")
        assert start == "2024-07-01"
        assert end == "2024-07-15"  # Includes ref date
        assert days == 15

    def test_last_3_months(self, gt):
        """Last 3 months (rolling from first of month-3 to ref)."""
        start, end, days = gt.compute_period("last_3_months")
        assert start == "2024-04-01"
        assert end == "2024-07-15"  # Includes ref date

    def test_custom_range(self, gt):
        """Custom date range."""
        start, end, days = gt.compute_period(
            "custom", {"start": "2024-03-01", "end": "2024-03-31"}
        )
        assert start == "2024-03-01"
        assert end == "2024-03-31"
        assert days == 31

    def test_days_ago(self, gt):
        """Days ago: 5 days ago from July 15 = July 10."""
        start, end, days = gt.compute_period("days_ago", {"n": 5})
        assert start == "2024-07-10"
        assert end == "2024-07-10"
        assert days == 1

    def test_recent(self, gt):
        """Recent: agent convention ref-7 to ref (8 days)."""
        start, end, days = gt.compute_period("recent")
        assert start == "2024-07-08"
        assert end == "2024-07-15"
        assert days == 8

    def test_last_weekend(self, gt):
        """Last weekend before Monday July 15 = Sat Jul 13 - Sun Jul 14."""
        start, end, days = gt.compute_period("last_weekend")
        assert start == "2024-07-13"  # Saturday
        assert end == "2024-07-14"  # Sunday
        assert days == 2

    def test_this_week(self, gt):
        """This week: Mon Jul 15 - Sun Jul 21."""
        start, end, days = gt.compute_period("this_week")
        assert start == "2024-07-15"
        assert end == "2024-07-21"
        assert days == 7


class TestGroundTruthSelfConsistency:
    """Verify that all computed ground truth values are self-consistent."""

    @pytest.fixture
    def gt(self):
        return GroundTruthComputer(REFERENCE_DATE)

    def test_all_day_counts_correct(self, gt):
        """Verify (end - start).days + 1 == calendar_days for all periods."""
        periods = [
            "today", "yesterday", "this_week", "last_week",
            "week_before_last", "this_month", "last_month",
            "this_quarter", "last_quarter", "this_year", "last_year", "ytd",
            "recent", "last_weekend",
        ]
        for ptype in periods:
            start_str, end_str, days = gt.compute_period(ptype)
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str)
            computed = (end - start).days + 1
            assert computed == days, f"{ptype}: {computed} != {days}"

    def test_all_four_quarters_sum_to_year(self, gt):
        """Q1 + Q2 + Q3 + Q4 of 2024 = 366 days (leap year)."""
        total = 0
        for q in range(1, 5):
            _, _, days = gt.compute_period(
                "named_quarter", {"quarter": q, "year": 2024}
            )
            total += days
        assert total == 366
