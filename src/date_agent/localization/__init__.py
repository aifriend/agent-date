"""Localization support for date expressions and names."""

from date_agent.localization.spanish import (
    MONTH_NAMES_ES,
    WEEKDAY_NAMES_ES,
    get_month_name_es,
    get_weekday_name_es,
    SPANISH_PERIOD_PATTERNS,
)
from date_agent.localization.english import (
    MONTH_NAMES_EN,
    WEEKDAY_NAMES_EN,
    get_month_name_en,
    get_weekday_name_en,
    ENGLISH_PERIOD_PATTERNS,
)

__all__ = [
    # Spanish
    "MONTH_NAMES_ES",
    "WEEKDAY_NAMES_ES",
    "get_month_name_es",
    "get_weekday_name_es",
    "SPANISH_PERIOD_PATTERNS",
    # English
    "MONTH_NAMES_EN",
    "WEEKDAY_NAMES_EN",
    "get_month_name_en",
    "get_weekday_name_en",
    "ENGLISH_PERIOD_PATTERNS",
]


def get_month_name(month: int, locale: str = "es") -> str:
    """Get localized month name.

    Args:
        month: Month number (1-12).
        locale: Locale code ('es' or 'en').

    Returns:
        Localized month name.
    """
    if locale == "es":
        return get_month_name_es(month)
    return get_month_name_en(month)


def get_weekday_name(weekday: int, locale: str = "es") -> str:
    """Get localized weekday name.

    Args:
        weekday: Weekday number (0=Monday, 6=Sunday).
        locale: Locale code ('es' or 'en').

    Returns:
        Localized weekday name.
    """
    if locale == "es":
        return get_weekday_name_es(weekday)
    return get_weekday_name_en(weekday)
