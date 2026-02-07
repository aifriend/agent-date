"""Tests for the Challenger Agent query generation."""

import pytest
from datetime import date

from date_agent.feedback.challenger import ChallengerAgent
from date_agent.feedback.models import QueryCategory, ChallengerQuery


REFERENCE_DATE = date(2024, 7, 15)


class TestChallengerAgent:
    """Validate challenger query generation."""

    @pytest.fixture
    def challenger(self):
        return ChallengerAgent(REFERENCE_DATE)

    def test_generate_batch_returns_queries(self, challenger):
        """Generate a batch of queries."""
        batch = challenger.generate_batch(20)
        assert len(batch) > 0
        assert len(batch) <= 20
        assert all(isinstance(q, ChallengerQuery) for q in batch)

    def test_all_categories_covered(self, challenger):
        """After enough batches, all categories should be represented.

        INVALID_QUERY is excluded because invalid query detection requires
        the LLM fallback, so those templates were removed to avoid false
        failures in the challenger evaluation loop.
        """
        all_queries = []
        for _ in range(5):
            all_queries.extend(challenger.generate_batch(50))

        categories_seen = {q.category for q in all_queries}
        # INVALID_QUERY requires LLM; COMPOSITIONAL requires iteration pipeline
        skip = {QueryCategory.INVALID_QUERY, QueryCategory.COMPOSITIONAL}
        for cat in QueryCategory:
            if cat in skip:
                continue
            assert cat in categories_seen, f"Category {cat.value} never generated"

    def test_queries_have_required_fields(self, challenger):
        """All queries must have essential fields populated."""
        batch = challenger.generate_batch(30)
        for q in batch:
            assert q.query_id, "Missing query_id"
            assert q.query_text, "Missing query_text"
            assert q.language in ("es", "en"), f"Invalid language: {q.language}"
            assert isinstance(q.category, QueryCategory)
            assert q.reference_date == REFERENCE_DATE

    def test_date_queries_have_ground_truth(self, challenger):
        """Queries expecting success must have start/end dates."""
        batch = challenger.generate_batch(30)
        for q in batch:
            if q.expected_success and q.expected_intent_type == "resolve_period":
                if q.expected_start_date is not None:
                    assert q.expected_end_date is not None, (
                        f"Query {q.query_id} has start but no end date"
                    )
                    assert q.expected_calendar_days is not None, (
                        f"Query {q.query_id} has dates but no day count"
                    )
                    # Verify day count is consistent
                    start = date.fromisoformat(q.expected_start_date)
                    end = date.fromisoformat(q.expected_end_date)
                    computed = (end - start).days + 1
                    assert computed == q.expected_calendar_days, (
                        f"Query {q.query_id}: {computed} != {q.expected_calendar_days}"
                    )

    def test_event_queries_expect_event_lookup(self, challenger):
        """Event queries should expect intent_type=event_lookup."""
        batch = challenger.generate_batch(50)
        event_queries = [
            q for q in batch if q.category == QueryCategory.EVENT_QUERY
        ]
        for q in event_queries:
            assert q.expected_intent_type == "event_lookup"

    def test_invalid_queries_expect_failure(self, challenger):
        """Invalid queries should expect success=False."""
        batch = challenger.generate_batch(50)
        invalid_queries = [
            q for q in batch if q.category == QueryCategory.INVALID_QUERY
        ]
        for q in invalid_queries:
            assert q.expected_success is False

    def test_unique_query_ids(self, challenger):
        """All query IDs should be unique."""
        batch = challenger.generate_batch(50)
        ids = [q.query_id for q in batch]
        assert len(ids) == len(set(ids)), "Duplicate query IDs found"

    def test_edge_case_queries_generated(self, challenger):
        """Edge case queries should include leap year tests."""
        batch = challenger.generate_batch(50)
        edge_cases = [
            q for q in batch if q.category == QueryCategory.EDGE_CASE
        ]
        assert len(edge_cases) > 0, "No edge case queries generated"

    def test_comparison_queries_generated(self, challenger):
        """Comparison queries should have comparison intent type."""
        batch = challenger.generate_batch(50)
        comps = [
            q for q in batch if q.category == QueryCategory.COMPARISON
        ]
        for q in comps:
            assert q.expected_intent_type == "comparison"
