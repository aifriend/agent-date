"""Gregorian calendar - standard calendar with weekends only."""

from datetime import date
from typing import List

from date_agent.calendars.base_calendar import BaseCalendar, Holiday


class GregorianCalendar(BaseCalendar):
    """Standard Gregorian calendar.

    This calendar considers only weekends (Saturday, Sunday) as non-business days.
    No holidays are defined - use this for simple date calculations
    that don't need holiday awareness.
    """

    @property
    def name(self) -> str:
        return "GREGORIAN"

    @property
    def description(self) -> str:
        return "Standard Gregorian calendar (weekends only, no holidays)"

    @property
    def timezone(self) -> str:
        return "UTC"

    def get_holidays(self, year: int) -> List[Holiday]:
        """Gregorian calendar has no holidays defined.

        Args:
            year: The year (ignored).

        Returns:
            Empty list (no holidays).
        """
        return []
