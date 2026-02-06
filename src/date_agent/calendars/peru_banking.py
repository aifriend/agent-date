"""Peru banking calendar - Peruvian banking holidays.

Ported from BIO project context. Includes all official Peruvian
national holidays that affect banking operations.
"""

from datetime import date
from typing import List, Dict

from date_agent.calendars.base_calendar import BaseCalendar, Holiday


# Peru banking holidays by year
# Source: SBS (Superintendencia de Banca, Seguros y AFP del Peru)
PERU_HOLIDAYS: Dict[int, List[Dict]] = {
    2024: [
        {"date": date(2024, 1, 1), "name": "New Year's Day", "name_es": "Ano Nuevo"},
        {"date": date(2024, 3, 28), "name": "Maundy Thursday", "name_es": "Jueves Santo"},
        {"date": date(2024, 3, 29), "name": "Good Friday", "name_es": "Viernes Santo"},
        {"date": date(2024, 5, 1), "name": "Labor Day", "name_es": "Dia del Trabajo"},
        {"date": date(2024, 6, 7), "name": "Battle of Arica Day", "name_es": "Dia de la Batalla de Arica"},
        {"date": date(2024, 6, 29), "name": "Saint Peter and Saint Paul", "name_es": "San Pedro y San Pablo"},
        {"date": date(2024, 7, 23), "name": "Air Force Day", "name_es": "Dia de la Fuerza Aerea"},
        {"date": date(2024, 7, 28), "name": "Independence Day", "name_es": "Fiestas Patrias"},
        {"date": date(2024, 7, 29), "name": "Independence Day (Day 2)", "name_es": "Fiestas Patrias"},
        {"date": date(2024, 8, 6), "name": "Battle of Junin Day", "name_es": "Batalla de Junin"},
        {"date": date(2024, 8, 30), "name": "Saint Rose of Lima", "name_es": "Santa Rosa de Lima"},
        {"date": date(2024, 10, 8), "name": "Battle of Angamos", "name_es": "Combate de Angamos"},
        {"date": date(2024, 11, 1), "name": "All Saints' Day", "name_es": "Dia de Todos los Santos"},
        {"date": date(2024, 12, 8), "name": "Immaculate Conception", "name_es": "Inmaculada Concepcion"},
        {"date": date(2024, 12, 9), "name": "Battle of Ayacucho", "name_es": "Batalla de Ayacucho"},
        {"date": date(2024, 12, 25), "name": "Christmas Day", "name_es": "Navidad"},
    ],
    2025: [
        {"date": date(2025, 1, 1), "name": "New Year's Day", "name_es": "Ano Nuevo"},
        {"date": date(2025, 4, 17), "name": "Maundy Thursday", "name_es": "Jueves Santo"},
        {"date": date(2025, 4, 18), "name": "Good Friday", "name_es": "Viernes Santo"},
        {"date": date(2025, 5, 1), "name": "Labor Day", "name_es": "Dia del Trabajo"},
        {"date": date(2025, 6, 7), "name": "Battle of Arica Day", "name_es": "Dia de la Batalla de Arica"},
        {"date": date(2025, 6, 29), "name": "Saint Peter and Saint Paul", "name_es": "San Pedro y San Pablo"},
        {"date": date(2025, 7, 23), "name": "Air Force Day", "name_es": "Dia de la Fuerza Aerea"},
        {"date": date(2025, 7, 28), "name": "Independence Day", "name_es": "Fiestas Patrias"},
        {"date": date(2025, 7, 29), "name": "Independence Day (Day 2)", "name_es": "Fiestas Patrias"},
        {"date": date(2025, 8, 6), "name": "Battle of Junin Day", "name_es": "Batalla de Junin"},
        {"date": date(2025, 8, 30), "name": "Saint Rose of Lima", "name_es": "Santa Rosa de Lima"},
        {"date": date(2025, 10, 8), "name": "Battle of Angamos", "name_es": "Combate de Angamos"},
        {"date": date(2025, 11, 1), "name": "All Saints' Day", "name_es": "Dia de Todos los Santos"},
        {"date": date(2025, 12, 8), "name": "Immaculate Conception", "name_es": "Inmaculada Concepcion"},
        {"date": date(2025, 12, 9), "name": "Battle of Ayacucho", "name_es": "Batalla de Ayacucho"},
        {"date": date(2025, 12, 25), "name": "Christmas Day", "name_es": "Navidad"},
    ],
    2026: [
        {"date": date(2026, 1, 1), "name": "New Year's Day", "name_es": "Ano Nuevo"},
        {"date": date(2026, 4, 2), "name": "Maundy Thursday", "name_es": "Jueves Santo"},
        {"date": date(2026, 4, 3), "name": "Good Friday", "name_es": "Viernes Santo"},
        {"date": date(2026, 5, 1), "name": "Labor Day", "name_es": "Dia del Trabajo"},
        {"date": date(2026, 6, 7), "name": "Battle of Arica Day", "name_es": "Dia de la Batalla de Arica"},
        {"date": date(2026, 6, 29), "name": "Saint Peter and Saint Paul", "name_es": "San Pedro y San Pablo"},
        {"date": date(2026, 7, 23), "name": "Air Force Day", "name_es": "Dia de la Fuerza Aerea"},
        {"date": date(2026, 7, 28), "name": "Independence Day", "name_es": "Fiestas Patrias"},
        {"date": date(2026, 7, 29), "name": "Independence Day (Day 2)", "name_es": "Fiestas Patrias"},
        {"date": date(2026, 8, 6), "name": "Battle of Junin Day", "name_es": "Batalla de Junin"},
        {"date": date(2026, 8, 30), "name": "Saint Rose of Lima", "name_es": "Santa Rosa de Lima"},
        {"date": date(2026, 10, 8), "name": "Battle of Angamos", "name_es": "Combate de Angamos"},
        {"date": date(2026, 11, 1), "name": "All Saints' Day", "name_es": "Dia de Todos los Santos"},
        {"date": date(2026, 12, 8), "name": "Immaculate Conception", "name_es": "Inmaculada Concepcion"},
        {"date": date(2026, 12, 9), "name": "Battle of Ayacucho", "name_es": "Batalla de Ayacucho"},
        {"date": date(2026, 12, 25), "name": "Christmas Day", "name_es": "Navidad"},
    ],
}


class PeruBankingCalendar(BaseCalendar):
    """Peru banking calendar.

    Includes all official Peruvian national holidays that affect
    banking operations, as defined by SBS (Superintendencia de
    Banca, Seguros y AFP del Peru).

    Notable holidays:
    - Fiestas Patrias (July 28-29): Independence Day celebration
    - Semana Santa: Easter week (Maundy Thursday, Good Friday)
    - Various battle commemoration days

    Default timezone: America/Lima (Peru Time, UTC-5)
    """

    @property
    def name(self) -> str:
        return "PERU_BANKING"

    @property
    def description(self) -> str:
        return "Peru banking calendar (SBS official holidays)"

    @property
    def timezone(self) -> str:
        return "America/Lima"

    def get_holidays(self, year: int) -> List[Holiday]:
        """Get Peru banking holidays for a year.

        Args:
            year: The year to get holidays for.

        Returns:
            List of Holiday objects.

        Raises:
            ValueError: If holiday data is not available for the year.
        """
        if year not in PERU_HOLIDAYS:
            # For years not in our data, return a warning
            # In production, this could fetch from an API or raise an error
            raise ValueError(
                f"Peru banking holiday data not available for year {year}. "
                f"Available years: {list(PERU_HOLIDAYS.keys())}"
            )

        holidays = []
        for h in PERU_HOLIDAYS[year]:
            holidays.append(
                Holiday(
                    date=h["date"],
                    name=h["name"],
                    name_localized=h.get("name_es"),
                    holiday_type="national",
                    observed=True,
                )
            )

        return holidays


# Helper function to get holiday name in Spanish
def get_peru_holiday_name_es(d: date) -> str:
    """Get the Spanish name of a Peru holiday.

    Args:
        d: The date to check.

    Returns:
        Spanish holiday name, or empty string if not a holiday.
    """
    if d.year not in PERU_HOLIDAYS:
        return ""

    for h in PERU_HOLIDAYS[d.year]:
        if h["date"] == d:
            return h.get("name_es", h["name"])

    return ""
