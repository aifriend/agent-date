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

    # Normalization map for common LLM output variations
    _PERIOD_NORMALIZATION_MAP = {
        # YTD variations (Spanish and English)
        "year_to_date": "ytd",
        "year-to-date": "ytd",
        "yeartodate": "ytd",
        "hasta_el_momento": "ytd",
        "hasta el momento": "ytd",
        "hasta_ahora": "ytd",
        "hasta ahora": "ytd",
        "hasta_la_fecha": "ytd",
        "hasta la fecha": "ytd",
        "al_dia_de_hoy": "ytd",
        "acumulado_del_año": "ytd",
        "acumulado_del_ano": "ytd",
        "en lo que va del año": "ytd",
        "en lo que va del ano": "ytd",
        "start_of_year_to_now": "ytd",
        "start_of_year": "ytd",
        "beginning_of_year": "ytd",
        "from_start_of_year": "ytd",
        "desde_inicio_del_año": "ytd",
        "desde_inicio_del_ano": "ytd",
        # Weekend variations
        "last_weekend": "last_weekend",
        "fin_de_semana_pasado": "last_weekend",
        # Week variations
        "previous_week": "last_week",
        "past_week": "last_week",
        "semana_pasada": "last_week",
        "ultima_semana": "last_week",
        "última_semana": "last_week",
        "semana_antepasada": "week_before_last",
        # Month variations
        "previous_month": "last_month",
        "past_month": "last_month",
        "mes_pasado": "last_month",
        "mes_anterior": "last_month",
        "ultimo_mes": "last_month",
        "último_mes": "last_month",
        # Quarter variations
        "previous_quarter": "last_quarter",
        "past_quarter": "last_quarter",
        "trimestre_pasado": "last_quarter",
        "trimestre_anterior": "last_quarter",
        "ultimo_trimestre": "last_quarter",
        "último_trimestre": "last_quarter",
        # Year variations
        "previous_year": "last_year",
        "past_year": "last_year",
        "año_pasado": "last_year",
        "ano_pasado": "last_year",
        # Recent
        "recent": "last_week",
        # Common dynamic patterns (belt-and-suspenders for LLM output)
        "last 3 months": "last_3_months",
        "last 3 days": "last_3_days",
        "last 7 days": "last_7_days",
        "last 15 days": "last_15_days",
        "last 30 days": "last_30_days",
    }

    def _normalize_period(self, period: str) -> Tuple[str, dict]:
        """Normalize a period expression from LLM or other sources.

        Handles variations like underscores, Spanish phrases, and
        dynamic 'last_N_X' patterns.

        Args:
            period: Raw period expression.

        Returns:
            Tuple of (normalized_period, extracted_values).
        """
        normalized = period.lower().strip()

        # Direct mapping
        if normalized in self._PERIOD_NORMALIZATION_MAP:
            return self._PERIOD_NORMALIZATION_MAP[normalized], {}

        # Handle "last_N_business_days" patterns
        biz_match = re.match(
            r"^(?:last|últimos?|ultimos?)[_\s]?(\d+)[_\s]?(?:business[_\s]?days?|d[ií]as?\s*h[áa]biles?)$",
            normalized,
        )
        if biz_match:
            n = int(biz_match.group(1))
            return f"last_{n}_business_days", {"count": n, "unit": "business_days"}

        # Handle "last_N_X" patterns dynamically: last_3_months, last_15_days, etc.
        last_n_match = re.match(
            r"^(?:last|últimos?|ultimos?)[_\s]?(\d+)[_\s]?(days?|d[ií]as?|weeks?|semanas?|months?|meses?)$",
            normalized,
        )
        if last_n_match:
            n = int(last_n_match.group(1))
            raw_unit = last_n_match.group(2).rstrip("s")
            # Normalize unit to English
            unit_map = {
                "day": "days", "dia": "days", "día": "days",
                "week": "weeks", "semana": "weeks",
                "month": "months", "mes": "months", "mese": "months",
            }
            unit = unit_map.get(raw_unit, f"{raw_unit}s")
            return f"last_{n}_{unit}", {"count": n, "unit": unit}

        # Handle bare month names (Spanish/English)
        month_names = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }
        if normalized in month_names:
            month_num = month_names[normalized]
            return f"named_month_{month_num}", {"month": month_num}

        # Handle bare year: "2024"
        if re.match(r"^\d{4}$", normalized):
            return f"year_{normalized}", {"year": int(normalized)}

        # Handle explicit date range: "2025-01-01 to 2025-01-15"
        range_match = re.match(
            r"^(\d{4}-\d{2}-\d{2})\s+(?:to|a|al|-)\s+(\d{4}-\d{2}-\d{2})$",
            normalized,
        )
        if range_match:
            return f"custom:{range_match.group(1)}:{range_match.group(2)}", {
                "start_date": range_match.group(1),
                "end_date": range_match.group(2),
            }

        # Handle comma-separated periods (comparison from LLM)
        if "," in normalized:
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) == 2:
                return f"comparison:{parts[0]}:{parts[1]}", {}

        return normalized, {}

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

        # Custom date range: "custom:2025-01-01:2025-01-15"
        custom_match = re.match(r"^custom:(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})$", normalized)
        if custom_match:
            return "custom", {
                "start_date": custom_match.group(1),
                "end_date": custom_match.group(2),
            }

        # Bare year: "year_2024"
        year_match = re.match(r"^year_(\d{4})$", normalized)
        if year_match:
            return "named_year", {"year": int(year_match.group(1))}

        # Bare month: "named_month_8" (August)
        month_match = re.match(r"^named_month_(\d{1,2})$", normalized)
        if month_match:
            return "named_month", {"month": int(month_match.group(1))}

        # Try named quarter pattern: Q1 2024, q3_2024, etc.
        quarter_match = re.match(r"^q([1-4])[\s_]?(\d{4})$", normalized)
        if quarter_match:
            return "named_quarter", {
                "quarter": int(quarter_match.group(1)),
                "year": int(quarter_match.group(2)),
            }

        # Comparison queries: "comparison:q1_2024:q2_2024"
        comparison_match = re.match(r"^comparison:(.+):(.+)$", normalized)
        if comparison_match:
            # Return first period; the agent/decomposer handles both periods
            first_period = comparison_match.group(1)
            return self._parse_period(first_period, locale)

        # Check if it's already a dynamic last_N_X pattern or extended period type
        if re.match(r"^last_\d+_(days|weeks|months|business_days)$", normalized):
            return normalized, {}
        if normalized in ("last_weekend", "recent"):
            return normalized, {}

        # Day-of-week filter: "dow_filter:0:last_month"
        dow_match = re.match(r"^dow_filter:(\d):(.+)$", normalized)
        if dow_match:
            dow = int(dow_match.group(1))
            base_period = dow_match.group(2)
            # Parse the base period, add dow filter to extracted
            base_type, base_extracted = self._parse_period(base_period, locale)
            base_extracted["day_of_week_filter"] = dow
            return f"dow_filter_{base_type}", base_extracted

        # Try normalization (handles LLM output variations and last_N_X patterns)
        norm_period, norm_extracted = self._normalize_period(normalized)
        if norm_period != normalized:
            # Check if normalized form is a canonical name or extended type
            if norm_period in [p.value for p in PeriodType]:
                return norm_period, norm_extracted
            if norm_period in ("last_weekend", "recent"):
                return norm_period, norm_extracted
            # Check if it's a dynamic last_N_X pattern (including business_days)
            if re.match(r"^last_\d+_(days|weeks|months|business_days)$", norm_period):
                return norm_period, norm_extracted
            # Check for named_month pattern
            month_m = re.match(r"^named_month_(\d{1,2})$", norm_period)
            if month_m:
                return "named_month", {"month": int(month_m.group(1))}
            # Check for year, custom, comparison patterns from normalization
            if norm_period.startswith("year_"):
                year_m = re.match(r"^year_(\d{4})$", norm_period)
                if year_m:
                    return "named_year", {"year": int(year_m.group(1))}
            if norm_period.startswith("custom:"):
                custom_m = re.match(r"^custom:(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})$", norm_period)
                if custom_m:
                    return "custom", {
                        "start_date": custom_m.group(1),
                        "end_date": custom_m.group(2),
                    }
            if norm_period.startswith("comparison:"):
                comp_m = re.match(r"^comparison:(.+):(.+)$", norm_period)
                if comp_m:
                    first_p = comp_m.group(1)
                    return self._parse_period(first_p, locale)

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

        elif period_type == "last_weekend":
            # Last weekend = previous Saturday and Sunday
            days_since_monday = ref_date.weekday()
            this_monday = ref_date - timedelta(days=days_since_monday)
            # Last Sunday is the day before this Monday
            last_sunday = this_monday - timedelta(days=1)
            last_saturday = last_sunday - timedelta(days=1)
            return last_saturday, last_sunday

        elif period_type == "recent":
            # "Recent" = last 7 days (rolling)
            start_date = ref_date - timedelta(days=7)
            return start_date, ref_date

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

        elif period_type == "named_year":
            # Bare year: "2024" -> Jan 1 to Dec 31
            target_year = extracted.get("year", year)
            return date(target_year, 1, 1), date(target_year, 12, 31)

        elif period_type == "named_month":
            # Bare month: "agosto" -> August 1-31 of the most recent occurrence
            target_month = extracted.get("month", 1)
            target_year = extracted.get("year", year)
            # If the month hasn't occurred yet this year, use last year
            if target_month > month or (target_month == month and ref_date.day < calendar.monthrange(year, target_month)[1]):
                target_year = year  # Current year (month hasn't ended yet or is current)
            if target_month > month:
                target_year = year - 1  # Month hasn't happened this year yet
            first_day = date(target_year, target_month, 1)
            last_day_num = calendar.monthrange(target_year, target_month)[1]
            last_day = date(target_year, target_month, last_day_num)
            return first_day, last_day

        elif period_type == "custom":
            # Explicit date range: custom with start_date and end_date
            start_str = extracted.get("start_date")
            end_str = extracted.get("end_date")
            if start_str and end_str:
                start = datetime.strptime(start_str, "%Y-%m-%d").date()
                end = datetime.strptime(end_str, "%Y-%m-%d").date()
                return start, end
            raise InvalidPeriodError(
                period=period_type,
                message="Custom period requires start_date and end_date",
            )

        else:
            # Dynamic last_N_business_days patterns
            biz_match = re.match(r"^last_(\d+)_business_days$", period_type)
            if biz_match:
                n = int(biz_match.group(1))
                # Walk backwards counting only business days (Mon-Fri)
                count = 0
                current = ref_date
                while count < n:
                    current = current - timedelta(days=1)
                    if current.weekday() < 5:  # Monday=0 to Friday=4
                        count += 1
                return current, ref_date

            # Day-of-week filter patterns: dow_filter_last_month, dow_filter_this_month
            dow_filter_match = re.match(r"^dow_filter_(.+)$", period_type)
            if dow_filter_match:
                base_period = dow_filter_match.group(1)
                # Resolve base period first
                base_extracted = {k: v for k, v in extracted.items() if k != "day_of_week_filter"}
                start, end = self._resolve_to_dates(base_period, base_extracted, ref_date)
                # The day_of_week_filter is in extracted but the range is the base period range
                # The agent/caller can use day_of_week_filter to post-filter
                return start, end

            # Dynamic last_N_X patterns: last_3_months, last_15_days, last_2_weeks
            last_n_match = re.match(r"^last_(\d+)_(days|weeks|months)$", period_type)
            if last_n_match:
                n = int(last_n_match.group(1))
                unit = last_n_match.group(2)

                if unit == "days":
                    start_date = ref_date - timedelta(days=n)
                    return start_date, ref_date
                elif unit == "weeks":
                    start_date = ref_date - timedelta(weeks=n)
                    return start_date, ref_date
                elif unit == "months":
                    # Go back N months
                    target_month = month - n
                    target_year = year
                    while target_month <= 0:
                        target_month += 12
                        target_year -= 1
                    start_date = date(target_year, target_month, 1)
                    return start_date, ref_date

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
        # For named_month, pass month number via quarter param (overloaded)
        if period_type == "named_month" and "month" in extracted:
            quarter = extracted["month"]

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
