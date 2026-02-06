"""Constants, enums, and mappings for the Date Reasoning Agent."""

from enum import Enum
from typing import Dict
from zoneinfo import ZoneInfo


class CalendarSystem(str, Enum):
    """Supported calendar systems for business day calculations."""

    GREGORIAN = "GREGORIAN"  # Standard calendar (weekends only)
    PERU_BANKING = "PERU_BANKING"  # Peru banking holidays + weekends
    # Future calendar systems (out of scope for initial release)
    # US_FED_RESERVE = "US_FED_RESERVE"
    # NYSE = "NYSE"
    # NASDAQ = "NASDAQ"


class PeriodType(str, Enum):
    """Semantic period types the agent can recognize."""

    # Absolute - single day
    TODAY = "today"
    YESTERDAY = "yesterday"

    # Relative - weeks
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    WEEK_BEFORE_LAST = "week_before_last"  # "semana antepasada" in Spanish

    # Relative - months
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"

    # Relative - quarters
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"

    # Relative - years
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"

    # Year to date
    YTD = "ytd"

    # Named quarters (pattern: Q{1-4}_{year})
    NAMED_QUARTER = "named_quarter"

    # Days ago (pattern: "hace N dias")
    DAYS_AGO = "days_ago"

    # Custom date range (explicit start/end)
    CUSTOM = "custom"


class DateOperation(str, Enum):
    """Atomic date operations for compute_date_range tool."""

    # Add/subtract calendar days
    ADD_CALENDAR_DAYS = "add_calendar_days"
    SUBTRACT_CALENDAR_DAYS = "subtract_calendar_days"

    # Add/subtract business days (respects calendar system)
    ADD_BUSINESS_DAYS = "add_business_days"
    SUBTRACT_BUSINESS_DAYS = "subtract_business_days"

    # Add/subtract weeks
    ADD_WEEKS = "add_weeks"
    SUBTRACT_WEEKS = "subtract_weeks"

    # Add/subtract months
    ADD_MONTHS = "add_months"
    SUBTRACT_MONTHS = "subtract_months"

    # Find specific dates
    NEXT_BUSINESS_DAY = "next_business_day"
    PREVIOUS_BUSINESS_DAY = "previous_business_day"
    MONTH_END = "month_end"
    MONTH_START = "month_start"
    QUARTER_END = "quarter_end"
    QUARTER_START = "quarter_start"
    WEEK_START = "week_start"  # Monday
    WEEK_END = "week_end"  # Sunday


class BoundaryType(str, Enum):
    """How to handle range boundaries."""

    INCLUSIVE = "inclusive"  # [start, end] - both included
    EXCLUSIVE = "exclusive"  # (start, end) - neither included
    START_INCLUSIVE = "start_inclusive"  # [start, end)
    END_INCLUSIVE = "end_inclusive"  # (start, end]


class HolidayType(str, Enum):
    """Types of holidays."""

    NATIONAL = "national"  # National holiday (feriado nacional)
    BANKING = "banking"  # Banking holiday only
    RELIGIOUS = "religious"  # Religious holiday
    REGIONAL = "regional"  # Regional holiday
    OPTIONAL = "optional"  # Optional holiday (some observe, some don't)


# Supported timezone mappings
TIMEZONE_MAPPINGS: Dict[str, ZoneInfo] = {
    "UTC": ZoneInfo("UTC"),
    "America/Lima": ZoneInfo("America/Lima"),  # Peru (default, from BIO)
    "America/New_York": ZoneInfo("America/New_York"),  # US Eastern
    "America/Chicago": ZoneInfo("America/Chicago"),  # US Central
    "America/Los_Angeles": ZoneInfo("America/Los_Angeles"),  # US Pacific
    "Europe/London": ZoneInfo("Europe/London"),  # UK
}

# Default timezone by calendar context
CONTEXT_DEFAULT_TIMEZONES: Dict[str, str] = {
    "GREGORIAN": "UTC",
    "PERU_BANKING": "America/Lima",
    # Future calendar systems:
    # "US_FED_RESERVE": "America/New_York",
    # "NYSE": "America/New_York",
}

# Weekday constants (Monday = 0, Sunday = 6)
MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

# Standard weekend days
WEEKEND_DAYS = {SATURDAY, SUNDAY}

# Months in a quarter
QUARTER_MONTHS = {
    1: [1, 2, 3],  # Q1
    2: [4, 5, 6],  # Q2
    3: [7, 8, 9],  # Q3
    4: [10, 11, 12],  # Q4
}

# First month of each quarter
QUARTER_START_MONTHS = {
    1: 1,  # Q1 starts in January
    2: 4,  # Q2 starts in April
    3: 7,  # Q3 starts in July
    4: 10,  # Q4 starts in October
}


def get_quarter(month: int) -> int:
    """Get the quarter number (1-4) for a given month (1-12).

    Args:
        month: Month number (1-12).

    Returns:
        Quarter number (1-4).

    Raises:
        ValueError: If month is not between 1 and 12.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be between 1 and 12, got {month}")
    return (month - 1) // 3 + 1
