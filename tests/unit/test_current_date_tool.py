"""Unit tests for get_current_date_info tool."""

import pytest
from datetime import datetime, timezone

from date_agent.tools.current_date_tool import GetCurrentDateInfoTool
from date_agent.core.config import ToolExecutionContext


class TestGetCurrentDateInfoTool:
    """Tests for the get_current_date_info tool."""

    @pytest.fixture
    def tool(self) -> GetCurrentDateInfoTool:
        return GetCurrentDateInfoTool()

    @pytest.mark.asyncio
    async def test_basic_execution(self, tool, tool_execution_context):
        """Test basic tool execution returns expected fields."""
        result = await tool.execute(tool_execution_context)

        assert result.success
        assert result.output is not None
        assert result.output.date == "2024-07-15"
        assert result.output.year == 2024
        assert result.output.month == 7
        assert result.output.day == 15

    @pytest.mark.asyncio
    async def test_weekday_calculation(self, tool, tool_execution_context):
        """Test weekday is correctly calculated (July 15, 2024 is Monday)."""
        result = await tool.execute(tool_execution_context)

        assert result.success
        assert result.output.weekday == 0  # Monday
        assert result.output.weekday_name == "Monday"
        assert result.output.weekday_name_localized == "lunes"

    @pytest.mark.asyncio
    async def test_month_names(self, tool, tool_execution_context):
        """Test month names in English and Spanish."""
        result = await tool.execute(tool_execution_context, locale="es")

        assert result.success
        assert result.output.month_name == "July"
        assert result.output.month_name_localized == "julio"

    @pytest.mark.asyncio
    async def test_iso_week(self, tool, tool_execution_context):
        """Test ISO week calculation."""
        result = await tool.execute(
            tool_execution_context,
            include_week_info=True,
        )

        assert result.success
        assert result.output.iso_week is not None
        assert result.output.iso_year == 2024

    @pytest.mark.asyncio
    async def test_week_boundaries(self, tool, tool_execution_context):
        """Test week boundary calculation (July 15, 2024 is Monday)."""
        result = await tool.execute(
            tool_execution_context,
            include_boundaries=True,
        )

        assert result.success
        # July 15 is Monday, so week is July 15-21
        assert result.output.this_week_monday == "2024-07-15"
        assert result.output.this_week_sunday == "2024-07-21"
        # Last week was July 8-14
        assert result.output.last_week_monday == "2024-07-08"
        assert result.output.last_week_sunday == "2024-07-14"

    @pytest.mark.asyncio
    async def test_month_boundaries(self, tool, tool_execution_context):
        """Test month boundary calculation."""
        result = await tool.execute(
            tool_execution_context,
            include_boundaries=True,
        )

        assert result.success
        assert result.output.this_month_start == "2024-07-01"
        assert result.output.this_month_end == "2024-07-31"
        assert result.output.last_month_start == "2024-06-01"
        assert result.output.last_month_end == "2024-06-30"

    @pytest.mark.asyncio
    async def test_quarter_info(self, tool, tool_execution_context):
        """Test quarter calculation (July is Q3)."""
        result = await tool.execute(
            tool_execution_context,
            include_boundaries=True,
        )

        assert result.success
        assert result.output.current_quarter == 3
        assert result.output.quarter_start == "2024-07-01"
        assert result.output.quarter_end == "2024-09-30"

    @pytest.mark.asyncio
    async def test_lookback_limit(self, tool, tool_execution_context):
        """Test financial lookback limit calculation."""
        result = await tool.execute(
            tool_execution_context,
            lookback_months=6,
            include_boundaries=True,
        )

        assert result.success
        # 6 months before July 15, 2024 = January 15, 2024
        assert result.output.lookback_limit_date == "2024-01-15"

    @pytest.mark.asyncio
    async def test_different_timezone(self, tool, fixed_reference_date):
        """Test with different timezone."""
        context = ToolExecutionContext(
            execution_id="test",
            reference_date=fixed_reference_date,
            timezone="America/New_York",
            calendar_system="GREGORIAN",
            locale="en",
        )

        result = await tool.execute(context, timezone="America/New_York")

        assert result.success
        assert result.output.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_computation_steps(self, tool, tool_execution_context):
        """Test that computation steps are recorded."""
        result = await tool.execute(tool_execution_context)

        assert result.success
        assert len(result.computation_steps) > 0
        assert any("Reference date" in step for step in result.computation_steps)
