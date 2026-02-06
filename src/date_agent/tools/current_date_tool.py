"""get_current_date_info tool - establishes the immutable reference point.

This tool MUST be called FIRST to establish the anchor for all date calculations.
Ported from BIO project's get_current_date_info() function.
"""

import calendar
from datetime import datetime, timedelta
from typing import Tuple, List
from zoneinfo import ZoneInfo

from date_agent.core.config import ToolExecutionContext
from date_agent.core.constants import (
    TIMEZONE_MAPPINGS,
    get_quarter,
    QUARTER_START_MONTHS,
    MONDAY,
    SUNDAY,
)
from date_agent.localization import get_month_name, get_weekday_name
from date_agent.localization.english import MONTH_NAMES_EN, WEEKDAY_NAMES_EN
from date_agent.models.tool_schemas import CurrentDateInput, CurrentDateOutput
from date_agent.tools.base_tool import BaseDateTool


class GetCurrentDateInfoTool(BaseDateTool[CurrentDateInput, CurrentDateOutput]):
    """Returns the immutable reference point for all date calculations.

    This tool MUST be called FIRST before any other date calculations.
    It establishes:
    - Today's exact date and time in the specified timezone
    - Pre-calculated week/month/quarter boundaries
    - The financial lookback limit (typically 6 months)

    The agent should NEVER compute dates manually - always use this tool first.
    """

    @property
    def name(self) -> str:
        return "get_current_date_info"

    @property
    def description(self) -> str:
        return """Returns comprehensive information about the current date in the specified timezone.
This is the IMMUTABLE REFERENCE POINT - all other date calculations must use this as the anchor.

Use this tool FIRST to establish:
- Today's exact date and time
- The financial lookback limit (typically 6 months)
- Pre-calculated week/month boundaries for common queries

The agent should NEVER compute dates manually - always use this tool to get the reference."""

    @property
    def input_schema(self) -> type[CurrentDateInput]:
        return CurrentDateInput

    @property
    def output_schema(self) -> type[CurrentDateOutput]:
        return CurrentDateOutput

    async def _execute(
        self,
        context: ToolExecutionContext,
        input_data: CurrentDateInput,
    ) -> Tuple[CurrentDateOutput, List[str]]:
        """Execute the tool to get current date information.

        Args:
            context: Execution context with reference_date.
            input_data: Tool input parameters.

        Returns:
            Tuple of (CurrentDateOutput, computation_steps).
        """
        steps: List[str] = []

        # Use the reference date from context (this ensures immutability)
        reference_utc = context.reference_date
        steps.append(f"Reference date (UTC): {reference_utc.isoformat()}")

        # Convert to requested timezone
        try:
            tz = TIMEZONE_MAPPINGS.get(input_data.timezone)
            if tz is None:
                tz = ZoneInfo(input_data.timezone)
        except Exception:
            # Fallback to UTC
            tz = ZoneInfo("UTC")
            steps.append(f"Warning: Unknown timezone '{input_data.timezone}', using UTC")

        now = reference_utc.astimezone(tz)
        steps.append(f"Converted to timezone: {input_data.timezone}")

        # Basic date info
        date_str = now.strftime("%Y-%m-%d")
        datetime_iso = now.isoformat()
        timestamp_utc = int(reference_utc.timestamp())

        # Date components
        year = now.year
        month = now.month
        day = now.day
        weekday = now.weekday()  # 0=Monday, 6=Sunday

        # Localized names
        weekday_name = WEEKDAY_NAMES_EN[weekday]
        weekday_name_localized = get_weekday_name(weekday, input_data.locale)
        month_name = MONTH_NAMES_EN[month]
        month_name_localized = get_month_name(month, input_data.locale)

        steps.append(f"Date: {date_str} ({weekday_name_localized})")

        # ISO week info
        iso_week = None
        iso_year = None
        if input_data.include_week_info:
            iso_cal = now.isocalendar()
            iso_week = iso_cal[1]
            iso_year = iso_cal[0]
            steps.append(f"ISO week: {iso_year}-W{iso_week:02d}")

        # Quarter info
        current_quarter = get_quarter(month)
        steps.append(f"Quarter: Q{current_quarter}")

        # Boundaries (if requested)
        this_week_monday = None
        this_week_sunday = None
        last_week_monday = None
        last_week_sunday = None
        this_month_start = None
        this_month_end = None
        last_month_start = None
        last_month_end = None
        quarter_start = None
        quarter_end = None
        lookback_limit_date = None

        if input_data.include_boundaries:
            # Week boundaries
            days_since_monday = weekday
            this_monday = now - timedelta(days=days_since_monday)
            this_sunday = this_monday + timedelta(days=6)
            this_week_monday = this_monday.strftime("%Y-%m-%d")
            this_week_sunday = this_sunday.strftime("%Y-%m-%d")

            last_monday = this_monday - timedelta(days=7)
            last_sunday = last_monday + timedelta(days=6)
            last_week_monday = last_monday.strftime("%Y-%m-%d")
            last_week_sunday = last_sunday.strftime("%Y-%m-%d")

            steps.append(f"This week: {this_week_monday} to {this_week_sunday}")
            steps.append(f"Last week: {last_week_monday} to {last_week_sunday}")

            # Month boundaries
            this_month_start = now.replace(day=1).strftime("%Y-%m-%d")
            last_day = calendar.monthrange(year, month)[1]
            this_month_end = now.replace(day=last_day).strftime("%Y-%m-%d")

            # Last month
            if month == 1:
                last_month_num = 12
                last_month_year = year - 1
            else:
                last_month_num = month - 1
                last_month_year = year

            last_month_start_dt = now.replace(
                year=last_month_year, month=last_month_num, day=1
            )
            last_month_last_day = calendar.monthrange(last_month_year, last_month_num)[1]
            last_month_end_dt = last_month_start_dt.replace(day=last_month_last_day)

            last_month_start = last_month_start_dt.strftime("%Y-%m-%d")
            last_month_end = last_month_end_dt.strftime("%Y-%m-%d")

            steps.append(f"This month: {this_month_start} to {this_month_end}")
            steps.append(f"Last month: {last_month_start} to {last_month_end}")

            # Quarter boundaries
            q_start_month = QUARTER_START_MONTHS[current_quarter]
            q_end_month = q_start_month + 2
            quarter_start_dt = now.replace(month=q_start_month, day=1)
            q_end_last_day = calendar.monthrange(year, q_end_month)[1]
            quarter_end_dt = now.replace(month=q_end_month, day=q_end_last_day)

            quarter_start = quarter_start_dt.strftime("%Y-%m-%d")
            quarter_end = quarter_end_dt.strftime("%Y-%m-%d")

            steps.append(f"This quarter: {quarter_start} to {quarter_end}")

            # Financial lookback limit (from BIO: 6-month lookback)
            lookback_months = input_data.lookback_months
            month_n_ago = month - lookback_months
            year_n_ago = year

            while month_n_ago <= 0:
                month_n_ago += 12
                year_n_ago -= 1

            # Ensure day is valid for the target month
            limit_day = min(day, calendar.monthrange(year_n_ago, month_n_ago)[1])
            lookback_limit_dt = now.replace(
                year=year_n_ago, month=month_n_ago, day=limit_day
            )
            lookback_limit_date = lookback_limit_dt.strftime("%Y-%m-%d")

            steps.append(
                f"Lookback limit ({lookback_months} months): {lookback_limit_date}"
            )

        # Build output
        output = CurrentDateOutput(
            date=date_str,
            datetime_iso=datetime_iso,
            timestamp_utc=timestamp_utc,
            timezone=input_data.timezone,
            year=year,
            month=month,
            day=day,
            weekday=weekday,
            weekday_name=weekday_name,
            weekday_name_localized=weekday_name_localized,
            month_name=month_name,
            month_name_localized=month_name_localized,
            iso_week=iso_week,
            iso_year=iso_year,
            current_quarter=current_quarter,
            this_week_monday=this_week_monday,
            this_week_sunday=this_week_sunday,
            last_week_monday=last_week_monday,
            last_week_sunday=last_week_sunday,
            this_month_start=this_month_start,
            this_month_end=this_month_end,
            last_month_start=last_month_start,
            last_month_end=last_month_end,
            quarter_start=quarter_start,
            quarter_end=quarter_end,
            lookback_limit_date=lookback_limit_date,
        )

        return output, steps
