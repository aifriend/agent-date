"""Unit tests for resolve_period tool."""

import pytest
from datetime import datetime, timezone

from date_agent.tools.resolve_period_tool import ResolvePeriodTool
from date_agent.core.config import ToolExecutionContext


class TestResolvePeriodTool:
    """Tests for the resolve_period tool."""

    @pytest.fixture
    def tool(self) -> ResolvePeriodTool:
        return ResolvePeriodTool()

    @pytest.mark.asyncio
    async def test_resolve_today(self, tool, tool_execution_context):
        """Test resolving 'today'."""
        result = await tool.execute(tool_execution_context, period="today")

        assert result.success
        assert result.output.start_date == "2024-07-15"
        assert result.output.end_date == "2024-07-15"
        assert result.output.calendar_days == 1
        assert result.output.period_type == "today"

    @pytest.mark.asyncio
    async def test_resolve_yesterday(self, tool, tool_execution_context):
        """Test resolving 'yesterday'."""
        result = await tool.execute(tool_execution_context, period="yesterday")

        assert result.success
        assert result.output.start_date == "2024-07-14"
        assert result.output.end_date == "2024-07-14"
        assert result.output.period_type == "yesterday"

    @pytest.mark.asyncio
    async def test_resolve_this_week(self, tool, tool_execution_context):
        """Test resolving 'this_week' (ref is Monday July 15)."""
        result = await tool.execute(tool_execution_context, period="this_week")

        assert result.success
        assert result.output.start_date == "2024-07-15"
        assert result.output.end_date == "2024-07-21"
        assert result.output.calendar_days == 7

    @pytest.mark.asyncio
    async def test_resolve_last_week(self, tool, tool_execution_context):
        """Test resolving 'last_week'."""
        result = await tool.execute(tool_execution_context, period="last_week")

        assert result.success
        assert result.output.start_date == "2024-07-08"
        assert result.output.end_date == "2024-07-14"
        assert result.output.calendar_days == 7
        assert result.output.period_type == "last_week"

    @pytest.mark.asyncio
    async def test_resolve_week_before_last(self, tool, tool_execution_context):
        """Test resolving 'week_before_last' (semana antepasada)."""
        result = await tool.execute(
            tool_execution_context,
            period="week_before_last",
        )

        assert result.success
        assert result.output.start_date == "2024-07-01"
        assert result.output.end_date == "2024-07-07"

    @pytest.mark.asyncio
    async def test_resolve_this_month(self, tool, tool_execution_context):
        """Test resolving 'this_month'."""
        result = await tool.execute(tool_execution_context, period="this_month")

        assert result.success
        assert result.output.start_date == "2024-07-01"
        assert result.output.end_date == "2024-07-31"
        assert result.output.calendar_days == 31

    @pytest.mark.asyncio
    async def test_resolve_last_month(self, tool, tool_execution_context):
        """Test resolving 'last_month'."""
        result = await tool.execute(tool_execution_context, period="last_month")

        assert result.success
        assert result.output.start_date == "2024-06-01"
        assert result.output.end_date == "2024-06-30"
        assert result.output.calendar_days == 30
        assert result.output.period_type == "last_month"

    @pytest.mark.asyncio
    async def test_resolve_this_quarter(self, tool, tool_execution_context):
        """Test resolving 'this_quarter' (Q3 for July)."""
        result = await tool.execute(tool_execution_context, period="this_quarter")

        assert result.success
        assert result.output.start_date == "2024-07-01"
        assert result.output.end_date == "2024-09-30"
        assert result.output.period_type == "this_quarter"

    @pytest.mark.asyncio
    async def test_resolve_last_quarter(self, tool, tool_execution_context):
        """Test resolving 'last_quarter' (Q2 for July)."""
        result = await tool.execute(tool_execution_context, period="last_quarter")

        assert result.success
        assert result.output.start_date == "2024-04-01"
        assert result.output.end_date == "2024-06-30"
        assert result.output.period_type == "last_quarter"

    @pytest.mark.asyncio
    async def test_resolve_named_quarter_q3_2024(self, tool, tool_execution_context):
        """Test resolving 'Q3 2024'."""
        result = await tool.execute(tool_execution_context, period="Q3 2024")

        assert result.success
        assert result.output.start_date == "2024-07-01"
        assert result.output.end_date == "2024-09-30"
        assert result.output.period_type == "named_quarter"

    @pytest.mark.asyncio
    async def test_resolve_named_quarter_q1_2024(self, tool, tool_execution_context):
        """Test resolving 'Q1 2024'."""
        result = await tool.execute(tool_execution_context, period="Q1 2024")

        assert result.success
        assert result.output.start_date == "2024-01-01"
        assert result.output.end_date == "2024-03-31"

    @pytest.mark.asyncio
    async def test_resolve_ytd(self, tool, tool_execution_context):
        """Test resolving 'ytd' (year to date)."""
        result = await tool.execute(tool_execution_context, period="ytd")

        assert result.success
        assert result.output.start_date == "2024-01-01"
        assert result.output.end_date == "2024-07-15"

    @pytest.mark.asyncio
    async def test_resolve_spanish_semana_pasada(self, tool, tool_execution_context):
        """Test resolving Spanish 'semana pasada'."""
        result = await tool.execute(
            tool_execution_context,
            period="semana pasada",
            locale="es",
        )

        assert result.success
        assert result.output.start_date == "2024-07-08"
        assert result.output.end_date == "2024-07-14"
        assert result.output.period_type == "last_week"

    @pytest.mark.asyncio
    async def test_resolve_spanish_mes_anterior(self, tool, tool_execution_context):
        """Test resolving Spanish 'mes anterior'."""
        result = await tool.execute(
            tool_execution_context,
            period="mes anterior",
            locale="es",
        )

        assert result.success
        assert result.output.start_date == "2024-06-01"
        assert result.output.end_date == "2024-06-30"
        assert result.output.period_type == "last_month"

    @pytest.mark.asyncio
    async def test_resolve_spanish_trimestre_pasado(self, tool, tool_execution_context):
        """Test resolving Spanish 'trimestre pasado'."""
        result = await tool.execute(
            tool_execution_context,
            period="trimestre pasado",
            locale="es",
        )

        assert result.success
        assert result.output.start_date == "2024-04-01"
        assert result.output.end_date == "2024-06-30"

    @pytest.mark.asyncio
    async def test_resolve_spanish_semana_antepasada(self, tool, tool_execution_context):
        """Test resolving Spanish 'semana antepasada' (week before last)."""
        result = await tool.execute(
            tool_execution_context,
            period="semana antepasada",
            locale="es",
        )

        assert result.success
        assert result.output.start_date == "2024-07-01"
        assert result.output.end_date == "2024-07-07"
        assert result.output.period_type == "week_before_last"

    @pytest.mark.asyncio
    async def test_localized_description(self, tool, tool_execution_context):
        """Test that description is localized."""
        result = await tool.execute(
            tool_execution_context,
            period="last_week",
            locale="es",
        )

        assert result.success
        assert "semana" in result.output.description_localized.lower()

    @pytest.mark.asyncio
    async def test_reference_date_override(self, tool, tool_execution_context):
        """Test reference date override."""
        result = await tool.execute(
            tool_execution_context,
            period="this_month",
            reference_date="2024-03-15",
        )

        assert result.success
        # March 2024
        assert result.output.start_date == "2024-03-01"
        assert result.output.end_date == "2024-03-31"
        assert result.output.reference_date_used == "2024-03-15"

    @pytest.mark.asyncio
    async def test_invalid_period(self, tool, tool_execution_context):
        """Test that invalid period raises error."""
        result = await tool.execute(
            tool_execution_context,
            period="invalid_period_xyz",
        )

        assert not result.success
        assert "error" in result.error.lower() or "cannot" in result.error.lower()
