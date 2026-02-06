"""compute_date_range tool - performs date arithmetic."""

import calendar
from datetime import date, datetime, timedelta
from typing import Tuple, List, Optional

from date_agent.calendars import get_calendar
from date_agent.core.config import ToolExecutionContext
from date_agent.core.constants import DateOperation, get_quarter, QUARTER_START_MONTHS
from date_agent.core.exceptions import CalendarNotFoundError
from date_agent.models.tool_schemas import (
    ComputeDateRangeInput,
    ComputeDateRangeOutput,
    ChainedOperation,
)
from date_agent.tools.base_tool import BaseDateTool


class ComputeDateRangeTool(BaseDateTool[ComputeDateRangeInput, ComputeDateRangeOutput]):
    """Performs date arithmetic with calendar-aware calculations.

    Supports adding/subtracting calendar days, business days, weeks, months,
    and finding specific dates like month-end or next business day.
    """

    @property
    def name(self) -> str:
        return "compute_date_range"

    @property
    def description(self) -> str:
        return """Performs date arithmetic operations like adding/subtracting days, weeks, months,
or finding specific dates like month-end or next business day.

Key capabilities:
- ADD/SUBTRACT calendar days, business days, weeks, months
- Find MONTH_END, MONTH_START, QUARTER_END, QUARTER_START
- Find NEXT_BUSINESS_DAY, PREVIOUS_BUSINESS_DAY
- Chain operations for compositional queries (e.g., "3 days before each month-end")

The calendar_system parameter determines which holidays to exclude when
calculating business days.

IMPORTANT: This tool is the SOURCE OF TRUTH for date calculations.
The agent should NEVER attempt to compute dates itself - always use this tool."""

    @property
    def input_schema(self) -> type[ComputeDateRangeInput]:
        return ComputeDateRangeInput

    @property
    def output_schema(self) -> type[ComputeDateRangeOutput]:
        return ComputeDateRangeOutput

    async def _execute(
        self,
        context: ToolExecutionContext,
        input_data: ComputeDateRangeInput,
    ) -> Tuple[ComputeDateRangeOutput, List[str]]:
        """Execute the date computation.

        Args:
            context: Execution context.
            input_data: Tool input parameters.

        Returns:
            Tuple of (ComputeDateRangeOutput, computation_steps).
        """
        steps: List[str] = []
        holidays_excluded: List[str] = []
        weekends_excluded: List[str] = []

        # Parse base date
        base_date = datetime.strptime(input_data.base_date, "%Y-%m-%d").date()
        steps.append(f"Base date: {base_date.isoformat()}")

        # Get calendar for business day calculations
        try:
            cal = get_calendar(input_data.calendar_system)
        except ValueError as e:
            raise CalendarNotFoundError(
                calendar_system=input_data.calendar_system,
                message=str(e),
            )

        # Execute the primary operation
        result_date, op_steps, op_holidays, op_weekends = self._execute_operation(
            base_date,
            input_data.operation,
            input_data.value,
            cal,
        )
        steps.extend(op_steps)
        holidays_excluded.extend(op_holidays)
        weekends_excluded.extend(op_weekends)

        # Execute chained operations
        if input_data.then_operations:
            for chain_op in input_data.then_operations:
                chain_cal = cal
                if chain_op.calendar_system:
                    try:
                        chain_cal = get_calendar(chain_op.calendar_system)
                    except ValueError:
                        pass  # Use original calendar

                result_date, op_steps, op_holidays, op_weekends = self._execute_operation(
                    result_date,
                    chain_op.operation,
                    chain_op.value,
                    chain_cal,
                )
                steps.extend(op_steps)
                holidays_excluded.extend(op_holidays)
                weekends_excluded.extend(op_weekends)

        steps.append(f"Result: {result_date.isoformat()}")

        output = ComputeDateRangeOutput(
            result_date=result_date.isoformat(),
            operations_applied=steps,
            holidays_excluded=holidays_excluded if holidays_excluded else None,
            weekends_excluded=weekends_excluded if weekends_excluded else None,
            calendar_system_used=input_data.calendar_system,
            base_date_used=input_data.base_date,
        )

        return output, steps

    def _execute_operation(
        self,
        base_date: date,
        operation: str,
        value: Optional[int],
        cal,
    ) -> Tuple[date, List[str], List[str], List[str]]:
        """Execute a single date operation.

        Args:
            base_date: Starting date.
            operation: Operation to perform.
            value: Numeric value (if applicable).
            cal: Calendar instance.

        Returns:
            Tuple of (result_date, steps, holidays_excluded, weekends_excluded).
        """
        steps: List[str] = []
        holidays_excluded: List[str] = []
        weekends_excluded: List[str] = []

        op = operation.lower()

        if op == DateOperation.ADD_CALENDAR_DAYS.value:
            result = base_date + timedelta(days=value or 0)
            steps.append(f"Added {value} calendar days")

        elif op == DateOperation.SUBTRACT_CALENDAR_DAYS.value:
            result = base_date - timedelta(days=value or 0)
            steps.append(f"Subtracted {value} calendar days")

        elif op == DateOperation.ADD_BUSINESS_DAYS.value:
            result, h_exc, w_exc = self._add_business_days_tracked(
                base_date, value or 0, cal
            )
            holidays_excluded.extend(h_exc)
            weekends_excluded.extend(w_exc)
            steps.append(f"Added {value} business days")

        elif op == DateOperation.SUBTRACT_BUSINESS_DAYS.value:
            result, h_exc, w_exc = self._add_business_days_tracked(
                base_date, -(value or 0), cal
            )
            holidays_excluded.extend(h_exc)
            weekends_excluded.extend(w_exc)
            steps.append(f"Subtracted {value} business days")

        elif op == DateOperation.ADD_WEEKS.value:
            result = base_date + timedelta(weeks=value or 0)
            steps.append(f"Added {value} weeks")

        elif op == DateOperation.SUBTRACT_WEEKS.value:
            result = base_date - timedelta(weeks=value or 0)
            steps.append(f"Subtracted {value} weeks")

        elif op == DateOperation.ADD_MONTHS.value:
            result = self._add_months(base_date, value or 0)
            steps.append(f"Added {value} months")

        elif op == DateOperation.SUBTRACT_MONTHS.value:
            result = self._add_months(base_date, -(value or 0))
            steps.append(f"Subtracted {value} months")

        elif op == DateOperation.NEXT_BUSINESS_DAY.value:
            result = cal.next_business_day(base_date)
            steps.append(f"Next business day from {base_date}")

        elif op == DateOperation.PREVIOUS_BUSINESS_DAY.value:
            result = cal.previous_business_day(base_date)
            steps.append(f"Previous business day from {base_date}")

        elif op == DateOperation.MONTH_END.value:
            last_day = calendar.monthrange(base_date.year, base_date.month)[1]
            result = base_date.replace(day=last_day)
            steps.append(f"Month end: {result.isoformat()}")

        elif op == DateOperation.MONTH_START.value:
            result = base_date.replace(day=1)
            steps.append(f"Month start: {result.isoformat()}")

        elif op == DateOperation.QUARTER_END.value:
            q = get_quarter(base_date.month)
            q_end_month = QUARTER_START_MONTHS[q] + 2
            last_day = calendar.monthrange(base_date.year, q_end_month)[1]
            result = date(base_date.year, q_end_month, last_day)
            steps.append(f"Quarter {q} end: {result.isoformat()}")

        elif op == DateOperation.QUARTER_START.value:
            q = get_quarter(base_date.month)
            q_start_month = QUARTER_START_MONTHS[q]
            result = date(base_date.year, q_start_month, 1)
            steps.append(f"Quarter {q} start: {result.isoformat()}")

        elif op == DateOperation.WEEK_START.value:
            # Monday
            days_since_monday = base_date.weekday()
            result = base_date - timedelta(days=days_since_monday)
            steps.append(f"Week start (Monday): {result.isoformat()}")

        elif op == DateOperation.WEEK_END.value:
            # Sunday
            days_until_sunday = 6 - base_date.weekday()
            result = base_date + timedelta(days=days_until_sunday)
            steps.append(f"Week end (Sunday): {result.isoformat()}")

        else:
            raise ValueError(f"Unknown operation: {operation}")

        return result, steps, holidays_excluded, weekends_excluded

    def _add_business_days_tracked(
        self, start_date: date, days: int, cal
    ) -> Tuple[date, List[str], List[str]]:
        """Add business days and track excluded dates.

        Args:
            start_date: Starting date.
            days: Number of business days (can be negative).
            cal: Calendar instance.

        Returns:
            Tuple of (result_date, holidays_excluded, weekends_excluded).
        """
        holidays_excluded: List[str] = []
        weekends_excluded: List[str] = []

        if days == 0:
            return start_date, holidays_excluded, weekends_excluded

        direction = 1 if days > 0 else -1
        remaining = abs(days)
        current = start_date

        while remaining > 0:
            current += timedelta(days=direction)

            if cal.is_weekend(current):
                weekends_excluded.append(current.isoformat())
            elif cal.is_holiday(current):
                holiday_info = cal.get_holiday_info(current)
                if holiday_info:
                    holidays_excluded.append(
                        f"{current.isoformat()} ({holiday_info.name})"
                    )
                else:
                    holidays_excluded.append(current.isoformat())
            else:
                remaining -= 1

        return current, holidays_excluded, weekends_excluded

    def _add_months(self, d: date, months: int) -> date:
        """Add months to a date, handling edge cases.

        Args:
            d: Starting date.
            months: Number of months to add (can be negative).

        Returns:
            Resulting date.
        """
        # Calculate target year and month
        total_months = d.year * 12 + d.month - 1 + months
        target_year = total_months // 12
        target_month = total_months % 12 + 1

        # Handle day overflow (e.g., Jan 31 + 1 month = Feb 28)
        max_day = calendar.monthrange(target_year, target_month)[1]
        target_day = min(d.day, max_day)

        return date(target_year, target_month, target_day)
