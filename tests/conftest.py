"""Pytest fixtures for Date Reasoning Agent tests."""

import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from date_agent.core.config import DateAgentConfig, ToolExecutionContext
from date_agent.agent.date_agent import DateReasoningAgent


@pytest.fixture
def fixed_reference_date() -> datetime:
    """Fixed reference date for deterministic testing.

    All tests use this as 'today' to ensure reproducibility.
    Set to July 15, 2024 (Monday) for comprehensive testing.
    """
    return datetime(2024, 7, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def peru_timezone() -> ZoneInfo:
    """Peru timezone for testing."""
    return ZoneInfo("America/Lima")


@pytest.fixture
def test_config() -> DateAgentConfig:
    """Test configuration (no Azure OpenAI to avoid API calls)."""
    return DateAgentConfig(
        agent_id="test-agent",
        azure_openai_endpoint=None,  # Disable LLM calls
        azure_openai_api_key=None,
        default_timezone="America/Lima",
        default_locale="es",
        max_lookback_months=6,
        enable_audit_trail=False,  # Disable for faster tests
    )


@pytest.fixture
def tool_execution_context(
    fixed_reference_date: datetime,
    test_config: DateAgentConfig,
) -> ToolExecutionContext:
    """Standard execution context for tool tests."""
    return ToolExecutionContext(
        execution_id="test-001",
        reference_date=fixed_reference_date,
        timezone="America/Lima",
        calendar_system="GREGORIAN",
        locale="es",
        audit_enabled=False,
    )


@pytest.fixture
def agent(test_config: DateAgentConfig) -> DateReasoningAgent:
    """Test agent instance."""
    return DateReasoningAgent(test_config)


@pytest.fixture
def peru_holidays_july_2024() -> list[dict]:
    """Peru banking holidays in July 2024."""
    return [
        {
            "date": "2024-07-28",
            "name": "Independence Day",
            "name_localized": "Fiestas Patrias",
        },
        {
            "date": "2024-07-29",
            "name": "Independence Day (Day 2)",
            "name_localized": "Fiestas Patrias",
        },
    ]


@pytest.fixture
def sample_spanish_queries() -> list[tuple[str, str]]:
    """Sample Spanish date queries and expected period types."""
    return [
        ("semana pasada", "last_week"),
        ("la semana pasada", "last_week"),
        ("mes anterior", "last_month"),
        ("ultimo mes", "last_month"),
        ("trimestre pasado", "last_quarter"),
        ("semana antepasada", "week_before_last"),
        ("hoy", "today"),
        ("ayer", "yesterday"),
    ]


@pytest.fixture
def sample_english_queries() -> list[tuple[str, str]]:
    """Sample English date queries and expected period types."""
    return [
        ("last week", "last_week"),
        ("this month", "this_month"),
        ("last quarter", "last_quarter"),
        ("Q3 2024", "named_quarter"),
        ("today", "today"),
        ("yesterday", "yesterday"),
    ]
