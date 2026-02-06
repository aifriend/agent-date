"""resolve_period tool - converts semantic periods to date ranges."""

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Tuple, List, Optional

from date_agent.core.config import ToolExecutionContext
from date_agent.core.constants import (
    PeriodType,
    QUARTER_START_MONTHS,
    get_quarter,
)
from date_agent.core.exceptions import InvalidPeriodError
from date_agent.localization.spanish import (
    parse_spanish_period,
    format_date_range_es,
    get_period_description_es,
)
from date_agent.localization.english import (
    parse_english_period,
    format_date_range_en,
    get_period_description_en,
)
from date_agent.models.tool_schemas import ResolvePeriodInput, ResolvePeriodOutput
from date_agent.tools.base_tool import BaseDateTool


class ResolvePeriodTool(BaseDateTool[ResolvePeriodInput, ResolvePeriodOutput]):
    """Converts semantic period expressions to concrete date ranges.

    Supports:
    - Relative periods: today, yesterday, this_week, last_month, etc.
    - Named quarters: Q1 2024, Q3 2023, etc.
    - Spanish expressions: "semana pasada", "mes anterior", "semana antepasada"
    """

    @property
    def name(self) -> str:
        return "resolve_period"

    @property
    def description(self) -> str:
        return """Converts semantic period expressions like "last quarter", "Q3 2024", or "ultimo mes"
into concrete date ranges (start_date, end_date).

Supports:
- Relative periods: today, yesterday, this_week, last_month, etc.
- Named quarters: Q1 2024, Q3 2023, etc.
- Fiscal periods: fiscal_q1, fiscal_ytd (requires fiscal calendar)
- Spanish expressions: "semana pasada", "mes anterior", "trimestre anterior"

The agent should use this tool after get_current_date_info to convert
user's temporal expressions into precise date ranges."""

    @property
    def input_schema(self) -> type[ResolvePeriodInput]:
        return ResolvePeriodInput

    @property
    def output_schema(self) -> type[ResolvePeriodOutput]:
        return ResolvePeriodOutput

    async def _execute(
        self,
        context: ToolExecutionContext,
        input_data: ResolvePeriodInput,
    ) -> Tuple[ResolvePeriodOutput, List[str]]:
        """Execute the tool to resolve a period expression.

        Args:
            context: Execution context with reference_date.
            input_data: Tool input parameters.

        Returns:
            Tuple of (ResolvePeriodOutput, computation_steps).
        """
        steps: List[str] = []

        # Determine reference date
        if input_data.reference_date:
            ref_date = datetime.strptime(input_data.reference_date, "%Y-%m-%d").date()
            steps.append(f"Using provided reference date: {input_data.reference_date}")
        else:
            ref_date = context.reference_date.date()
            steps.append(f"Using context reference date: {ref_date.isoformat()}")

        # Parse the period expression
        period_type, extracted = self._parse_period(
            input_data.period, input_data.locale
        )
        steps.append(f"Parsed period type: {period_type}")

        # Resolve to date range
        start_date, end_date = self._resolve_to_dates(
            period_type, extracted, ref_date
        )
        steps.append(f"Resolved range: {start_date} to {end_date}")

        # Calculate calendar days
        calendar_days = (end_date - start_date).days + 1
        steps.append(f"Calendar days: {calendar_days}")

        # Generate descriptions
        description = self._get_description(
            period_type, start_date, end_date, "en", extracted
        )
        description_localized = self._get_description(
            period_type, start_date, end_date, input_data.locale, extracted
        )

        output = ResolvePeriodOutput(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            period_type=period_type,
            calendar_system=input_data.calendar_system,
            boundary_type=input_data.boundary_type,
            calendar_days=calendar_days,
            reference_date_used=ref_date.isoformat(),
            description=description,
            description_localized=description_localized,
        )

        return output, steps

    def _parse_period(
        self, period: str, locale: str
    ) -> Tuple[str, dict]:
        """Parse a period expression into canonical type.

        Args:
            period: Period expression (e.g., "last_week", "Q3 2024", "semana pasada").
            locale: Locale for parsing.

        Returns:
            Tuple of (period_type, extracted_values).
        """
        normalized = period.lower().strip()

        # Try canonical names first
        if normalized in [p.value for p in PeriodType]:
            return normalized, {}

        # Try named quarter pattern: Q1 2024, q3_2024, etc.
        quarter_match = re.match(r"^q([1-4])[\s_]?(\d{4})$", normalized)
        if quarter_match:
            return "named_quarter", {
                "quarter": int(quarter_match.group(1)),
                "year": int(quarter_match.group(2)),
            }

        # Try locale-specific parsing
        try:
            if locale == "es":
                return parse_spanish_period(period)
            else:
                return parse_english_period(period)
        except ValueError:
            pass

        # If nothing matches, try the other locale as fallback
        try:
            if locale != "es":
                return parse_spanish_period(period)
            else:
                return parse_english_period(period)
        except ValueError:
            pass

        raise InvalidPeriodError(
            period=period,
            suggestions=["today", "yesterday", "last_week", "last_month", "Q1 2024"],
        )

    def _resolve_to_dates(
        self, period_type: str, extracted: dict, ref_date: date
    ) -> Tuple[date, date]:
        """Resolve a period type to start and end dates.

        Args:
            period_type: Canonical period type.
            extracted: Any extracted values (e.g., quarter, year, days).
            ref_date: Reference date.

        Returns:
            Tuple of (start_date, end_date).
        """
        year = ref_date.year
        month = ref_date.month

        if period_type == "today":
            return ref_date, ref_date

        elif period_type == "yesterday":
            yesterday = ref_date - timedelta(days=1)
            return yesterday, yesterday

        elif period_type == "this_week":
            # Week starts Monday
            days_since_monday = ref_date.weekday()
            monday = ref_date - timedelta(days=days_since_monday)
            sunday = monday + timedelta(days=6)
            return monday, sunday

        elif period_type == "last_week":
            days_since_monday = ref_date.weekday()
            this_monday = ref_date - timedelta(days=days_since_monday)
            last_monday = this_monday - timedelta(days=7)
            last_sunday = last_monday + timedelta(days=6)
            return last_monday, last_sunday

        elif period_type == "week_before_last":
            days_since_monday = ref_date.weekday()
            this_monday = ref_date - timedelta(days=days_since_monday)
            two_weeks_ago_monday = this_monday - timedelta(days=14)
            two_weeks_ago_sunday = two_weeks_ago_monday + timedelta(days=6)
            return two_weeks_ago_monday, two_weeks_ago_sunday

        elif period_type == "this_month":
            first_day = ref_date.replace(day=1)
            last_day_num = calendar.monthrange(year, month)[1]
            last_day = ref_date.replace(day=last_day_num)
            return first_day, last_day

        elif period_type == "last_month":
            if month == 1:
                last_month = 12
                last_month_year = year - 1
            else:
                last_month = month - 1
                last_month_year = year

            first_day = date(last_month_year, last_month, 1)
            last_day_num = calendar.monthrange(last_month_year, last_month)[1]
            last_day = date(last_month_year, last_month, last_day_num)
            return first_day, last_day

        elif period_type == "this_quarter":
            q = get_quarter(month)
            q_start_month = QUARTER_START_MONTHS[q]
            q_end_month = q_start_month + 2
            first_day = date(year, q_start_month, 1)
            last_day_num = calendar.monthrange(year, q_end_month)[1]
            last_day = date(year, q_end_month, last_day_num)
            return first_day, last_day

        elif period_type == "last_quarter":
            q = get_quarter(month)
            if q == 1:
                prev_q = 4
                prev_year = year - 1
            else:
                prev_q = q - 1
                prev_year = year

            q_start_month = QUARTER_START_MONTHS[prev_q]
            q_end_month = q_start_month + 2
            first_day = date(prev_year, q_start_month, 1)
            last_day_num = calendar.monthrange(prev_year, q_end_month)[1]
            last_day = date(prev_year, q_end_month, last_day_num)
            return first_day, last_day

        elif period_type == "this_year":
            first_day = date(year, 1, 1)
            last_day = date(year, 12, 31)
            return first_day, last_day

        elif period_type == "last_year":
            first_day = date(year - 1, 1, 1)
            last_day = date(year - 1, 12, 31)
            return first_day, last_day

        elif period_type == "ytd":
            first_day = date(year, 1, 1)
            return first_day, ref_date

        elif period_type == "named_quarter":
            q = extracted.get("quarter", 1)
            q_year = extracted.get("year", year)
            q_start_month = QUARTER_START_MONTHS[q]
            q_end_month = q_start_month + 2
            first_day = date(q_year, q_start_month, 1)
            last_day_num = calendar.monthrange(q_year, q_end_month)[1]
            last_day = date(q_year, q_end_month, last_day_num)
            return first_day, last_day

        elif period_type.startswith("q") and len(period_type) == 2:
            # Handle q1, q2, q3, q4 without year
            q = int(period_type[1])
            q_year = extracted.get("year", year)
            q_start_month = QUARTER_START_MONTHS[q]
            q_end_month = q_start_month + 2
            first_day = date(q_year, q_start_month, 1)
            last_day_num = calendar.monthrange(q_year, q_end_month)[1]
            last_day = date(q_year, q_end_month, last_day_num)
            return first_day, last_day

        elif period_type == "days_ago":
            days = extracted.get("days", 1)
            target_date = ref_date - timedelta(days=days)
            return target_date, target_date

        else:
            raise InvalidPeriodError(
                period=period_type,
                message=f"Unknown period type: {period_type}",
            )

    def _get_description(
        self,
        period_type: str,
        start_date: date,
        end_date: date,
        locale: str,
        extracted: dict,
    ) -> str:
        """Generate a human-readable description of the period.

        Args:
            period_type: Canonical period type.
            start_date: Start date.
            end_date: End date.
            locale: Locale for description.
            extracted: Any extracted values.

        Returns:
            Human-readable description.
        """
        year = extracted.get("year")
        quarter = extracted.get("quarter")

        if locale == "es":
            base = get_period_description_es(period_type, year, quarter)
            range_str = format_date_range_es(
                start_date.isoformat(), end_date.isoformat()
            )
        else:
            base = get_period_description_en(period_type, year, quarter)
            range_str = format_date_range_en(
                start_date.isoformat(), end_date.isoformat()
            )

        return f"{base.capitalize()} ({range_str})"
