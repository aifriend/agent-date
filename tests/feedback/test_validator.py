"""Tests for the Validator."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from date_agent.feedback.models import (
    ChallengerQuery,
    QueryCategory,
    ValidationResult,
)
from date_agent.feedback.validator import Validator


REFERENCE_DATE = date(2024, 7, 15)


def make_query(**kwargs):
    """Helper to create a ChallengerQuery with defaults."""
    defaults = {
        "query_id": "test_001",
        "query_text": "test query",
        "language": "es",
        "category": QueryCategory.SIMPLE_PERIOD,
        "reference_date": REFERENCE_DATE,
        "expected_success": True,
        "expected_start_date": "2024-07-08",
        "expected_end_date": "2024-07-14",
        "expected_calendar_days": 7,
        "expected_intent_type": "resolve_period",
    }
    defaults.update(kwargs)
    return ChallengerQuery(**defaults)


class TestValidator:
    """Test validation logic with mock agent."""

    @pytest.fixture
    def mock_agent(self):
        agent = MagicMock()
        agent.process_query = AsyncMock()
        return agent

    @pytest.fixture
    def validator(self, mock_agent):
        return Validator(mock_agent)

    @pytest.mark.asyncio
    async def test_pass_when_all_match(self, validator, mock_agent):
        """Should PASS when agent output matches ground truth."""
        mock_agent.process_query.return_value = {
            "success": True,
            "start_date": "2024-07-08",
            "end_date": "2024-07-14",
            "calendar_days": 7,
        }
        query = make_query()
        report = await validator.validate(query)
        assert report.result == ValidationResult.PASS
        assert not report.mismatches

    @pytest.mark.asyncio
    async def test_fail_start_date(self, validator, mock_agent):
        """Should FAIL_START_DATE when start_date mismatches."""
        mock_agent.process_query.return_value = {
            "success": True,
            "start_date": "2024-07-07",  # Wrong
            "end_date": "2024-07-14",
            "calendar_days": 7,
        }
        query = make_query()
        report = await validator.validate(query)
        assert report.result == ValidationResult.FAIL_START_DATE
        assert "start_date" in report.mismatches

    @pytest.mark.asyncio
    async def test_fail_end_date(self, validator, mock_agent):
        """Should FAIL_END_DATE when end_date mismatches."""
        mock_agent.process_query.return_value = {
            "success": True,
            "start_date": "2024-07-08",
            "end_date": "2024-07-15",  # Wrong
            "calendar_days": 7,
        }
        query = make_query()
        report = await validator.validate(query)
        assert report.result == ValidationResult.FAIL_END_DATE

    @pytest.mark.asyncio
    async def test_fail_calendar_days(self, validator, mock_agent):
        """Should FAIL_CALENDAR_DAYS when day count mismatches."""
        mock_agent.process_query.return_value = {
            "success": True,
            "start_date": "2024-07-08",
            "end_date": "2024-07-14",
            "calendar_days": 8,  # Wrong
        }
        query = make_query()
        report = await validator.validate(query)
        assert report.result == ValidationResult.FAIL_CALENDAR_DAYS

    @pytest.mark.asyncio
    async def test_fail_success_flag(self, validator, mock_agent):
        """Should FAIL_SUCCESS_FLAG when success differs."""
        mock_agent.process_query.return_value = {
            "success": False,
            "error": "Something went wrong",
        }
        query = make_query(expected_success=True)
        report = await validator.validate(query)
        assert report.result == ValidationResult.FAIL_SUCCESS_FLAG

    @pytest.mark.asyncio
    async def test_fail_exception(self, validator, mock_agent):
        """Should FAIL_EXCEPTION when agent throws."""
        mock_agent.process_query.side_effect = RuntimeError("boom")
        query = make_query()
        report = await validator.validate(query)
        assert report.result == ValidationResult.FAIL_EXCEPTION
        assert "exception" in report.mismatches
        assert report.error_traceback is not None

    @pytest.mark.asyncio
    async def test_event_query_pass(self, validator, mock_agent):
        """Event queries should pass when intent_type=event_lookup."""
        mock_agent.process_query.return_value = {
            "success": True,
            "intent_type": "event_lookup",
        }
        query = make_query(
            expected_intent_type="event_lookup",
            expected_success=True,
            expected_start_date=None,
            expected_end_date=None,
            expected_calendar_days=None,
            category=QueryCategory.EVENT_QUERY,
        )
        report = await validator.validate(query)
        assert report.result == ValidationResult.PASS

    @pytest.mark.asyncio
    async def test_event_query_fail(self, validator, mock_agent):
        """Event queries should fail when intent_type is wrong."""
        mock_agent.process_query.return_value = {
            "success": True,
            "start_date": "2024-07-01",
            "end_date": "2024-07-15",
            "computation_trace": {"intent_type": "resolve_period"},
        }
        query = make_query(
            expected_intent_type="event_lookup",
            expected_success=True,
            expected_start_date=None,
            expected_end_date=None,
            expected_calendar_days=None,
            category=QueryCategory.EVENT_QUERY,
        )
        report = await validator.validate(query)
        assert report.result == ValidationResult.FAIL_INTENT_TYPE

    @pytest.mark.asyncio
    async def test_comparison_query_pass(self, validator, mock_agent):
        """Comparison queries pass when intent_type=comparison."""
        mock_agent.process_query.return_value = {
            "success": True,
            "intent_type": "comparison",
        }
        query = make_query(
            expected_intent_type="comparison",
            expected_start_date=None,
            expected_end_date=None,
            expected_calendar_days=None,
            category=QueryCategory.COMPARISON,
        )
        report = await validator.validate(query)
        assert report.result == ValidationResult.PASS

    @pytest.mark.asyncio
    async def test_invalid_query_pass(self, validator, mock_agent):
        """Invalid queries should pass when success=False."""
        mock_agent.process_query.return_value = {
            "success": False,
            "error": "Unrecognized query",
        }
        query = make_query(
            expected_success=False,
            expected_start_date=None,
            expected_end_date=None,
            expected_calendar_days=None,
            category=QueryCategory.INVALID_QUERY,
        )
        report = await validator.validate(query)
        assert report.result == ValidationResult.PASS
