"""Calendar system implementations."""

from date_agent.calendars.base_calendar import BaseCalendar, Holiday
from date_agent.calendars.gregorian import GregorianCalendar
from date_agent.calendars.peru_banking import PeruBankingCalendar

__all__ = [
    "BaseCalendar",
    "Holiday",
    "GregorianCalendar",
    "PeruBankingCalendar",
]


def get_calendar(calendar_system: str) -> BaseCalendar:
    """Get a calendar instance by system name.

    Args:
        calendar_system: Calendar system identifier (e.g., "GREGORIAN", "PERU_BANKING").

    Returns:
        Calendar instance.

    Raises:
        ValueError: If calendar system is not supported.
    """
    calendars = {
        "GREGORIAN": GregorianCalendar,
        "PERU_BANKING": PeruBankingCalendar,
    }

    calendar_class = calendars.get(calendar_system.upper())
    if calendar_class is None:
        raise ValueError(
            f"Unsupported calendar system: '{calendar_system}'. "
            f"Supported: {list(calendars.keys())}"
        )

    return calendar_class()
