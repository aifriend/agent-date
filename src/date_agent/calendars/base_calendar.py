"""Base calendar interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Set

from date_agent.core.constants import WEEKEND_DAYS


@dataclass
class Holiday:
    """Represents a single holiday.

    Attributes:
        date: The holiday date.
        name: Holiday name in English.
        name_localized: Holiday name in local language.
        holiday_type: Type of holiday (national, banking, etc.).
        observed: Whether the holiday is observed.
    """

    date: date
    name: str
    name_localized: Optional[str] = None
    holiday_type: str = "national"
    observed: bool = True


class BaseCalendar(ABC):
    """Abstract base class for calendar systems.

    All calendar implementations must inherit from this class
    and provide holiday data for their specific system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Calendar system identifier (e.g., 'PERU_BANKING')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the calendar."""
        ...

    @property
    @abstractmethod
    def timezone(self) -> str:
        """Default timezone for this calendar (IANA format)."""
        ...

    @property
    def weekend_days(self) -> Set[int]:
        """Weekend days (0=Monday, 6=Sunday).

        Default is Saturday and Sunday. Override for different weekend definitions.
        """
        return WEEKEND_DAYS

    @abstractmethod
    def get_holidays(self, year: int) -> List[Holiday]:
        """Get all holidays for a given year.

        Args:
            year: The year to get holidays for.

        Returns:
            List of Holiday objects for the year.
        """
        ...

    def get_holidays_in_range(
        self, start_date: date, end_date: date
    ) -> List[Holiday]:
        """Get holidays within a date range.

        Args:
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).

        Returns:
            List of holidays in the range.
        """
        holidays = []

        # Get holidays for all years in range
        for year in range(start_date.year, end_date.year + 1):
            year_holidays = self.get_holidays(year)
            for holiday in year_holidays:
                if start_date <= holiday.date <= end_date:
                    holidays.append(holiday)

        return sorted(holidays, key=lambda h: h.date)

    def is_holiday(self, d: date) -> bool:
        """Check if a date is a holiday.

        Args:
            d: The date to check.

        Returns:
            True if the date is a holiday.
        """
        holidays = self.get_holidays(d.year)
        return any(h.date == d and h.observed for h in holidays)

    def get_holiday_info(self, d: date) -> Optional[Holiday]:
        """Get holiday information for a date.

        Args:
            d: The date to check.

        Returns:
            Holiday object if the date is a holiday, None otherwise.
        """
        holidays = self.get_holidays(d.year)
        for h in holidays:
            if h.date == d:
                return h
        return None

    def is_weekend(self, d: date) -> bool:
        """Check if a date is a weekend.

        Args:
            d: The date to check.

        Returns:
            True if the date is a weekend day.
        """
        return d.weekday() in self.weekend_days

    def is_business_day(self, d: date) -> bool:
        """Check if a date is a business day.

        A business day is neither a weekend nor a holiday.

        Args:
            d: The date to check.

        Returns:
            True if the date is a business day.
        """
        return not self.is_weekend(d) and not self.is_holiday(d)

    def get_business_days_in_range(
        self, start_date: date, end_date: date
    ) -> List[date]:
        """Get all business days in a range.

        Args:
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).

        Returns:
            List of business day dates.
        """
        business_days = []
        current = start_date
        while current <= end_date:
            if self.is_business_day(current):
                business_days.append(current)
            current += timedelta(days=1)
        return business_days

    def count_business_days(self, start_date: date, end_date: date) -> int:
        """Count business days in a range.

        Args:
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).

        Returns:
            Number of business days.
        """
        return len(self.get_business_days_in_range(start_date, end_date))

    def add_business_days(self, start_date: date, days: int) -> date:
        """Add business days to a date.

        Args:
            start_date: Starting date.
            days: Number of business days to add (can be negative).

        Returns:
            Resulting date.
        """
        if days == 0:
            return start_date

        direction = 1 if days > 0 else -1
        remaining = abs(days)
        current = start_date

        while remaining > 0:
            current += timedelta(days=direction)
            if self.is_business_day(current):
                remaining -= 1

        return current

    def next_business_day(self, d: date) -> date:
        """Get the next business day.

        If the date is a business day, returns the next business day.

        Args:
            d: Starting date.

        Returns:
            Next business day.
        """
        return self.add_business_days(d, 1)

    def previous_business_day(self, d: date) -> date:
        """Get the previous business day.

        If the date is a business day, returns the previous business day.

        Args:
            d: Starting date.

        Returns:
            Previous business day.
        """
        return self.add_business_days(d, -1)

    def adjust_to_business_day(self, d: date, forward: bool = True) -> date:
        """Adjust a date to a business day if it isn't one.

        Args:
            d: The date to adjust.
            forward: If True, move forward; if False, move backward.

        Returns:
            The same date if it's a business day, otherwise the nearest
            business day in the specified direction.
        """
        if self.is_business_day(d):
            return d

        direction = 1 if forward else -1
        current = d

        while not self.is_business_day(current):
            current += timedelta(days=direction)

        return current
