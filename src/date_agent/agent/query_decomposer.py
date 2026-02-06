"""Query decomposer - breaks down complex queries into tool calls."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from date_agent.agent.semantic_parser import ParsedIntent


@dataclass
class ToolCallSpec:
    """Specification for a single tool call."""

    tool_name: str
    parameters: Dict[str, Any]
    step_id: str
    depends_on: List[str] = field(default_factory=list)
    can_parallelize: bool = False
    description: str = ""


@dataclass
class ExecutionPlan:
    """Complete execution plan for a query."""

    steps: List[ToolCallSpec]
    is_compositional: bool = False
    iteration_count: Optional[int] = None
    description: str = ""


class QueryDecomposer:
    """Decomposes parsed intents into executable tool call plans.

    Handles the five complexity layers:
    1. Semantic: Period resolution
    2. Calendar: Holiday/weekend handling
    3. Domain: Business day calculations
    4. Boundaries: Inclusive/exclusive handling
    5. Compositional: Iteration over ranges
    """

    def decompose(
        self,
        intent: ParsedIntent,
        reference_info: Dict[str, Any],
    ) -> ExecutionPlan:
        """Decompose an intent into an execution plan.

        Args:
            intent: Parsed intent from semantic parser.
            reference_info: Current date info from get_current_date_info.

        Returns:
            ExecutionPlan with ordered tool calls.
        """
        steps: List[ToolCallSpec] = []

        # Always start with establishing the reference (already done, but record it)
        # This step is implicit - reference_info is the output

        # Handle compositional queries specially
        if intent.is_compositional:
            return self._plan_compositional(intent, reference_info)

        # Step 1: Resolve period (if we have one)
        if intent.period:
            # For named_quarter with extracted values, use the original query
            # which contains the explicit year (e.g., "Q3 2024")
            period_to_resolve = intent.period
            if intent.period == "named_quarter" and intent.extracted_values.get("year"):
                # Use the raw period text which contains the year
                period_to_resolve = intent.period_raw or intent.period

            steps.append(
                ToolCallSpec(
                    tool_name="resolve_period",
                    parameters={
                        "period": period_to_resolve,
                        "calendar_system": intent.calendar_system or "GREGORIAN",
                        "locale": intent.locale,
                    },
                    step_id="resolve_period",
                    description=f"Resolve period: {period_to_resolve}",
                )
            )

        # Step 2: Get holidays (if needed)
        if intent.exclude_holidays or intent.business_days_only:
            calendar = intent.calendar_system or "GREGORIAN"

            # If we have a period, get holidays for that range
            if intent.period:
                steps.append(
                    ToolCallSpec(
                        tool_name="get_holiday_calendar",
                        parameters={
                            "calendar_system": calendar,
                            # Dates will be filled from resolve_period result
                            "start_date": "${resolve_period.start_date}",
                            "end_date": "${resolve_period.end_date}",
                            "locale": intent.locale,
                        },
                        step_id="get_holidays",
                        depends_on=["resolve_period"],
                        description=f"Get {calendar} holidays",
                    )
                )

        # Step 3: Date computation (if needed)
        if intent.operation and intent.operation_value:
            base_date = "${resolve_period.end_date}" if intent.period else reference_info.get("date")

            steps.append(
                ToolCallSpec(
                    tool_name="compute_date_range",
                    parameters={
                        "base_date": base_date,
                        "operation": intent.operation,
                        "value": intent.operation_value,
                        "calendar_system": intent.calendar_system or "GREGORIAN",
                    },
                    step_id="compute_date",
                    depends_on=["resolve_period"] if intent.period else [],
                    description=f"{intent.operation}({intent.operation_value})",
                )
            )

        return ExecutionPlan(
            steps=steps,
            is_compositional=False,
            description=self._describe_plan(intent),
        )

    def _plan_compositional(
        self,
        intent: ParsedIntent,
        reference_info: Dict[str, Any],
    ) -> ExecutionPlan:
        """Plan a compositional query (requires iteration).

        Example: "3 business days before each month-end for the last 6 months"

        Args:
            intent: Parsed intent.
            reference_info: Current date info.

        Returns:
            ExecutionPlan with iteration support.
        """
        steps: List[ToolCallSpec] = []

        # Step 1: Resolve the iteration range
        iteration_range = intent.iteration_range or "last_6_months"
        steps.append(
            ToolCallSpec(
                tool_name="resolve_period",
                parameters={
                    "period": iteration_range,
                    "calendar_system": intent.calendar_system or "GREGORIAN",
                    "locale": intent.locale,
                },
                step_id="resolve_range",
                description=f"Resolve iteration range: {iteration_range}",
            )
        )

        # Step 2: The iteration itself
        # For each month in range, compute the target
        iteration_target = intent.iteration_target or "month_end"
        operation = intent.operation or "subtract_business_days"
        value = intent.operation_value or 3

        steps.append(
            ToolCallSpec(
                tool_name="compute_date_range",
                parameters={
                    "base_date": "${iterate:month_start}",  # Will iterate
                    "operation": iteration_target,
                    "calendar_system": intent.calendar_system or "GREGORIAN",
                    "then_operations": [
                        {
                            "operation": operation,
                            "value": value,
                            "calendar_system": intent.calendar_system or "GREGORIAN",
                        }
                    ],
                },
                step_id="compute_each",
                depends_on=["resolve_range"],
                description=f"For each month: {operation}({value}) from {iteration_target}",
            )
        )

        # Estimate iteration count
        iteration_count = 6  # Default
        if "last_" in iteration_range:
            # Try to extract number
            import re

            match = re.search(r"last_(\d+)", iteration_range)
            if match:
                iteration_count = int(match.group(1))

        return ExecutionPlan(
            steps=steps,
            is_compositional=True,
            iteration_count=iteration_count,
            description=self._describe_plan(intent),
        )

    def _describe_plan(self, intent: ParsedIntent) -> str:
        """Generate a human-readable description of the plan.

        Args:
            intent: The parsed intent.

        Returns:
            Description string.
        """
        parts = []

        if intent.period:
            parts.append(f"Resolve '{intent.period}'")

        if intent.exclude_holidays:
            parts.append("exclude holidays")

        if intent.business_days_only:
            parts.append("business days only")

        if intent.operation and intent.operation_value:
            parts.append(f"{intent.operation}({intent.operation_value})")

        if intent.is_compositional:
            parts.append(f"iterate over {intent.iteration_range or 'range'}")

        if intent.calendar_system:
            parts.append(f"using {intent.calendar_system}")

        return ", ".join(parts) if parts else "Process date query"
