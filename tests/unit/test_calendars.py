"""Unit tests for calendar systems."""

import pytest
from datetime import date

from date_agent.calendars import get_calendar, GregorianCalendar, PeruBankingCalendar


class TestGregorianCalendar:
    """Tests for the Gregorian calendar."""

    @pytest.fixture
    def calendar(self) -> GregorianCalendar:
        return GregorianCalendar()

    def test_no_holidays(self, calendar):
        """Gregorian calendar should have no holidays."""
        holidays = calendar.get_holidays(2024)
        assert holidays == []

    def test_is_weekend_saturday(self, calendar):
        """Test Saturday is weekend."""
        # July 20, 2024 is Saturday
        assert calendar.is_weekend(date(2024, 7, 20))

    def test_is_weekend_sunday(self, calendar):
        """Test Sunday is weekend."""
        # July 21, 2024 is Sunday
        assert calendar.is_weekend(date(2024, 7, 21))

    def test_is_not_weekend_monday(self, calendar):
        """Test Monday is not weekend."""
        # July 15, 2024 is Monday
        assert not calendar.is_weekend(date(2024, 7, 15))

    def test_is_business_day_weekday(self, calendar):
        """Test weekday is business day."""
        assert calendar.is_business_day(date(2024, 7, 15))  # Monday

    def test_is_not_business_day_weekend(self, calendar):
        """Test weekend is not business day."""
        assert not calendar.is_business_day(date(2024, 7, 20))  # Saturday

    def test_count_business_days(self, calendar):
        """Test business day count for a week."""
        # July 15-21, 2024 (Mon-Sun)
        count = calendar.count_business_days(date(2024, 7, 15), date(2024, 7, 21))
        assert count == 5  # Mon-Fri

    def test_add_business_days(self, calendar):
        """Test adding business days."""
        # From Monday July 15, add 5 business days = Monday July 22
        result = calendar.add_business_days(date(2024, 7, 15), 5)
        assert result == date(2024, 7, 22)

    def test_subtract_business_days(self, calendar):
        """Test subtracting business days."""
        # From Monday July 22, subtract 5 business days = Monday July 15
        result = calendar.add_business_days(date(2024, 7, 22), -5)
        assert result == date(2024, 7, 15)


class TestPeruBankingCalendar:
    """Tests for the Peru banking calendar."""

    @pytest.fixture
    def calendar(self) -> PeruBankingCalendar:
        return PeruBankingCalendar()

    def test_has_holidays_2024(self, calendar):
        """Peru calendar should have holidays for 2024."""
        holidays = calendar.get_holidays(2024)
        assert len(holidays) > 0

    def test_fiestas_patrias_2024(self, calendar):
        """Test Fiestas Patrias (July 28-29) are holidays."""
        holidays = calendar.get_holidays(2024)
        holiday_dates = {h.date for h in holidays}

        assert date(2024, 7, 28) in holiday_dates
        assert date(2024, 7, 29) in holiday_dates

    def test_new_year_2024(self, calendar):
        """Test New Year's Day is a holiday."""
        holidays = calendar.get_holidays(2024)
        holiday_dates = {h.date for h in holidays}

        assert date(2024, 1, 1) in holiday_dates

    def test_is_holiday_fiestas_patrias(self, calendar):
        """Test is_holiday for Fiestas Patrias."""
        assert calendar.is_holiday(date(2024, 7, 28))
        assert calendar.is_holiday(date(2024, 7, 29))

    def test_is_not_holiday_regular_day(self, calendar):
        """Test is_holiday returns False for regular days."""
        assert not calendar.is_holiday(date(2024, 7, 15))

    def test_is_not_business_day_holiday(self, calendar):
        """Test holiday is not a business day."""
        assert not calendar.is_business_day(date(2024, 7, 28))

    def test_is_business_day_regular_weekday(self, calendar):
        """Test regular weekday is business day."""
        assert calendar.is_business_day(date(2024, 7, 15))

    def test_holiday_name_localized(self, calendar):
        """Test holiday has Spanish name."""
        holiday_info = calendar.get_holiday_info(date(2024, 7, 28))

        assert holiday_info is not None
        assert holiday_info.name == "Independence Day"
        assert holiday_info.name_localized == "Fiestas Patrias"

    def test_holidays_in_range(self, calendar):
        """Test getting holidays in a date range."""
        holidays = calendar.get_holidays_in_range(
            date(2024, 7, 1),
            date(2024, 7, 31),
        )

        # Should include Fiestas Patrias (July 28-29) and possibly July 23 (Air Force Day)
        assert len(holidays) >= 2
        holiday_dates = {h.date for h in holidays}
        assert date(2024, 7, 28) in holiday_dates
        assert date(2024, 7, 29) in holiday_dates

    def test_add_business_days_skips_holiday(self, calendar):
        """Test adding business days skips holidays."""
        # July 25, 2024 is Thursday
        # Add 1 business day should be July 26 (Friday)
        result = calendar.add_business_days(date(2024, 7, 25), 1)
        assert result == date(2024, 7, 26)

        # Add 2 more business days from July 26 should skip weekend and holidays
        # July 27 (Sat), 28 (Sun+Holiday), 29 (Mon+Holiday), so next is July 30 (Tue)
        result = calendar.add_business_days(date(2024, 7, 26), 2)
        assert result == date(2024, 7, 31)  # Skip 27 (Sat), 28, 29, 30 is first BD

    def test_year_not_available(self, calendar):
        """Test error for year without data."""
        with pytest.raises(ValueError, match="not available"):
            calendar.get_holidays(2020)

    def test_timezone(self, calendar):
        """Test Peru timezone is correct."""
        assert calendar.timezone == "America/Lima"


class TestGetCalendar:
    """Tests for the get_calendar factory function."""

    def test_get_gregorian(self):
        """Test getting Gregorian calendar."""
        cal = get_calendar("GREGORIAN")
        assert isinstance(cal, GregorianCalendar)

    def test_get_peru_banking(self):
        """Test getting Peru banking calendar."""
        cal = get_calendar("PERU_BANKING")
        assert isinstance(cal, PeruBankingCalendar)

    def test_case_insensitive(self):
        """Test calendar names are case-insensitive."""
        cal = get_calendar("gregorian")
        assert isinstance(cal, GregorianCalendar)

    def test_invalid_calendar(self):
        """Test error for invalid calendar system."""
        with pytest.raises(ValueError, match="Unsupported"):
            get_calendar("INVALID_CALENDAR")
