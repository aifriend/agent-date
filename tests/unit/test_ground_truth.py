"""Ground truth validation tests for calendar accuracy.

These tests validate the Date Reasoning Agent's calendar calculations
against multiple external sources of truth:

1. Python's `holidays` library (official government sources)
2. Algorithmic Easter calculation (computus)
3. Known historical dates
4. Python's calendar module

The goal is to ensure HIGH CONFIDENCE that all date calculations
are mathematically and calendrically correct.
"""

import pytest
from datetime import date, timedelta
import calendar as cal_module
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import our modules
from date_agent.calendars.peru_banking_validated import (
    compute_easter,
    compute_maundy_thursday,
    compute_good_friday,
    PeruBankingValidatedCalendar,
    get_validated_peru_calendar,
    HOLIDAYS_AVAILABLE,
)
from date_agent.calendars import get_calendar

# Try to import holidays library for cross-validation
try:
    import holidays as holidays_lib
    HAS_HOLIDAYS_LIB = True
except ImportError:
    HAS_HOLIDAYS_LIB = False


# =============================================================================
# EASTER ALGORITHM TESTS (Computus)
# =============================================================================

class TestEasterAlgorithm:
    """Test the Easter calculation algorithm against known dates.

    Easter dates are well-documented and can be verified against multiple
    authoritative sources including:
    - US Naval Observatory
    - Old Farmer's Almanac
    - Wikipedia
    """

    # Known Easter Sunday dates (verified against multiple sources)
    KNOWN_EASTER_DATES = [
        (2020, date(2020, 4, 12)),
        (2021, date(2021, 4, 4)),
        (2022, date(2022, 4, 17)),
        (2023, date(2023, 4, 9)),
        (2024, date(2024, 3, 31)),
        (2025, date(2025, 4, 20)),
        (2026, date(2026, 4, 5)),
        (2027, date(2027, 3, 28)),
        (2028, date(2028, 4, 16)),
        (2029, date(2029, 4, 1)),
        (2030, date(2030, 4, 21)),
    ]

    @pytest.mark.parametrize("year,expected", KNOWN_EASTER_DATES)
    def test_easter_calculation(self, year: int, expected: date):
        """Verify Easter calculation against known dates."""
        computed = compute_easter(year)
        assert computed == expected, (
            f"Easter {year}: computed {computed}, expected {expected}"
        )

    @pytest.mark.parametrize("year,expected", KNOWN_EASTER_DATES)
    def test_maundy_thursday_is_3_days_before_easter(self, year: int, expected: date):
        """Maundy Thursday is always 3 days before Easter Sunday."""
        easter = compute_easter(year)
        maundy = compute_maundy_thursday(year)
        assert maundy == easter - timedelta(days=3)

    @pytest.mark.parametrize("year,expected", KNOWN_EASTER_DATES)
    def test_good_friday_is_2_days_before_easter(self, year: int, expected: date):
        """Good Friday is always 2 days before Easter Sunday."""
        easter = compute_easter(year)
        good_fri = compute_good_friday(year)
        assert good_fri == easter - timedelta(days=2)

    def test_easter_range_constraint(self):
        """Easter must fall between March 22 and April 25 (inclusive)."""
        for year in range(2000, 2100):
            easter = compute_easter(year)
            assert easter >= date(year, 3, 22), f"Easter {year} too early: {easter}"
            assert easter <= date(year, 4, 25), f"Easter {year} too late: {easter}"

    def test_easter_is_always_sunday(self):
        """Easter must always be a Sunday (weekday = 6)."""
        for year in range(2000, 2100):
            easter = compute_easter(year)
            assert easter.weekday() == 6, f"Easter {year} is not Sunday: {easter}"


# =============================================================================
# CROSS-VALIDATION WITH HOLIDAYS LIBRARY
# =============================================================================

@pytest.mark.skipif(not HAS_HOLIDAYS_LIB, reason="holidays library not installed")
class TestHolidaysLibraryValidation:
    """Cross-validate our calendar against the holidays library.

    The `holidays` library sources data from official government publications
    and is maintained by an active open-source community.
    """

    @pytest.fixture
    def validated_calendar(self):
        return get_validated_peru_calendar()

    @pytest.mark.parametrize("year", [2024, 2025, 2026])
    def test_all_library_holidays_included(self, validated_calendar, year: int):
        """All holidays from the library should be in our calendar.

        Note: Easter Sunday is in the holidays library but NOT a Peru
        banking holiday (banks are closed on Maundy Thursday and Good Friday,
        but Easter Sunday is already a non-business day because it's Sunday).
        """
        validation = validated_calendar.validate_against_library(year)

        # Easter Sunday is in library but not in Peru banking calendar
        # (it's a Sunday anyway, so banks would be closed regardless)
        easter_sunday = compute_easter(year)
        allowed_missing = {easter_sunday.isoformat()}

        missing = [d for d in validation["missing"] if d not in allowed_missing]

        assert len(missing) == 0, (
            f"Year {year}: Missing holidays from library (excluding Easter Sunday): {missing}"
        )

    @pytest.mark.parametrize("year", [2024, 2025, 2026])
    def test_easter_dates_match_library(self, validated_calendar, year: int):
        """Our computed Easter dates should match the library."""
        pe_holidays = holidays_lib.Peru(years=year)

        # Find Maundy Thursday in library
        maundy_lib = None
        good_fri_lib = None
        for d, name in pe_holidays.items():
            if "Maundy" in name or "Jueves Santo" in name.lower():
                maundy_lib = d
            if "Good Friday" in name or "Viernes Santo" in name.lower():
                good_fri_lib = d

        maundy_computed = compute_maundy_thursday(year)
        good_fri_computed = compute_good_friday(year)

        if maundy_lib:
            assert maundy_computed == maundy_lib, (
                f"Maundy Thursday {year}: computed {maundy_computed}, library {maundy_lib}"
            )
        if good_fri_lib:
            assert good_fri_computed == good_fri_lib, (
                f"Good Friday {year}: computed {good_fri_computed}, library {good_fri_lib}"
            )

    def test_peru_fiestas_patrias_dates(self, validated_calendar):
        """Peru Independence Day is always July 28-29."""
        for year in [2024, 2025, 2026]:
            holidays_list = validated_calendar.get_holidays(year)
            july_28 = date(year, 7, 28)
            july_29 = date(year, 7, 29)

            holiday_dates = {h.date for h in holidays_list}
            assert july_28 in holiday_dates, f"Missing July 28 {year}"
            assert july_29 in holiday_dates, f"Missing July 29 {year}"


# =============================================================================
# ORIGINAL CALENDAR VALIDATION
# =============================================================================

class TestOriginalCalendarAgainstValidated:
    """Compare the original hardcoded calendar against the validated one."""

    @pytest.fixture
    def original_calendar(self):
        return get_calendar("PERU_BANKING")

    @pytest.fixture
    def validated_calendar(self):
        return get_validated_peru_calendar()

    @pytest.mark.parametrize("year", [2024, 2025, 2026])
    def test_original_matches_validated(self, original_calendar, validated_calendar, year: int):
        """Original hardcoded calendar should match validated calendar."""
        original = {h.date for h in original_calendar.get_holidays(year)}
        validated = {h.date for h in validated_calendar.get_holidays(year)}

        missing = validated - original
        extra = original - validated

        # Allow for slight differences (e.g., Easter Sunday inclusion)
        assert len(missing) <= 1, f"Year {year}: Original missing: {missing}"
        assert len(extra) <= 1, f"Year {year}: Original has extra: {extra}"


# =============================================================================
# CALENDAR ARITHMETIC VALIDATION
# =============================================================================

class TestCalendarArithmetic:
    """Validate basic calendar arithmetic against Python's calendar module."""

    @pytest.mark.parametrize("year,month,expected_days", [
        (2024, 1, 31),  # January
        (2024, 2, 29),  # February (leap year)
        (2025, 2, 28),  # February (non-leap year)
        (2024, 4, 30),  # April
        (2024, 7, 31),  # July
    ])
    def test_month_lengths(self, year: int, month: int, expected_days: int):
        """Verify month lengths match Python's calendar module."""
        _, days = cal_module.monthrange(year, month)
        assert days == expected_days

    @pytest.mark.parametrize("year,is_leap", [
        (2020, True),
        (2024, True),
        (2021, False),
        (2025, False),
        (2100, False),  # Century years divisible by 400 only
        (2000, True),   # 2000 was a leap year
    ])
    def test_leap_year_detection(self, year: int, is_leap: bool):
        """Verify leap year detection."""
        assert cal_module.isleap(year) == is_leap

    def test_quarter_boundaries(self):
        """Verify quarter boundaries are correct."""
        quarters = {
            1: (1, 1, 3, 31),   # Q1: Jan 1 - Mar 31
            2: (4, 1, 6, 30),   # Q2: Apr 1 - Jun 30
            3: (7, 1, 9, 30),   # Q3: Jul 1 - Sep 30
            4: (10, 1, 12, 31), # Q4: Oct 1 - Dec 31
        }

        for quarter, (start_month, start_day, end_month, end_day) in quarters.items():
            # Verify month assignments
            for month in range(start_month, end_month + 1):
                computed_quarter = (month - 1) // 3 + 1
                assert computed_quarter == quarter, (
                    f"Month {month} should be Q{quarter}, got Q{computed_quarter}"
                )


# =============================================================================
# DATE AGENT INTEGRATION VALIDATION
# =============================================================================

class TestDateAgentGroundTruth:
    """Validate the Date Agent's outputs against ground truth."""

    @pytest.fixture
    def agent(self):
        from date_agent.agent.date_agent import DateReasoningAgent
        from date_agent.core.config import DateAgentConfig
        config = DateAgentConfig()
        return DateReasoningAgent(config)

    @pytest.mark.asyncio
    async def test_quarter_dates_correct(self, agent):
        """Verify named quarter dates are mathematically correct."""
        quarters_2024 = [
            ("Q1 2024", "2024-01-01", "2024-03-31"),
            ("Q2 2024", "2024-04-01", "2024-06-30"),
            ("Q3 2024", "2024-07-01", "2024-09-30"),
            ("Q4 2024", "2024-10-01", "2024-12-31"),
        ]

        for query, expected_start, expected_end in quarters_2024:
            result = await agent.process_query(query)
            assert result["success"], f"Query '{query}' failed"
            assert result["start_date"] == expected_start, (
                f"{query}: start_date {result['start_date']} != {expected_start}"
            )
            assert result["end_date"] == expected_end, (
                f"{query}: end_date {result['end_date']} != {expected_end}"
            )

    @pytest.mark.asyncio
    async def test_today_matches_system(self, agent):
        """Today's date must match system date."""
        from datetime import date as date_cls
        today = date_cls.today()

        result = await agent.process_query("hoy")
        assert result["success"]
        assert result["start_date"] == today.isoformat()

    @pytest.mark.asyncio
    async def test_yesterday_is_one_day_before_today(self, agent):
        """Yesterday must be exactly one day before today."""
        from datetime import date as date_cls, timedelta
        yesterday = date_cls.today() - timedelta(days=1)

        result = await agent.process_query("ayer")
        assert result["success"]
        assert result["start_date"] == yesterday.isoformat()

    @pytest.mark.asyncio
    async def test_calendar_days_count_correct(self, agent):
        """Verify calendar day counts are mathematically correct."""
        test_cases = [
            ("Q1 2024", 91),   # Jan(31) + Feb(29) + Mar(31) = 91 (leap year)
            ("Q2 2024", 91),   # Apr(30) + May(31) + Jun(30) = 91
            ("Q3 2024", 92),   # Jul(31) + Aug(31) + Sep(30) = 92
            ("Q4 2024", 92),   # Oct(31) + Nov(30) + Dec(31) = 92
            ("Q1 2025", 90),   # Jan(31) + Feb(28) + Mar(31) = 90 (non-leap year)
        ]

        for query, expected_days in test_cases:
            result = await agent.process_query(query)
            assert result["success"], f"Query '{query}' failed"
            assert result["calendar_days"] == expected_days, (
                f"{query}: calendar_days {result['calendar_days']} != {expected_days}"
            )


# =============================================================================
# WEEK CALCULATION VALIDATION
# =============================================================================

class TestWeekCalculations:
    """Validate week calculations follow ISO 8601."""

    def test_week_starts_monday(self):
        """ISO weeks start on Monday (weekday 0)."""
        # Find a known Monday
        monday = date(2024, 1, 1)  # Jan 1, 2024 is a Monday
        assert monday.weekday() == 0, f"Jan 1, 2024 should be Monday"

    def test_week_has_7_days(self):
        """A week always has exactly 7 days."""
        start = date(2024, 1, 1)
        end = start + timedelta(days=6)
        days = (end - start).days + 1
        assert days == 7

    @pytest.mark.parametrize("test_date,expected_iso_week", [
        (date(2024, 1, 1), 1),   # First week of 2024
        (date(2024, 1, 7), 1),   # Still week 1
        (date(2024, 1, 8), 2),   # Week 2 starts
        (date(2024, 12, 30), 1), # Week 1 of 2025 (ISO week year)
    ])
    def test_iso_week_numbers(self, test_date: date, expected_iso_week: int):
        """Verify ISO week numbers are correct."""
        iso_cal = test_date.isocalendar()
        assert iso_cal[1] == expected_iso_week, (
            f"{test_date}: ISO week {iso_cal[1]} != {expected_iso_week}"
        )


# =============================================================================
# BUSINESS DAY VALIDATION
# =============================================================================

class TestBusinessDayValidation:
    """Validate business day calculations."""

    @pytest.fixture
    def calendar(self):
        return get_calendar("PERU_BANKING")

    def test_weekends_are_not_business_days(self, calendar):
        """Saturday and Sunday should never be business days."""
        # Check several weekends
        saturdays = [date(2024, 1, 6), date(2024, 7, 27), date(2025, 3, 1)]
        sundays = [date(2024, 1, 7), date(2024, 7, 28), date(2025, 3, 2)]

        for sat in saturdays:
            assert sat.weekday() == 5, f"{sat} is not Saturday"
            assert not calendar.is_business_day(sat), f"{sat} should not be business day"

        for sun in sundays:
            assert sun.weekday() == 6, f"{sun} is not Sunday"
            assert not calendar.is_business_day(sun), f"{sun} should not be business day"

    def test_holidays_are_not_business_days(self, calendar):
        """All holidays should not be business days."""
        for year in [2024, 2025, 2026]:
            for holiday in calendar.get_holidays(year):
                assert not calendar.is_business_day(holiday.date), (
                    f"Holiday {holiday.date} ({holiday.name}) should not be business day"
                )

    def test_regular_weekdays_are_business_days(self, calendar):
        """Regular weekdays that are not holidays should be business days."""
        # Find some known non-holiday weekdays
        regular_days = [
            date(2024, 1, 2),   # Tuesday after New Year
            date(2024, 7, 30),  # Day after Fiestas Patrias
            date(2024, 8, 1),   # Regular Thursday
        ]

        for d in regular_days:
            assert 0 <= d.weekday() <= 4, f"{d} is not a weekday"
            assert calendar.is_business_day(d), f"{d} should be a business day"


# =============================================================================
# SUMMARY TEST
# =============================================================================

class TestGroundTruthSummary:
    """Summary test that reports overall validation status."""

    def test_ground_truth_validation_summary(self):
        """Print a summary of ground truth validation."""
        print("\n" + "=" * 60)
        print("GROUND TRUTH VALIDATION SUMMARY")
        print("=" * 60)

        # Easter validation
        errors = []
        for year in range(2020, 2031):
            easter = compute_easter(year)
            if easter.weekday() != 6:
                errors.append(f"Easter {year} not Sunday")
            if not (date(year, 3, 22) <= easter <= date(year, 4, 25)):
                errors.append(f"Easter {year} out of range")

        print(f"Easter Algorithm: {'PASS' if not errors else 'FAIL'}")
        if errors:
            for e in errors:
                print(f"  - {e}")

        # Holidays library validation
        if HAS_HOLIDAYS_LIB:
            cal = get_validated_peru_calendar()
            for year in [2024, 2025, 2026]:
                result = cal.validate_against_library(year)
                status = "PASS" if not result.get("missing") else "WARN"
                print(f"Peru {year} vs holidays lib: {status}")
                if result.get("missing"):
                    print(f"  Missing: {result['missing']}")
        else:
            print("Holidays library: NOT INSTALLED")

        print("=" * 60)
        assert not errors, "Ground truth validation failed"
