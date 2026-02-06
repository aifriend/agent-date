"""Spanish localization for date expressions.

Ported from BIO project's date handling.
"""

from typing import Dict, Tuple
import re

# Spanish month names (1-indexed in tuple, access as MONTH_NAMES_ES[month])
MONTH_NAMES_ES = (
    "",  # Index 0 unused
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

# Spanish weekday names (0=Monday, 6=Sunday)
WEEKDAY_NAMES_ES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)

# Spanish period expression patterns
# Maps regex pattern to canonical period type
SPANISH_PERIOD_PATTERNS: Dict[str, str] = {
    # Today/Yesterday
    r"^hoy$": "today",
    r"^ayer$": "yesterday",
    # Weeks
    r"^(esta\s+)?semana(\s+actual)?$": "this_week",
    r"^semana\s+pasada$": "last_week",
    r"^la\s+semana\s+pasada$": "last_week",
    r"^ultima\s+semana$": "last_week",
    r"^última\s+semana$": "last_week",
    r"^semana\s+antepasada$": "week_before_last",  # Unique Spanish expression
    r"^la\s+semana\s+antepasada$": "week_before_last",
    # Months
    r"^(este\s+)?mes(\s+actual)?$": "this_month",
    r"^mes\s+pasado$": "last_month",
    r"^el\s+mes\s+pasado$": "last_month",
    r"^mes\s+anterior$": "last_month",
    r"^ultimo\s+mes$": "last_month",
    r"^último\s+mes$": "last_month",
    # Quarters
    r"^(este\s+)?trimestre(\s+actual)?$": "this_quarter",
    r"^trimestre\s+pasado$": "last_quarter",
    r"^el\s+trimestre\s+pasado$": "last_quarter",
    r"^trimestre\s+anterior$": "last_quarter",
    r"^ultimo\s+trimestre$": "last_quarter",
    r"^último\s+trimestre$": "last_quarter",
    # Years
    r"^(este\s+)?año(\s+actual)?$": "this_year",
    r"^año\s+pasado$": "last_year",
    r"^el\s+año\s+pasado$": "last_year",
    r"^ultimo\s+año$": "last_year",
    r"^último\s+año$": "last_year",
    # Year to date
    r"^ytd$": "ytd",
    r"^año\s+hasta\s+la\s+fecha$": "ytd",
    r"^acumulado\s+del\s+año$": "ytd",
    # Named quarters (Q1-Q4 with year)
    r"^q([1-4])\s*(\d{4})$": "named_quarter",
    r"^t([1-4])\s*(\d{4})$": "named_quarter",  # "T1 2024" format
    r"^primer\s+trimestre\s*(\d{4})?$": "q1",
    r"^segundo\s+trimestre\s*(\d{4})?$": "q2",
    r"^tercer\s+trimestre\s*(\d{4})?$": "q3",
    r"^cuarto\s+trimestre\s*(\d{4})?$": "q4",
    # Days ago pattern - "hace N días"
    r"^hace\s+(\d+)\s+d[ií]as?$": "days_ago",
}

# Period descriptions in Spanish
SPANISH_PERIOD_DESCRIPTIONS: Dict[str, str] = {
    "today": "hoy",
    "yesterday": "ayer",
    "this_week": "esta semana",
    "last_week": "la semana pasada",
    "week_before_last": "la semana antepasada",
    "this_month": "este mes",
    "last_month": "el mes pasado",
    "this_quarter": "este trimestre",
    "last_quarter": "el trimestre pasado",
    "this_year": "este año",
    "last_year": "el año pasado",
    "ytd": "acumulado del año",
}


def get_month_name_es(month: int) -> str:
    """Get Spanish month name.

    Args:
        month: Month number (1-12).

    Returns:
        Spanish month name.

    Raises:
        ValueError: If month is not between 1 and 12.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be between 1 and 12, got {month}")
    return MONTH_NAMES_ES[month]


def get_weekday_name_es(weekday: int) -> str:
    """Get Spanish weekday name.

    Args:
        weekday: Weekday number (0=Monday, 6=Sunday).

    Returns:
        Spanish weekday name.

    Raises:
        ValueError: If weekday is not between 0 and 6.
    """
    if not 0 <= weekday <= 6:
        raise ValueError(f"Weekday must be between 0 and 6, got {weekday}")
    return WEEKDAY_NAMES_ES[weekday]


def parse_spanish_period(text: str) -> Tuple[str, Dict[str, int]]:
    """Parse a Spanish period expression.

    Args:
        text: Spanish text to parse (e.g., "semana pasada", "hace 5 días").

    Returns:
        Tuple of (period_type, extracted_values) where:
        - period_type: Canonical period type (e.g., "last_week", "days_ago")
        - extracted_values: Dict with any extracted numbers (e.g., {"days": 5})

    Raises:
        ValueError: If the text doesn't match any known pattern.
    """
    normalized = text.lower().strip()
    extracted: Dict[str, int] = {}

    for pattern, period_type in SPANISH_PERIOD_PATTERNS.items():
        match = re.match(pattern, normalized, re.IGNORECASE)
        if match:
            # Handle patterns with captured groups
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

    raise ValueError(f"Cannot parse Spanish period expression: '{text}'")


def format_date_range_es(start_date: str, end_date: str) -> str:
    """Format a date range description in Spanish.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        Spanish formatted date range (e.g., "1 de julio - 31 de julio 2024").
    """
    from datetime import datetime

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    start_day = start.day
    start_month = MONTH_NAMES_ES[start.month]
    end_day = end.day
    end_month = MONTH_NAMES_ES[end.month]
    end_year = end.year

    if start.month == end.month and start.year == end.year:
        return f"{start_day} - {end_day} de {end_month} {end_year}"
    elif start.year == end.year:
        return f"{start_day} de {start_month} - {end_day} de {end_month} {end_year}"
    else:
        start_year = start.year
        return f"{start_day} de {start_month} {start_year} - {end_day} de {end_month} {end_year}"


def get_period_description_es(period_type: str, year: int = None, quarter: int = None) -> str:
    """Get a Spanish description for a period type.

    Args:
        period_type: Canonical period type.
        year: Optional year for named periods.
        quarter: Optional quarter number.

    Returns:
        Spanish description of the period.
    """
    if period_type in SPANISH_PERIOD_DESCRIPTIONS:
        return SPANISH_PERIOD_DESCRIPTIONS[period_type]

    if period_type.startswith("q") and len(period_type) == 2:
        q_num = int(period_type[1])
        quarter_names = ["primer", "segundo", "tercer", "cuarto"]
        if year:
            return f"{quarter_names[q_num - 1]} trimestre {year}"
        return f"{quarter_names[q_num - 1]} trimestre"

    if period_type == "named_quarter" and quarter:
        quarter_names = ["primer", "segundo", "tercer", "cuarto"]
        if year:
            return f"{quarter_names[quarter - 1]} trimestre {year}"
        return f"{quarter_names[quarter - 1]} trimestre"

    return period_type
