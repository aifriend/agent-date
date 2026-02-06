"""get_holiday_calendar tool - returns holidays for calendar systems."""

from datetime import date, datetime, timedelta
from typing import Tuple, List

from date_agent.calendars import get_calendar
from date_agent.core.config import ToolExecutionContext
from date_agent.core.constants import WEEKEND_DAYS
from date_agent.core.exceptions import CalendarNotFoundError
from date_agent.models.tool_schemas import (
    GetHolidayCalendarInput,
    GetHolidayCalendarOutput,
    HolidayEntry,
)
from date_agent.tools.base_tool import BaseDateTool


class GetHolidayCalendarTool(BaseDateTool[GetHolidayCalendarInput, GetHolidayCalendarOutput]):
    """Returns holiday information for specific calendar systems.

    Provides the list of holidays and non-business days for a given
    calendar system within a date range.
    """

    @property
    def name(self) -> str:
        return "get_holiday_calendar"

    @property
    def description(self) -> str:
        return """Returns the list of holidays and non-business days for a specific calendar system
within a date range.

Calendar systems have different definitions of "business days":
- GREGORIAN: Only weekends are non-business days
- PERU_BANKING: Peru banking holidays + weekends

Use this tool to:
- Get the list of holidays to exclude from date calculations
- Determine business days vs calendar days
- Validate if a specific date is a business day

The agent should use this tool when the user's query involves business days,
trading days, or bank holidays."""

    @property
    def input_schema(self) -> type[GetHolidayCalendarInput]:
        return GetHolidayCalendarInput

    @property
    def output_schema(self) -> type[GetHolidayCalendarOutput]:
        return GetHolidayCalendarOutput

    async def _execute(
        self,
        context: ToolExecutionContext,
        input_data: GetHolidayCalendarInput,
    ) -> Tuple[GetHolidayCalendarOutput, List[str]]:
        """Execute the tool to get holiday calendar information.

        Args:
            context: Execution context.
            input_data: Tool input parameters.

        Returns:
            Tuple of (GetHolidayCalendarOutput, computation_steps).
        """
        steps: List[str] = []

        # Parse dates
        start_date = datetime.strptime(input_data.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(input_data.end_date, "%Y-%m-%d").date()
        steps.append(f"Date range: {start_date} to {end_date}")

        # Get the calendar
        try:
            cal = get_calendar(input_data.calendar_system)
            steps.append(f"Using calendar: {cal.name}")
        except ValueError as e:
            raise CalendarNotFoundError(
                calendar_system=input_data.calendar_system,
                message=str(e),
            )

        # Get holidays in range
        try:
            holidays = cal.get_holidays_in_range(start_date, end_date)
            steps.append(f"Found {len(holidays)} holidays in range")
        except ValueError as e:
            raise CalendarNotFoundError(
                calendar_system=input_data.calendar_system,
                message=str(e),
            )

        # Convert to output format
        holiday_entries = []
        for h in holidays:
            # Get localized name based on locale
            if input_data.locale == "es" and h.name_localized:
                localized = h.name_localized
            else:
                localized = h.name_localized

            holiday_entries.append(
                HolidayEntry(
                    date=h.date.isoformat(),
                    name=h.name,
                    name_localized=localized,
                    holiday_type=h.holiday_type,
                    observed=h.observed,
                )
            )

        # Calculate statistics
        total_calendar_days = (end_date - start_date).days + 1
        steps.append(f"Total calendar days: {total_calendar_days}")

        # Count weekends
        weekend_dates: List[str] = []
        current = start_date
        while current <= end_date:
            if current.weekday() in WEEKEND_DAYS:
                weekend_dates.append(current.isoformat())
            current += timedelta(days=1)

        total_weekend_days = len(weekend_dates)
        steps.append(f"Weekend days: {total_weekend_days}")

        # Count holidays (excluding those on weekends to avoid double-counting)
        holiday_dates_set = {h.date for h in holidays if h.observed}
        weekend_dates_set = {
            datetime.strptime(d, "%Y-%m-%d").date() for d in weekend_dates
        }

        # Holidays that fall on weekdays only
        holidays_on_weekdays = holiday_dates_set - weekend_dates_set
        total_holidays = len(holidays_on_weekdays)
        steps.append(f"Holidays on weekdays: {total_holidays}")

        # Total non-business days (weekends + holidays not on weekends)
        total_non_business_days = total_weekend_days + total_holidays
        total_business_days = total_calendar_days - total_non_business_days

        steps.append(f"Total non-business days: {total_non_business_days}")
        steps.append(f"Total business days: {total_business_days}")

        output = GetHolidayCalendarOutput(
            calendar_system=input_data.calendar_system,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            holidays=holiday_entries,
            weekend_dates=weekend_dates if input_data.include_weekends else None,
            total_calendar_days=total_calendar_days,
            total_holidays=len(holidays),  # Total holidays including those on weekends
            total_weekend_days=total_weekend_days,
            total_non_business_days=total_non_business_days,
            total_business_days=total_business_days,
        )

        return output, steps
