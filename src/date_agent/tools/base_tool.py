"""Base class for date calculation tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, TypeVar, Optional
import time
import uuid

from pydantic import BaseModel

from date_agent.core.config import ToolExecutionContext
from date_agent.core.exceptions import ToolExecutionError

# Type variables for input/output schemas
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass
class ToolResult(Generic[OutputT]):
    """Result wrapper for tool execution.

    Wraps the tool output with execution metadata for audit trail.

    Attributes:
        success: Whether the execution succeeded.
        output: The tool output (if successful).
        error: Error message (if failed).
        execution_id: Unique identifier for this execution.
        duration_ms: Execution duration in milliseconds.
        computation_steps: Step-by-step trace of the calculation.
    """

    success: bool
    output: Optional[OutputT] = None
    error: Optional[str] = None
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    duration_ms: float = 0.0
    computation_steps: list[str] = field(default_factory=list)

    @classmethod
    def ok(
        cls,
        output: OutputT,
        execution_id: str,
        duration_ms: float,
        computation_steps: Optional[list[str]] = None,
    ) -> "ToolResult[OutputT]":
        """Create a successful result.

        Args:
            output: The tool output.
            execution_id: The execution identifier.
            duration_ms: Execution duration.
            computation_steps: Optional trace of steps.

        Returns:
            A successful ToolResult.
        """
        return cls(
            success=True,
            output=output,
            execution_id=execution_id,
            duration_ms=duration_ms,
            computation_steps=computation_steps or [],
        )

    @classmethod
    def fail(
        cls,
        error: str,
        execution_id: str,
        duration_ms: float = 0.0,
        computation_steps: Optional[list[str]] = None,
    ) -> "ToolResult[OutputT]":
        """Create a failed result.

        Args:
            error: Error message.
            execution_id: The execution identifier.
            duration_ms: Execution duration.
            computation_steps: Optional trace of steps before failure.

        Returns:
            A failed ToolResult.
        """
        return cls(
            success=False,
            error=error,
            execution_id=execution_id,
            duration_ms=duration_ms,
            computation_steps=computation_steps or [],
        )


class BaseDateTool(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all date calculation tools.

    All date tools must inherit from this class and implement:
    - name: Tool identifier
    - description: Human-readable description for semantic understanding
    - input_schema: Pydantic model for input validation
    - output_schema: Pydantic model for output
    - _execute: The actual computation logic

    The execute() method wraps _execute() with timing and error handling.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier (e.g., 'get_current_date_info')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for semantic understanding.

        This description helps the agent understand when to use this tool.
        """
        ...

    @property
    @abstractmethod
    def input_schema(self) -> type[InputT]:
        """Pydantic model class for input validation."""
        ...

    @property
    @abstractmethod
    def output_schema(self) -> type[OutputT]:
        """Pydantic model class for output."""
        ...

    @abstractmethod
    async def _execute(
        self,
        context: ToolExecutionContext,
        input_data: InputT,
    ) -> tuple[OutputT, list[str]]:
        """Execute the tool with given input.

        This is the main computation method that subclasses must implement.
        The execute() wrapper handles timing, error handling, and audit.

        Args:
            context: The execution context with reference date, timezone, etc.
            input_data: Validated input parameters.

        Returns:
            A tuple of (output, computation_steps) where:
            - output: The tool output (Pydantic model)
            - computation_steps: List of steps taken for audit trail

        Raises:
            Any exception will be caught by execute() and wrapped in ToolResult.
        """
        ...

    async def execute(
        self,
        context: ToolExecutionContext,
        **kwargs: Any,
    ) -> ToolResult[OutputT]:
        """Execute the tool with timing and error handling.

        This is the public interface that should be called by the agent.
        It validates input, times execution, and catches errors.

        Args:
            context: The execution context.
            **kwargs: Tool parameters matching the input schema.

        Returns:
            ToolResult wrapping the output or error.
        """
        execution_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        computation_steps: list[str] = []

        try:
            # Validate input
            computation_steps.append(f"Tool: {self.name}")
            computation_steps.append(f"Input: {kwargs}")

            input_data = self.input_schema(**kwargs)
            computation_steps.append("Input validated")

            # Execute the tool
            output, steps = await self._execute(context, input_data)
            computation_steps.extend(steps)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult.ok(
                output=output,
                execution_id=execution_id,
                duration_ms=duration_ms,
                computation_steps=computation_steps,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            computation_steps.append(f"Error: {type(e).__name__}: {e}")

            return ToolResult.fail(
                error=str(e),
                execution_id=execution_id,
                duration_ms=duration_ms,
                computation_steps=computation_steps,
            )

    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool parameters.

        This can be used for tool definition in LLM function calling.

        Returns:
            JSON schema dict for the input parameters.
        """
        return self.input_schema.model_json_schema()

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return a complete tool definition for LLM function calling.

        Returns a dict compatible with OpenAI/Azure function calling format.

        Returns:
            Tool definition dict with name, description, and parameters.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_schema(),
            },
        }
