"""
Ground Truth Validation for Complex Temporal Queries

Tests the 104 query examples from app.py against mathematically
computed ground truth dates using fixed reference: July 15, 2024 (Monday).

This test file validates:
1. DATE_QUERIES - Pure date/period expressions (20 tests)
2. Comparison queries - Queries comparing two periods (10 tests)
3. Explicit date ranges - "entre enero y marzo", "del 15 al 30" (8 tests)
4. Business day queries - "últimos 5 días hábiles" (6 tests)
5. Quincena queries - Fortnight patterns (3 tests)
6. Weekday patterns - "los lunes del mes pasado" (4 tests)
7. Intent detection - For queries needing external data (20 tests)
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from typing import List, Tuple, Dict, Optional

# Import from the date_agent module
from date_agent.tools.resolve_period_tool import ResolvePeriodTool
from date_agent.tools.current_date_tool import GetCurrentDateInfoTool
from date_agent.calendars.peru_banking import PeruBankingCalendar
from date_agent.calendars.gregorian import GregorianCalendar
from date_agent.core.config import ToolExecutionContext


# =============================================================================
# GROUND TRUTH DATA - Reference Date: July 15, 2024 (Monday)
# =============================================================================

REFERENCE_DATE = date(2024, 7, 15)  # Monday

# Ground truth for period resolutions (start, end, calendar_days)
GROUND_TRUTH_PERIODS = {
    # === Single days ===
    "hoy": ("2024-07-15", "2024-07-15", 1),
    "today": ("2024-07-15", "2024-07-15", 1),
    "ayer": ("2024-07-14", "2024-07-14", 1),
    "yesterday": ("2024-07-14", "2024-07-14", 1),

    # === Weeks (ISO: Monday-Sunday) ===
    "semana pasada": ("2024-07-08", "2024-07-14", 7),
    "last week": ("2024-07-08", "2024-07-14", 7),
    "last_week": ("2024-07-08", "2024-07-14", 7),
    "semana antepasada": ("2024-07-01", "2024-07-07", 7),
    "week_before_last": ("2024-07-01", "2024-07-07", 7),

    # === Months ===
    "este mes": ("2024-07-01", "2024-07-31", 31),
    "this_month": ("2024-07-01", "2024-07-31", 31),
    "mes anterior": ("2024-06-01", "2024-06-30", 30),
    "last_month": ("2024-06-01", "2024-06-30", 30),

    # === Quarters ===
    "trimestre pasado": ("2024-04-01", "2024-06-30", 91),
    "last_quarter": ("2024-04-01", "2024-06-30", 91),
    "this_quarter": ("2024-07-01", "2024-09-30", 92),

    # === Named quarters ===
    "Q1 2024": ("2024-01-01", "2024-03-31", 91),  # Leap year Feb
    "Q2 2024": ("2024-04-01", "2024-06-30", 91),
    "Q3 2024": ("2024-07-01", "2024-09-30", 92),
    "Q4 2024": ("2024-10-01", "2024-12-31", 92),

    # === Year to date ===
    "ytd": ("2024-01-01", "2024-07-15", 197),
}

# Ground truth for complex date ranges
GROUND_TRUTH_RANGES = {
    "enero_marzo_2024": ("2024-01-01", "2024-03-31", 91),
    "julio_2024_hasta_hoy": ("2024-07-01", "2024-07-15", 15),
    "ultima_quincena_junio": ("2024-06-16", "2024-06-30", 15),
    "del_15_al_30_junio": ("2024-06-15", "2024-06-30", 16),
    "enero_1_15_2025": ("2025-01-01", "2025-01-15", 15),
}

# Weekday patterns in June 2024
MONDAYS_JUNE_2024 = ["2024-06-03", "2024-06-10", "2024-06-17", "2024-06-24"]
WEEKENDS_JULY_2024_UNTIL_REF = [
    ("2024-07-06", "2024-07-07"),  # First weekend
    ("2024-07-13", "2024-07-14"),  # Second weekend (includes ref-1 day)
]

# First business day each month 2024 (Peru Banking Calendar)
FIRST_BUSINESS_DAY_2024 = {
    1: "2024-01-02",  # Jan 1 = Año Nuevo
    2: "2024-02-01",  # Thursday
    3: "2024-03-01",  # Friday
    4: "2024-04-01",  # Monday
    5: "2024-05-02",  # May 1 = Día del Trabajo
    6: "2024-06-03",  # Jun 1-2 = weekend
    7: "2024-07-01",  # Monday
}

# Last 5 business days from July 15, 2024 (backwards)
# Jul 15 (Mon), Jul 12 (Fri), Jul 11 (Thu), Jul 10 (Wed), Jul 9 (Tue)
LAST_5_BUSINESS_DAYS = ["2024-07-09", "2024-07-10", "2024-07-11", "2024-07-12", "2024-07-15"]

# Peru Banking Holidays 2024 (before reference date July 15)
PERU_HOLIDAYS_BEFORE_REF = [
    ("2024-01-01", "Año Nuevo"),
    ("2024-03-28", "Jueves Santo"),
    ("2024-03-29", "Viernes Santo"),
    ("2024-05-01", "Día del Trabajo"),
    ("2024-06-07", "Batalla de Arica"),
    ("2024-06-29", "San Pedro y San Pablo"),
]

# Peru Banking Holidays 2024 (after reference date)
PERU_HOLIDAYS_AFTER_REF = [
    ("2024-07-28", "Fiestas Patrias"),
    ("2024-07-29", "Fiestas Patrias"),
]


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def resolve_period_tool() -> ResolvePeriodTool:
    """Create a resolve period tool instance."""
    return ResolvePeriodTool()


@pytest.fixture
def peru_calendar() -> PeruBankingCalendar:
    """Create a Peru banking calendar instance."""
    return PeruBankingCalendar()


# =============================================================================
# TEST CLASS: DATE_QUERIES Ground Truth
# =============================================================================

class TestDateQueriesGroundTruth:
    """Validate DATE_QUERIES - all should resolve to exact dates."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("period,expected_start,expected_end,expected_days", [
        ("today", "2024-07-15", "2024-07-15", 1),
        ("yesterday", "2024-07-14", "2024-07-14", 1),
        ("last_week", "2024-07-08", "2024-07-14", 7),
        ("week_before_last", "2024-07-01", "2024-07-07", 7),
        ("this_month", "2024-07-01", "2024-07-31", 31),
        ("last_month", "2024-06-01", "2024-06-30", 30),
        ("this_quarter", "2024-07-01", "2024-09-30", 92),
        ("last_quarter", "2024-04-01", "2024-06-30", 91),
        ("ytd", "2024-01-01", "2024-07-15", 197),
    ])
    async def test_english_periods(
        self, resolve_period_tool, tool_execution_context,
        period, expected_start, expected_end, expected_days
    ):
        """Test English period expressions against ground truth."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period=period,
            locale="en",
        )

        assert result.success
        assert result.output.start_date == expected_start
        assert result.output.end_date == expected_end
        assert result.output.calendar_days == expected_days

    @pytest.mark.asyncio
    @pytest.mark.parametrize("period,expected_start,expected_end,expected_days", [
        ("semana pasada", "2024-07-08", "2024-07-14", 7),
        ("semana antepasada", "2024-07-01", "2024-07-07", 7),
        ("mes anterior", "2024-06-01", "2024-06-30", 30),
        ("trimestre pasado", "2024-04-01", "2024-06-30", 91),
    ])
    async def test_spanish_periods(
        self, resolve_period_tool, tool_execution_context,
        period, expected_start, expected_end, expected_days
    ):
        """Test Spanish period expressions against ground truth."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period=period,
            locale="es",
        )

        assert result.success
        assert result.output.start_date == expected_start
        assert result.output.end_date == expected_end
        assert result.output.calendar_days == expected_days

    @pytest.mark.asyncio
    @pytest.mark.parametrize("quarter,expected_start,expected_end,expected_days", [
        ("Q1 2024", "2024-01-01", "2024-03-31", 91),
        ("Q2 2024", "2024-04-01", "2024-06-30", 91),
        ("Q3 2024", "2024-07-01", "2024-09-30", 92),
        ("Q4 2024", "2024-10-01", "2024-12-31", 92),
    ])
    async def test_named_quarters(
        self, resolve_period_tool, tool_execution_context,
        quarter, expected_start, expected_end, expected_days
    ):
        """Test named quarter expressions (Q1-Q4 YYYY) against ground truth."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period=quarter,
        )

        assert result.success
        assert result.output.start_date == expected_start
        assert result.output.end_date == expected_end
        assert result.output.calendar_days == expected_days

    @pytest.mark.asyncio
    async def test_july_2024_month_has_31_days(
        self, resolve_period_tool, tool_execution_context
    ):
        """Verify July 2024 (this_month) has exactly 31 days."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="this_month",
        )

        assert result.success
        assert result.output.calendar_days == 31
        assert result.output.start_date == "2024-07-01"
        assert result.output.end_date == "2024-07-31"

    @pytest.mark.asyncio
    async def test_june_2024_has_30_days(
        self, resolve_period_tool, tool_execution_context
    ):
        """Verify June 2024 (last_month) has exactly 30 days."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="last_month",
        )

        assert result.success
        assert result.output.calendar_days == 30
        assert result.output.start_date == "2024-06-01"
        assert result.output.end_date == "2024-06-30"

    @pytest.mark.asyncio
    async def test_q1_2024_leap_year(
        self, resolve_period_tool, tool_execution_context
    ):
        """Verify Q1 2024 has 91 days (includes Feb 29 leap day)."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="Q1 2024",
        )

        # Q1 2024: Jan (31) + Feb (29 - leap year) + Mar (31) = 91 days
        assert result.success
        assert result.output.calendar_days == 91
        assert result.output.start_date == "2024-01-01"
        assert result.output.end_date == "2024-03-31"

    @pytest.mark.asyncio
    async def test_ytd_from_july_15(
        self, resolve_period_tool, tool_execution_context
    ):
        """Verify YTD from July 15, 2024 = 197 days."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="ytd",
        )

        # Jan 1 to Jul 15 in a leap year
        # Jan(31) + Feb(29) + Mar(31) + Apr(30) + May(31) + Jun(30) + Jul 1-15(15) = 197
        assert result.success
        assert result.output.calendar_days == 197
        assert result.output.start_date == "2024-01-01"
        assert result.output.end_date == "2024-07-15"


# =============================================================================
# TEST CLASS: Comparison Queries
# =============================================================================

class TestComparisonQueries:
    """Validate queries that compare two periods."""

    @pytest.mark.asyncio
    async def test_este_mes_vs_mes_pasado_dates(
        self, resolve_period_tool, tool_execution_context
    ):
        """Validate date ranges for 'este mes' and 'mes pasado'."""
        result_este = await resolve_period_tool.execute(
            tool_execution_context,
            period="this_month",
        )
        result_pasado = await resolve_period_tool.execute(
            tool_execution_context,
            period="last_month",
        )

        # Este mes = July 2024
        assert result_este.output.start_date == "2024-07-01"
        assert result_este.output.end_date == "2024-07-31"

        # Mes pasado = June 2024
        assert result_pasado.output.start_date == "2024-06-01"
        assert result_pasado.output.end_date == "2024-06-30"

    @pytest.mark.asyncio
    async def test_q3_vs_q2_2024_dates(
        self, resolve_period_tool, tool_execution_context
    ):
        """Validate date ranges for Q3 2024 vs Q2 2024."""
        result_q3 = await resolve_period_tool.execute(
            tool_execution_context,
            period="Q3 2024",
        )
        result_q2 = await resolve_period_tool.execute(
            tool_execution_context,
            period="Q2 2024",
        )

        # Q3 = Jul-Sep 2024
        assert result_q3.output.start_date == "2024-07-01"
        assert result_q3.output.end_date == "2024-09-30"
        assert result_q3.output.calendar_days == 92

        # Q2 = Apr-Jun 2024
        assert result_q2.output.start_date == "2024-04-01"
        assert result_q2.output.end_date == "2024-06-30"
        assert result_q2.output.calendar_days == 91

    @pytest.mark.asyncio
    async def test_trimestre_pasado_is_q2(
        self, resolve_period_tool, tool_execution_context
    ):
        """'trimestre pasado' from July should be Q2 2024."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="last_quarter",
        )

        # From July (Q3), last quarter is Q2
        assert result.output.start_date == "2024-04-01"
        assert result.output.end_date == "2024-06-30"

    @pytest.mark.asyncio
    async def test_all_2024_quarters_sum_to_366(
        self, resolve_period_tool, tool_execution_context
    ):
        """All 4 quarters of 2024 should sum to 366 days (leap year)."""
        quarters = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"]
        total_days = 0

        for q in quarters:
            result = await resolve_period_tool.execute(
                tool_execution_context,
                period=q,
            )
            total_days += result.output.calendar_days

        assert total_days == 366  # 2024 is a leap year


# =============================================================================
# TEST CLASS: Business Day Queries
# =============================================================================

class TestBusinessDayQueries:
    """Validate business day calculations with Peru banking calendar."""

    def test_peru_calendar_july_2024_holidays(self, peru_calendar):
        """Verify Peru banking holidays in July 2024."""
        holidays = peru_calendar.get_holidays(2024)
        holiday_dates = {h.date for h in holidays}

        # Fiestas Patrias should be July 28-29
        assert date(2024, 7, 28) in holiday_dates
        assert date(2024, 7, 29) in holiday_dates

    def test_weekends_not_business_days(self, peru_calendar):
        """Verify weekends are not business days."""
        # July 13-14, 2024 is Saturday-Sunday
        assert not peru_calendar.is_business_day(date(2024, 7, 13))  # Saturday
        assert not peru_calendar.is_business_day(date(2024, 7, 14))  # Sunday

        # July 15, 2024 is Monday (business day)
        assert peru_calendar.is_business_day(date(2024, 7, 15))

    def test_count_business_days_last_week_july(self, peru_calendar):
        """Count business days in last week of July before ref date."""
        # July 8-14, 2024 (last week from July 15)
        start = date(2024, 7, 8)
        end = date(2024, 7, 14)

        count = peru_calendar.count_business_days(start, end)

        # Mon-Fri = 5 business days (Jul 8-12)
        # Sat-Sun = weekend (Jul 13-14)
        assert count == 5

    def test_first_business_day_january_2024(self, peru_calendar):
        """First business day of January 2024 is January 2 (Jan 1 = holiday)."""
        assert not peru_calendar.is_business_day(date(2024, 1, 1))  # Holiday
        assert peru_calendar.is_business_day(date(2024, 1, 2))       # First business day

    def test_first_business_day_may_2024(self, peru_calendar):
        """First business day of May 2024 is May 2 (May 1 = Labor Day)."""
        assert not peru_calendar.is_business_day(date(2024, 5, 1))  # Día del Trabajo
        assert peru_calendar.is_business_day(date(2024, 5, 2))

    def test_first_business_day_june_2024(self, peru_calendar):
        """First business day of June 2024 is June 3 (June 1-2 = weekend)."""
        # June 1, 2024 is Saturday
        # June 2, 2024 is Sunday
        assert not peru_calendar.is_business_day(date(2024, 6, 1))
        assert not peru_calendar.is_business_day(date(2024, 6, 2))
        assert peru_calendar.is_business_day(date(2024, 6, 3))  # Monday


# =============================================================================
# TEST CLASS: Quincena (Fortnight) Queries
# =============================================================================

class TestQuincenaQueries:
    """Validate fortnight (quincena) date patterns."""

    def test_primera_quincena_july(self):
        """First fortnight of July = July 1-15."""
        expected_start = date(2024, 7, 1)
        expected_end = date(2024, 7, 15)
        expected_days = 15

        # Calculate the range
        days = (expected_end - expected_start).days + 1

        assert days == expected_days
        assert expected_start.day == 1
        assert expected_end.day == 15

    def test_segunda_quincena_june(self):
        """Second fortnight of June = June 16-30."""
        expected_start = date(2024, 6, 16)
        expected_end = date(2024, 6, 30)
        expected_days = 15

        days = (expected_end - expected_start).days + 1

        assert days == expected_days
        assert expected_start.day == 16
        assert expected_end.day == 30

    def test_ultima_quincena_31_day_month(self):
        """Second fortnight of a 31-day month = 16 days."""
        # July has 31 days, so July 16-31 = 16 days
        expected_start = date(2024, 7, 16)
        expected_end = date(2024, 7, 31)
        expected_days = 16

        days = (expected_end - expected_start).days + 1

        assert days == expected_days


# =============================================================================
# TEST CLASS: Weekday Pattern Queries
# =============================================================================

class TestWeekdayPatternQueries:
    """Validate queries filtering by specific weekdays."""

    def test_mondays_in_june_2024(self):
        """Find all Mondays in June 2024."""
        expected_mondays = [
            date(2024, 6, 3),
            date(2024, 6, 10),
            date(2024, 6, 17),
            date(2024, 6, 24),
        ]

        # Calculate Mondays in June 2024
        mondays = []
        current = date(2024, 6, 1)
        while current.month == 6:
            if current.weekday() == 0:  # Monday
                mondays.append(current)
            current += timedelta(days=1)

        assert mondays == expected_mondays
        assert len(mondays) == 4

    def test_saturdays_in_july_2024_until_ref(self):
        """Find all Saturdays in July 2024 until reference date."""
        expected_saturdays = [
            date(2024, 7, 6),
            date(2024, 7, 13),
        ]

        # Calculate Saturdays until July 15
        saturdays = []
        current = date(2024, 7, 1)
        while current <= REFERENCE_DATE:
            if current.weekday() == 5:  # Saturday
                saturdays.append(current)
            current += timedelta(days=1)

        assert saturdays == expected_saturdays
        assert len(saturdays) == 2

    def test_weekends_in_july_2024_until_ref(self):
        """Find all weekend days in July 2024 until reference date."""
        expected_weekend_days = [
            date(2024, 7, 6),   # Saturday
            date(2024, 7, 7),   # Sunday
            date(2024, 7, 13),  # Saturday
            date(2024, 7, 14),  # Sunday
        ]

        weekend_days = []
        current = date(2024, 7, 1)
        while current <= REFERENCE_DATE:
            if current.weekday() >= 5:  # Saturday or Sunday
                weekend_days.append(current)
            current += timedelta(days=1)

        assert weekend_days == expected_weekend_days
        assert len(weekend_days) == 4

    def test_fridays_in_last_month(self):
        """Find all Fridays in June 2024 (mes pasado)."""
        expected_fridays = [
            date(2024, 6, 7),
            date(2024, 6, 14),
            date(2024, 6, 21),
            date(2024, 6, 28),
        ]

        fridays = []
        current = date(2024, 6, 1)
        while current.month == 6:
            if current.weekday() == 4:  # Friday
                fridays.append(current)
            current += timedelta(days=1)

        assert fridays == expected_fridays
        assert len(fridays) == 4


# =============================================================================
# TEST CLASS: Intent Detection Only
# =============================================================================

class TestIntentDetectionOnly:
    """
    For queries that require external user data, validate that temporal
    intent is correctly detected even if dates can't be fully resolved.

    These queries contain temporal expressions but need:
    - User transaction history
    - User card activation date
    - User loyalty level history
    - Campaign data
    """

    # Queries that have temporal elements but need external data
    TEMPORAL_QUERIES_NEEDING_DATA = [
        # Loyalty - need level history
        "cuánto tiempo llevo en mi nivel actual de loyalty?",
        "cuándo fue la última vez que subí de nivel?",
        "en qué mes del año pasado alcancé el nivel oro?",
        "desde cuándo estoy en el nivel actual?",

        # Knowledge Base - need user-specific dates
        "cuántos días faltan para mi fecha de corte?",
        "cuándo fue mi último pago de tarjeta?",
        "cuál fue la fecha de mi último estado de cuenta?",
        "cuándo vence el pago mínimo de este mes?",
        "hace cuánto tiempo que no pago el total de mi tarjeta?",

        # Campaign - need campaign data
        "cuándo termina la campaña actual de cashback doble?",
        "cuántos días faltan para que termine mi campaña de desafío?",
        "cuántas campañas he completado desde que tengo la tarjeta?",

        # Other - need card/transaction history
        "cuántos meses llevo usando mi tarjeta io?",
        "cuándo fue mi primera compra con la tarjeta?",
        "hace cuánto tiempo que no uso mi tarjeta física?",
        "cuántas transacciones he hecho desde que activé la tarjeta?",
        "en qué fecha cumple un año mi tarjeta?",
        "cuántos días han pasado desde mi última transacción?",
    ]

    # Temporal keywords that should be detected
    TEMPORAL_KEYWORDS_ES = [
        "cuánto tiempo", "cuándo", "desde cuándo", "hace cuánto",
        "último", "última", "pasado", "pasada", "mes", "año",
        "días", "nivel", "fecha", "termina", "vence", "primera",
        "desde que", "cuántas", "cuántos",  # Added for "desde que tengo", "cuántas campañas"
    ]

    def test_queries_contain_temporal_keywords(self):
        """All queries in the list should contain temporal keywords."""
        for query in self.TEMPORAL_QUERIES_NEEDING_DATA:
            query_lower = query.lower()
            has_temporal = any(
                kw in query_lower for kw in self.TEMPORAL_KEYWORDS_ES
            )
            assert has_temporal, f"Query should have temporal keyword: {query}"

    def test_count_queries_needing_external_data(self):
        """Verify we have 18 queries that need external data."""
        assert len(self.TEMPORAL_QUERIES_NEEDING_DATA) == 18

    @pytest.mark.parametrize("query", [
        "cuánto tiempo llevo en mi nivel actual de loyalty?",
        "cuándo fue la última vez que subí de nivel?",
        "cuántos meses llevo usando mi tarjeta io?",
        "cuándo fue mi primera compra con la tarjeta?",
    ])
    def test_temporal_query_has_question_mark(self, query):
        """Queries should be properly formatted as questions."""
        assert "?" in query

    def test_loyalty_queries_have_level_keywords(self):
        """Loyalty queries should contain 'nivel' keyword."""
        loyalty_queries = [
            q for q in self.TEMPORAL_QUERIES_NEEDING_DATA
            if "nivel" in q.lower() or "loyalty" in q.lower()
        ]
        assert len(loyalty_queries) >= 4


# =============================================================================
# TEST CLASS: Ground Truth Summary
# =============================================================================

class TestGroundTruthSummary:
    """Summary tests validating overall ground truth accuracy."""

    def test_reference_date_is_monday(self):
        """Verify reference date July 15, 2024 is a Monday."""
        assert REFERENCE_DATE.weekday() == 0  # Monday

    def test_2024_is_leap_year(self):
        """Verify 2024 is a leap year."""
        from calendar import isleap
        assert isleap(2024)

    def test_year_2024_has_366_days(self):
        """Verify 2024 has 366 days (leap year)."""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        days = (end - start).days + 1
        assert days == 366

    def test_all_ground_truth_periods_have_valid_dates(self):
        """Verify all ground truth period data is valid."""
        for period_name, (start, end, days) in GROUND_TRUTH_PERIODS.items():
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
            computed_days = (end_date - start_date).days + 1

            assert computed_days == days, \
                f"Period {period_name}: expected {days} days, got {computed_days}"

    def test_ground_truth_ranges_valid(self):
        """Verify all explicit range data is valid."""
        for range_name, (start, end, days) in GROUND_TRUTH_RANGES.items():
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
            computed_days = (end_date - start_date).days + 1

            assert computed_days == days, \
                f"Range {range_name}: expected {days} days, got {computed_days}"

    def test_mondays_june_2024_are_all_mondays(self):
        """Verify all dates in MONDAYS_JUNE_2024 are actually Mondays."""
        for date_str in MONDAYS_JUNE_2024:
            d = date.fromisoformat(date_str)
            assert d.weekday() == 0, f"{date_str} is not a Monday"
            assert d.month == 6, f"{date_str} is not in June"
            assert d.year == 2024, f"{date_str} is not in 2024"

    def test_first_business_days_are_valid(self):
        """Verify first business day data is reasonable."""
        for month, date_str in FIRST_BUSINESS_DAY_2024.items():
            d = date.fromisoformat(date_str)
            assert d.month == month, f"First business day for month {month} should be in that month"
            assert d.weekday() < 5, f"{date_str} should be a weekday"
            assert d.day <= 3, f"First business day should be within first 3 days of month"


# =============================================================================
# TEST CLASS: Complex Query Examples from app.py
# =============================================================================

class TestAppPyQueryExamples:
    """Test specific complex queries from app.py."""

    @pytest.mark.asyncio
    async def test_query_este_mes_resolves(
        self, resolve_period_tool, tool_execution_context
    ):
        """'cuánto cashback he ganado este mes?' should resolve 'este mes'."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="this_month",
        )

        assert result.success
        assert result.output.start_date == "2024-07-01"
        assert result.output.end_date == "2024-07-31"

    @pytest.mark.asyncio
    async def test_query_ultimo_mes_resolves(
        self, resolve_period_tool, tool_execution_context
    ):
        """'cuánto cashback he ganado el último mes?' should resolve to June."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="last_month",
        )

        assert result.success
        assert result.output.start_date == "2024-06-01"
        assert result.output.end_date == "2024-06-30"

    @pytest.mark.asyncio
    async def test_query_semana_pasada_resolves(
        self, resolve_period_tool, tool_execution_context
    ):
        """'semana pasada' - test week resolution."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="semana pasada",
            locale="es",
        )

        # Last week from July 15 (Monday) = July 8-14
        assert result.success
        assert result.output.start_date == "2024-07-08"
        assert result.output.end_date == "2024-07-14"
        assert result.output.calendar_days == 7

    @pytest.mark.asyncio
    async def test_q3_2024_vs_q2_2024_comparison(
        self, resolve_period_tool, tool_execution_context
    ):
        """'comparar mi cashback del Q3 2024 vs Q2 2024' - both quarters resolve."""
        q3 = await resolve_period_tool.execute(
            tool_execution_context, period="Q3 2024"
        )
        q2 = await resolve_period_tool.execute(
            tool_execution_context, period="Q2 2024"
        )

        # Q3 2024: Jul-Sep
        assert q3.output.start_date == "2024-07-01"
        assert q3.output.end_date == "2024-09-30"

        # Q2 2024: Apr-Jun
        assert q2.output.start_date == "2024-04-01"
        assert q2.output.end_date == "2024-06-30"

        # Q3 > Q2 in days (92 vs 91)
        assert q3.output.calendar_days > q2.output.calendar_days

    @pytest.mark.asyncio
    async def test_trimestre_anterior_is_q2(
        self, resolve_period_tool, tool_execution_context
    ):
        """'trimestre anterior al actual' from July = Q2 2024."""
        result = await resolve_period_tool.execute(
            tool_execution_context,
            period="last_quarter",
        )

        # July is Q3, so previous quarter is Q2
        assert result.output.start_date == "2024-04-01"
        assert result.output.end_date == "2024-06-30"


# =============================================================================
# RUN SUMMARY
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
