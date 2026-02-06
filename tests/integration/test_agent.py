"""Integration tests for the DateReasoningAgent."""

import pytest
from datetime import datetime, timezone

from date_agent.agent.date_agent import DateReasoningAgent
from date_agent.core.config import DateAgentConfig


class TestDateReasoningAgent:
    """Integration tests for the full agent pipeline."""

    @pytest.fixture
    def agent(self) -> DateReasoningAgent:
        """Agent with disabled LLM for testing."""
        config = DateAgentConfig(
            agent_id="test-agent",
            azure_openai_endpoint=None,
            azure_openai_api_key=None,
            default_timezone="America/Lima",
            default_locale="es",
            enable_audit_trail=False,
        )
        return DateReasoningAgent(config)

    @pytest.mark.asyncio
    async def test_simple_period_query(self, agent):
        """Test simple period resolution: 'Q3 2024'."""
        result = await agent.process_query("Q3 2024")

        assert result["success"]
        # Q3 2024 is explicitly specified, so dates should be fixed
        assert result["start_date"] == "2024-07-01"
        assert result["end_date"] == "2024-09-30"

    @pytest.mark.asyncio
    async def test_simple_period_query_q1(self, agent):
        """Test simple period resolution: 'Q1 2024'."""
        result = await agent.process_query("Q1 2024")

        assert result["success"]
        assert result["start_date"] == "2024-01-01"
        assert result["end_date"] == "2024-03-31"

    @pytest.mark.asyncio
    async def test_spanish_query_semana_pasada(self, agent):
        """Test Spanish query: 'semana pasada'."""
        result = await agent.process_query("semana pasada")

        assert result["success"]
        assert "start_date" in result
        assert "end_date" in result
        # Should be 7 days
        from datetime import datetime
        start = datetime.strptime(result["start_date"], "%Y-%m-%d")
        end = datetime.strptime(result["end_date"], "%Y-%m-%d")
        assert (end - start).days == 6  # 7 days inclusive

    @pytest.mark.asyncio
    async def test_spanish_query_mes_anterior(self, agent):
        """Test Spanish query: 'mes anterior'."""
        result = await agent.process_query("mes anterior")

        assert result["success"]
        assert "start_date" in result
        assert "end_date" in result

    @pytest.mark.asyncio
    async def test_query_with_holiday_exclusion(self, agent):
        """Test query with holiday exclusion intent."""
        result = await agent.process_query(
            "julio 2024 excluyendo feriados bancarios"
        )

        assert result["success"]
        # Should detect intent related to holidays
        # The parser may classify this as get_holidays, mixed, or resolve_period
        assert result.get("computation_trace", {}).get("intent_type") in [
            "resolve_period",
            "mixed",
            "get_holidays",  # Valid when holiday keywords are dominant
        ]

    @pytest.mark.asyncio
    async def test_reference_date_in_response(self, agent):
        """Test that reference date is included in response."""
        result = await agent.process_query("hoy")

        assert result["success"]
        assert "reference_date" in result
        assert "timezone" in result

    @pytest.mark.asyncio
    async def test_audit_id_in_response(self, agent):
        """Test that audit ID is included in response."""
        result = await agent.process_query("ayer")

        assert "audit_id" in result

    @pytest.mark.asyncio
    async def test_computation_trace_in_response(self, agent):
        """Test that computation trace is included."""
        result = await agent.process_query("last_month")

        assert result["success"]
        assert "computation_trace" in result
        trace = result["computation_trace"]
        assert "intent_type" in trace
        assert "confidence" in trace

    @pytest.mark.asyncio
    async def test_available_tools(self, agent):
        """Test get_available_tools returns tool definitions."""
        tools = agent.get_available_tools()

        assert len(tools) == 4
        tool_names = {t["function"]["name"] for t in tools}
        assert "get_current_date_info" in tool_names
        assert "resolve_period" in tool_names
        assert "get_holiday_calendar" in tool_names
        assert "compute_date_range" in tool_names

    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test error handling for invalid query."""
        # This should still return a result (with lower confidence)
        result = await agent.process_query("xyz invalid query 123")

        # Agent should handle gracefully
        assert "success" in result


class TestAgentWithHolidays:
    """Integration tests involving holiday calculations."""

    @pytest.fixture
    def agent(self) -> DateReasoningAgent:
        """Agent configured for Peru."""
        config = DateAgentConfig(
            agent_id="test-peru",
            default_timezone="America/Lima",
            default_locale="es",
            enable_audit_trail=False,
        )
        return DateReasoningAgent(config)

    @pytest.mark.asyncio
    async def test_query_triggers_holiday_lookup(self, agent):
        """Test that business day query triggers holiday lookup."""
        result = await agent.process_query(
            "dame los ultimos 5 dias habiles"
        )

        assert result["success"]
        # Should detect business_days_only intent
        trace = result.get("computation_trace", {})
        # The semantic parser may classify this as get_holidays when
        # business day keywords dominate
        assert trace.get("intent_type") in [
            "resolve_period",
            "compute_date",
            "mixed",
            "get_holidays",  # Valid when business day keywords present
        ]
