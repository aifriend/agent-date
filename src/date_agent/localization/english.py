"""English localization for date expressions."""

from typing import Dict, Tuple
import re

# English month names (1-indexed in tuple)
MONTH_NAMES_EN = (
    "",  # Index 0 unused
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# English weekday names (0=Monday, 6=Sunday)
WEEKDAY_NAMES_EN = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

# English period expression patterns
ENGLISH_PERIOD_PATTERNS: Dict[str, str] = {
    # Today/Yesterday
    r"^today$": "today",
    r"^yesterday$": "yesterday",
    # Weeks
    r"^(this\s+)?week$": "this_week",
    r"^current\s+week$": "this_week",
    r"^last\s+week$": "last_week",
    r"^previous\s+week$": "last_week",
    r"^(the\s+)?week\s+before\s+last$": "week_before_last",
    # Months
    r"^(this\s+)?month$": "this_month",
    r"^current\s+month$": "this_month",
    r"^last\s+month$": "last_month",
    r"^previous\s+month$": "last_month",
    # Quarters
    r"^(this\s+)?quarter$": "this_quarter",
    r"^current\s+quarter$": "this_quarter",
    r"^last\s+quarter$": "last_quarter",
    r"^previous\s+quarter$": "last_quarter",
    # Years
    r"^(this\s+)?year$": "this_year",
    r"^current\s+year$": "this_year",
    r"^last\s+year$": "last_year",
    r"^previous\s+year$": "last_year",
    # Year to date
    r"^ytd$": "ytd",
    r"^year\s+to\s+date$": "ytd",
    # Named quarters (Q1-Q4 with year)
    r"^q([1-4])\s*(\d{4})$": "named_quarter",
    r"^(first|1st)\s+quarter\s*(\d{4})?$": "q1",
    r"^(second|2nd)\s+quarter\s*(\d{4})?$": "q2",
    r"^(third|3rd)\s+quarter\s*(\d{4})?$": "q3",
    r"^(fourth|4th)\s+quarter\s*(\d{4})?$": "q4",
    # Days ago pattern
    r"^(\d+)\s+days?\s+ago$": "days_ago",
}

# Period descriptions in English
ENGLISH_PERIOD_DESCRIPTIONS: Dict[str, str] = {
    "today": "today",
    "yesterday": "yesterday",
    "this_week": "this week",
    "last_week": "last week",
    "week_before_last": "the week before last",
    "this_month": "this month",
    "last_month": "last month",
    "this_quarter": "this quarter",
    "last_quarter": "last quarter",
    "this_year": "this year",
    "last_year": "last year",
    "ytd": "year to date",
}


def get_month_name_en(month: int) -> str:
    """Get English month name.

    Args:
        month: Month number (1-12).

    Returns:
        English month name.

    Raises:
        ValueError: If month is not between 1 and 12.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be between 1 and 12, got {month}")
    return MONTH_NAMES_EN[month]


def get_weekday_name_en(weekday: int) -> str:
    """Get English weekday name.

    Args:
        weekday: Weekday number (0=Monday, 6=Sunday).

    Returns:
        English weekday name.

    Raises:
        ValueError: If weekday is not between 0 and 6.
    """
    if not 0 <= weekday <= 6:
        raise ValueError(f"Weekday must be between 0 and 6, got {weekday}")
    return WEEKDAY_NAMES_EN[weekday]


def parse_english_period(text: str) -> Tuple[str, Dict[str, int]]:
    """Parse an English period expression.

    Args:
        text: English text to parse (e.g., "last week", "5 days ago").

    Returns:
        Tuple of (period_type, extracted_values) where:
        - period_type: Canonical period type (e.g., "last_week", "days_ago")
        - extracted_values: Dict with any extracted numbers

    Raises:
        ValueError: If the text doesn't match any known pattern.
    """
    normalized = text.lower().strip()
    extracted: Dict[str, int] = {}

    for pattern, period_type in ENGLISH_PERIOD_PATTERNS.items():
        match = re.match(pattern, normalized, re.IGNORECASE)
        if match:
            if period_type == "days_ago":
                days = int(match.group(1))
                extracted["days"] = days
            elif period_type == "named_quarter":
                quarter = int(match.group(1))
                year = int(match.group(2)) if match.lastindex >= 2 else None
                extracted["quarter"] = quarter
                if year:
                    extracted["year"] = year

            return period_type, extracted

    raise ValueError(f"Cannot parse English period expression: '{text}'")


def format_date_range_en(start_date: str, end_date: str) -> str:
    """Format a date range description in English.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        English formatted date range (e.g., "July 1 - July 31, 2024").
    """
    from datetime import datetime

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    start_day = start.day
    start_month = MONTH_NAMES_EN[start.month]
    end_day = end.day
    end_month = MONTH_NAMES_EN[end.month]
    end_year = end.year

    if start.month == end.month and start.year == end.year:
        return f"{start_month} {start_day} - {end_day}, {end_year}"
    elif start.year == end.year:
        return f"{start_month} {start_day} - {end_month} {end_day}, {end_year}"
    else:
        start_year = start.year
        return f"{start_month} {start_day}, {start_year} - {end_month} {end_day}, {end_year}"


def get_period_description_en(period_type: str, year: int = None, quarter: int = None) -> str:
    """Get an English description for a period type.

    Args:
        period_type: Canonical period type.
        year: Optional year for named periods.
        quarter: Optional quarter number.

    Returns:
        English description of the period.
    """
    if period_type in ENGLISH_PERIOD_DESCRIPTIONS:
        return ENGLISH_PERIOD_DESCRIPTIONS[period_type]

    if period_type.startswith("q") and len(period_type) == 2:
        q_num = int(period_type[1])
        ordinals = ["first", "second", "third", "fourth"]
        if year:
            return f"{ordinals[q_num - 1]} quarter {year}"
        return f"{ordinals[q_num - 1]} quarter"

    if period_type == "named_quarter" and quarter:
        ordinals = ["first", "second", "third", "fourth"]
        if year:
            return f"{ordinals[quarter - 1]} quarter {year}"
        return f"{ordinals[quarter - 1]} quarter"

    return period_type
