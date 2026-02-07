"""Validator - compares date agent output against ground truth."""

import logging
import time
import traceback
from typing import Any, Dict

from date_agent.agent.date_agent import DateReasoningAgent
from date_agent.feedback.models import (
    ChallengerQuery,
    ValidationReport,
    ValidationResult,
)

logger = logging.getLogger("Validator")


class Validator:
    """Validates date agent output against ground truth.

    Checks: start_date, end_date, calendar_days, success flag, intent_type.
    """

    def __init__(self, agent: DateReasoningAgent):
        self.agent = agent

    async def validate(self, query: ChallengerQuery) -> ValidationReport:
        """Run one query through the agent and validate."""
        start_time = time.perf_counter()

        context = {
            "timezone": "America/Lima",
            "reference_date": query.reference_date.isoformat(),
        }

        try:
            result = await self.agent.process_query(
                query.query_text, context=context
            )
        except Exception as e:
            return ValidationReport(
                query=query,
                agent_output={"error": str(e)},
                result=ValidationResult.FAIL_EXCEPTION,
                mismatches={
                    "exception": {"expected": "no_exception", "actual": str(e)}
                },
                error_traceback=traceback.format_exc(),
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

        duration = (time.perf_counter() - start_time) * 1000
        mismatches: Dict[str, Dict[str, Any]] = {}

        # --- Check success flag ---
        actual_success = result.get("success", False)
        if actual_success != query.expected_success:
            mismatches["success"] = {
                "expected": query.expected_success,
                "actual": actual_success,
            }

        # --- For event queries, check intent_type ---
        if query.expected_intent_type == "event_lookup":
            actual_intent = result.get("intent_type") or result.get(
                "computation_trace", {}
            ).get("intent_type")
            if actual_intent != "event_lookup":
                mismatches["intent_type"] = {
                    "expected": "event_lookup",
                    "actual": actual_intent,
                }
            # Event queries: only validate intent, not dates
            return self._build_report(query, result, mismatches, duration)

        # --- For comparison queries, check intent_type ---
        if query.expected_intent_type == "comparison":
            actual_intent = result.get("intent_type") or result.get(
                "computation_trace", {}
            ).get("intent_type")
            if actual_intent != "comparison":
                mismatches["intent_type"] = {
                    "expected": "comparison",
                    "actual": actual_intent,
                }
            return self._build_report(query, result, mismatches, duration)

        # --- For invalid queries, only check success=False ---
        if not query.expected_success:
            return self._build_report(query, result, mismatches, duration)

        # --- For date period queries, check dates ---
        if query.expected_start_date:
            fields = [
                ("start_date", query.expected_start_date),
                ("end_date", query.expected_end_date),
                ("calendar_days", query.expected_calendar_days),
            ]
            for field_name, expected in fields:
                if expected is None:
                    continue
                actual = result.get(field_name)
                if str(actual) != str(expected):
                    mismatches[field_name] = {
                        "expected": expected,
                        "actual": actual,
                    }

        return self._build_report(query, result, mismatches, duration)

    def _build_report(
        self,
        query: ChallengerQuery,
        result: Dict[str, Any],
        mismatches: Dict[str, Dict[str, Any]],
        duration_ms: float,
    ) -> ValidationReport:
        """Determine overall result and build report."""
        if not mismatches:
            overall = ValidationResult.PASS
        elif "exception" in mismatches:
            overall = ValidationResult.FAIL_EXCEPTION
        elif "success" in mismatches:
            overall = ValidationResult.FAIL_SUCCESS_FLAG
        elif "intent_type" in mismatches:
            overall = ValidationResult.FAIL_INTENT_TYPE
        elif "start_date" in mismatches:
            overall = ValidationResult.FAIL_START_DATE
        elif "end_date" in mismatches:
            overall = ValidationResult.FAIL_END_DATE
        elif "calendar_days" in mismatches:
            overall = ValidationResult.FAIL_CALENDAR_DAYS
        else:
            overall = ValidationResult.FAIL_PERIOD_TYPE

        return ValidationReport(
            query=query,
            agent_output=result,
            result=overall,
            mismatches=mismatches,
            duration_ms=duration_ms,
        )
