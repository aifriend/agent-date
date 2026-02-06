"""Main Date Reasoning Agent - orchestrates tools for date queries.

Core Principle: The agent handles SEMANTIC UNDERSTANDING only.
All date calculations are performed by deterministic TOOLS.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from date_agent.core.config import DateAgentConfig, ToolExecutionContext
from date_agent.core.audit import AuditManager
from date_agent.core.exceptions import DateAgentError, ToolExecutionError
from date_agent.agent.semantic_parser import SemanticParser, ParsedIntent
from date_agent.agent.query_decomposer import QueryDecomposer, ExecutionPlan, ToolCallSpec
from date_agent.tools import (
    BaseDateTool,
    GetCurrentDateInfoTool,
    ResolvePeriodTool,
    GetHolidayCalendarTool,
    ComputeDateRangeTool,
)


class DateReasoningAgent:
    """High-Precision Date Reasoning Agent for Financial Operations.

    Design Philosophy: The agent handles SEMANTIC UNDERSTANDING and QUERY DECOMPOSITION.
    All actual date calculations are performed by TOOLS - the agent never computes dates itself.

    Usage:
        config = DateAgentConfig()
        agent = DateReasoningAgent(config)

        result = await agent.process_query("Q3 2024 excluding Peru banking holidays")
    """

    def __init__(self, config: Optional[DateAgentConfig] = None):
        """Initialize the Date Reasoning Agent.

        Args:
            config: Agent configuration. If None, uses defaults with env vars.
        """
        self.config = config or DateAgentConfig()
        self.logger = logging.getLogger(f"DateAgent.{self.config.agent_id}")

        # Initialize tools (Source of Truth)
        self.tools: Dict[str, BaseDateTool] = {}
        self._register_tools()

        # Initialize components
        self.semantic_parser = SemanticParser(
            config=self.config,
            locale=self.config.default_locale,
        )
        self.query_decomposer = QueryDecomposer()
        self.audit_manager = AuditManager(
            enabled=self.config.enable_audit_trail,
            log_path=self.config.audit_log_path,
            logger=self.logger,
        )

        self.logger.info(f"DateReasoningAgent initialized: {self.config.agent_id}")

    def _register_tools(self) -> None:
        """Register all date calculation tools."""
        self.tools = {
            "get_current_date_info": GetCurrentDateInfoTool(),
            "resolve_period": ResolvePeriodTool(),
            "get_holiday_calendar": GetHolidayCalendarTool(),
            "compute_date_range": ComputeDateRangeTool(),
        }
        self.logger.debug(f"Registered {len(self.tools)} tools")

    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a natural language date query.

        The agent:
        1. Establishes the reference point (get_current_date_info)
        2. Parses the semantic intent
        3. Decomposes into tool calls
        4. Orchestrates tool execution
        5. Synthesizes the response

        The agent NEVER computes dates itself - all calculations via tools.

        Args:
            query: Natural language date query.
            context: Optional context (e.g., override reference date).

        Returns:
            Dict with query results and audit information.
        """
        execution_id = str(uuid.uuid4())
        session_id = self.audit_manager.create_session(query)

        self.logger.info(f"Processing query: {query[:100]}...")

        try:
            # Step 1: Establish the reference point (ALWAYS FIRST)
            reference_result = await self._establish_reference_point(
                execution_id, context
            )
            self.logger.debug(f"Reference: {reference_result.get('date')}")

            # Step 2: Parse semantic intent
            intent = await self.semantic_parser.parse(query)
            self.logger.debug(f"Intent: {intent.intent_type}, period={intent.period}")

            # Step 3: Decompose into tool call plan
            plan = self.query_decomposer.decompose(intent, reference_result)
            self.logger.debug(f"Plan: {len(plan.steps)} steps")

            # Step 4: Execute tools in order
            results = await self._execute_plan(plan, reference_result, session_id)

            # Step 5: Synthesize response
            response = self._synthesize_response(
                query, intent, plan, results, reference_result, execution_id
            )

            # Finalize audit
            await self.audit_manager.finalize_session(session_id, response)

            return response

        except DateAgentError as e:
            self.logger.error(f"Agent error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "audit_id": session_id,
            }
        except Exception as e:
            self.logger.exception(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "UnexpectedError",
                "audit_id": session_id,
            }

    async def _establish_reference_point(
        self,
        execution_id: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Establish the immutable reference point.

        ALWAYS called first to anchor all calculations.

        Args:
            execution_id: Execution identifier.
            context: Optional context with override settings.

        Returns:
            Reference date information from get_current_date_info.
        """
        # Create execution context
        exec_context = ToolExecutionContext.create_default(
            execution_id=execution_id,
            config=self.config,
        )

        # Override timezone if provided in context
        timezone_override = None
        if context and "timezone" in context:
            timezone_override = context["timezone"]

        # Execute get_current_date_info
        tool = self.tools["get_current_date_info"]
        result = await tool.execute(
            exec_context,
            timezone=timezone_override or self.config.default_timezone,
            locale=self.config.default_locale,
            lookback_months=self.config.max_lookback_months,
        )

        if not result.success:
            raise ToolExecutionError(
                tool_name="get_current_date_info",
                original_error=Exception(result.error or "Unknown error"),
            )

        return result.output.model_dump()

    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        reference_result: Dict[str, Any],
        session_id: str,
    ) -> Dict[str, Any]:
        """Execute a tool call plan.

        Args:
            plan: The execution plan.
            reference_result: Reference date information.
            session_id: Audit session ID.

        Returns:
            Dict mapping step_id to results.
        """
        results: Dict[str, Any] = {"reference": reference_result}
        exec_context = ToolExecutionContext.create_default(
            execution_id=session_id,
            config=self.config,
        )

        for step in plan.steps:
            # Resolve parameter references
            params = self._resolve_parameters(step.parameters, results)

            # Get the tool
            tool = self.tools.get(step.tool_name)
            if not tool:
                self.logger.warning(f"Unknown tool: {step.tool_name}")
                continue

            # Execute the tool
            self.logger.debug(f"Executing: {step.tool_name}")
            result = await tool.execute(exec_context, **params)

            if not result.success:
                self.logger.error(f"Tool failed: {step.tool_name} - {result.error}")
                results[step.step_id] = {"error": result.error}
            else:
                results[step.step_id] = result.output.model_dump()

            # Log to audit trail
            await self.audit_manager.log_tool_execution(
                session_id=session_id,
                execution_id=result.execution_id,
                tool_name=step.tool_name,
                input_params=params,
                output_result=results[step.step_id],
                reference_date=exec_context.reference_date,
                calendar_system=exec_context.calendar_system,
                timezone=exec_context.timezone,
                computation_steps=result.computation_steps,
                duration_ms=result.duration_ms,
                success=result.success,
                error_message=result.error,
            )

        return results

    def _resolve_parameters(
        self,
        params: Dict[str, Any],
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve parameter references from previous step results.

        Handles patterns like "${resolve_period.start_date}".

        Args:
            params: Parameters with potential references.
            results: Results from previous steps.

        Returns:
            Resolved parameters.
        """
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${"):
                # Extract reference: ${step_id.field}
                match = re.match(r"\$\{([^.]+)\.([^}]+)\}", value)
                if match:
                    step_id, field = match.groups()
                    step_result = results.get(step_id, {})
                    resolved[key] = step_result.get(field, value)
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self._resolve_parameters(value, results)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_parameters(v, results) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _synthesize_response(
        self,
        query: str,
        intent: ParsedIntent,
        plan: ExecutionPlan,
        results: Dict[str, Any],
        reference: Dict[str, Any],
        execution_id: str,
    ) -> Dict[str, Any]:
        """Synthesize the final response from tool results.

        Args:
            query: Original query.
            intent: Parsed intent.
            plan: Execution plan.
            results: Tool execution results.
            reference: Reference date information.
            execution_id: Execution identifier.

        Returns:
            Final response dict.
        """
        response: Dict[str, Any] = {
            "success": True,
            "query": query,
            "audit_id": execution_id,
            "reference_date": reference.get("date"),
            "timezone": reference.get("timezone"),
        }

        # Extract main result based on intent type
        if "resolve_period" in results:
            period_result = results["resolve_period"]
            if not isinstance(period_result, dict) or "error" in period_result:
                response["success"] = False
                response["error"] = period_result.get("error", "Period resolution failed")
            else:
                response["start_date"] = period_result.get("start_date")
                response["end_date"] = period_result.get("end_date")
                response["calendar_days"] = period_result.get("calendar_days")
                response["period_type"] = period_result.get("period_type")
                response["description"] = period_result.get("description_localized")

        if "get_holidays" in results:
            holidays_result = results["get_holidays"]
            if isinstance(holidays_result, dict) and "error" not in holidays_result:
                response["holidays"] = holidays_result.get("holidays", [])
                response["business_days"] = holidays_result.get("total_business_days")
                response["excluded_holidays"] = [
                    h["date"] for h in holidays_result.get("holidays", [])
                ]

        if "compute_date" in results:
            compute_result = results["compute_date"]
            if isinstance(compute_result, dict) and "error" not in compute_result:
                response["result_date"] = compute_result.get("result_date")
                response["operations_applied"] = compute_result.get("operations_applied")
                response["holidays_excluded"] = compute_result.get("holidays_excluded")
                response["weekends_excluded"] = compute_result.get("weekends_excluded")

        # Add computation trace for transparency
        response["computation_trace"] = {
            "intent_type": intent.intent_type,
            "confidence": intent.confidence,
            "plan_steps": len(plan.steps),
            "is_compositional": plan.is_compositional,
        }

        return response

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools and their schemas.

        Returns:
            List of tool definitions.
        """
        return [tool.get_tool_definition() for tool in self.tools.values()]
