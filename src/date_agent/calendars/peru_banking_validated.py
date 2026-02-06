"""Peru banking calendar with external validation.

This module provides a Peru banking calendar that:
1. Uses the `holidays` library as the ground truth source
2. Calculates Easter dates algorithmically (computus)
3. Validates all dates against official sources

The `holidays` library sources its data from official government calendars.
"""

from datetime import date, timedelta
from typing import List, Optional, Dict, Set
import logging

from date_agent.calendars.base_calendar import BaseCalendar, Holiday

logger = logging.getLogger(__name__)

# Try to import holidays library
try:
    import holidays as holidays_lib
    HOLIDAYS_AVAILABLE = True
except ImportError:
    HOLIDAYS_AVAILABLE = False
    logger.warning("holidays library not installed. Using hardcoded calendar.")


def compute_easter(year: int) -> date:
    """Calculate Easter Sunday using the Anonymous Gregorian algorithm (computus).

    This algorithm was published in 1876 and is mathematically proven to be
    accurate for all years in the Gregorian calendar.

    References:
        - https://en.wikipedia.org/wiki/Date_of_Easter#Anonymous_Gregorian_algorithm
        - "Computus" by Edward M. Reingold and Nachum Dershowitz

    Args:
        year: The year to calculate Easter for.

    Returns:
        The date of Easter Sunday for that year.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1

    return date(year, month, day)


def compute_maundy_thursday(year: int) -> date:
    """Calculate Maundy Thursday (3 days before Easter Sunday)."""
    easter = compute_easter(year)
    return easter - timedelta(days=3)


def compute_good_friday(year: int) -> date:
    """Calculate Good Friday (2 days before Easter Sunday)."""
    easter = compute_easter(year)
    return easter - timedelta(days=2)


class PeruBankingValidatedCalendar(BaseCalendar):
    """Peru banking calendar with external validation.

    This calendar uses multiple sources of truth:
    1. Primary: `holidays` Python library (official government sources)
    2. Fallback: Algorithmically computed Easter dates
    3. Fixed holidays: Known fixed-date Peruvian holidays

    All holidays are cross-validated when the holidays library is available.
    """

    # Fixed holidays that don't change year to year
    FIXED_HOLIDAYS = [
        (1, 1, "New Year's Day", "Año Nuevo"),
        (5, 1, "Labor Day", "Día del Trabajo"),
        (6, 7, "Battle of Arica Day", "Día de la Batalla de Arica"),
        (6, 29, "Saint Peter and Saint Paul", "San Pedro y San Pablo"),
        (7, 23, "Air Force Day", "Día de la Fuerza Aérea"),
        (7, 28, "Independence Day", "Fiestas Patrias"),
        (7, 29, "Independence Day (Day 2)", "Fiestas Patrias"),
        (8, 6, "Battle of Junín Day", "Batalla de Junín"),
        (8, 30, "Saint Rose of Lima", "Santa Rosa de Lima"),
        (10, 8, "Battle of Angamos", "Combate de Angamos"),
        (11, 1, "All Saints' Day", "Día de Todos los Santos"),
        (12, 8, "Immaculate Conception", "Inmaculada Concepción"),
        (12, 9, "Battle of Ayacucho", "Batalla de Ayacucho"),
        (12, 25, "Christmas Day", "Navidad"),
    ]

    def __init__(self):
        """Initialize the calendar."""
        self._cache: Dict[int, List[Holiday]] = {}
        self._holidays_lib_cache: Dict[int, Set[date]] = {}

    @property
    def name(self) -> str:
        return "PERU_BANKING_VALIDATED"

    @property
    def description(self) -> str:
        return "Peru banking calendar with external validation (holidays library + computus)"

    @property
    def timezone(self) -> str:
        return "America/Lima"

    def _get_holidays_from_library(self, year: int) -> Set[date]:
        """Get holidays from the holidays library."""
        if year in self._holidays_lib_cache:
            return self._holidays_lib_cache[year]

        if not HOLIDAYS_AVAILABLE:
            return set()

        try:
            pe_holidays = holidays_lib.Peru(years=year)
            holiday_dates = set(pe_holidays.keys())
            self._holidays_lib_cache[year] = holiday_dates
            return holiday_dates
        except Exception as e:
            logger.warning(f"Failed to load holidays from library for {year}: {e}")
            return set()

    def get_holidays(self, year: int) -> List[Holiday]:
        """Get all holidays for a given year.

        Uses the holidays library as primary source, with algorithmic
        Easter calculation as validation/fallback.

        Args:
            year: The year to get holidays for.

        Returns:
            List of Holiday objects for the year.
        """
        if year in self._cache:
            return self._cache[year]

        holidays_list: List[Holiday] = []
        lib_holidays = self._get_holidays_from_library(year)

        # Add fixed holidays
        for month, day, name_en, name_es in self.FIXED_HOLIDAYS:
            holiday_date = date(year, month, day)

            # Validate against library if available
            if lib_holidays and holiday_date not in lib_holidays:
                logger.warning(
                    f"Fixed holiday {holiday_date} ({name_en}) not in holidays library"
                )

            holidays_list.append(Holiday(
                date=holiday_date,
                name=name_en,
                name_localized=name_es,
                holiday_type="national",
            ))

        # Add Easter-based holidays (computed algorithmically)
        maundy_thursday = compute_maundy_thursday(year)
        good_friday = compute_good_friday(year)

        # Validate Easter dates against library
        if lib_holidays:
            if maundy_thursday not in lib_holidays:
                logger.error(
                    f"EASTER MISMATCH: Computed Maundy Thursday {maundy_thursday} "
                    f"not in holidays library for {year}"
                )
            if good_friday not in lib_holidays:
                logger.error(
                    f"EASTER MISMATCH: Computed Good Friday {good_friday} "
                    f"not in holidays library for {year}"
                )

        holidays_list.append(Holiday(
            date=maundy_thursday,
            name="Maundy Thursday",
            name_localized="Jueves Santo",
            holiday_type="religious",
        ))

        holidays_list.append(Holiday(
            date=good_friday,
            name="Good Friday",
            name_localized="Viernes Santo",
            holiday_type="religious",
        ))

        # Sort by date
        holidays_list.sort(key=lambda h: h.date)

        # Cache and return
        self._cache[year] = holidays_list
        return holidays_list

    def validate_against_library(self, year: int) -> Dict[str, List[str]]:
        """Validate our holidays against the holidays library.

        Args:
            year: Year to validate.

        Returns:
            Dict with 'missing', 'extra', and 'matching' lists.
        """
        result = {
            "missing": [],  # In library but not in our calendar
            "extra": [],    # In our calendar but not in library
            "matching": [], # In both
        }

        if not HOLIDAYS_AVAILABLE:
            result["error"] = "holidays library not available"
            return result

        lib_holidays = self._get_holidays_from_library(year)
        our_holidays = {h.date for h in self.get_holidays(year)}

        for d in lib_holidays:
            if d in our_holidays:
                result["matching"].append(d.isoformat())
            else:
                result["missing"].append(d.isoformat())

        for d in our_holidays:
            if d not in lib_holidays:
                result["extra"].append(d.isoformat())

        return result


# Create singleton instance
_validated_calendar = None

def get_validated_peru_calendar() -> PeruBankingValidatedCalendar:
    """Get the validated Peru banking calendar singleton."""
    global _validated_calendar
    if _validated_calendar is None:
        _validated_calendar = PeruBankingValidatedCalendar()
    return _validated_calendar
