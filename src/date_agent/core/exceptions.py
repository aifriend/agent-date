"""Custom exceptions for the Date Reasoning Agent."""

from typing import Any, Optional


class DateAgentError(Exception):
    """Base exception for all date agent errors.

    All custom exceptions in this package inherit from this class,
    making it easy to catch any agent-related error.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidPeriodError(DateAgentError):
    """Raised when a period expression cannot be resolved.

    Examples of invalid periods:
    - Unrecognized format: "next fortnight"
    - Out of range: "Q5 2024" (no Q5)
    - Ambiguous: "last week" without context
    """

    def __init__(
        self,
        period: str,
        message: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            period: The period expression that failed to parse.
            message: Optional custom error message.
            suggestions: Optional list of valid period expressions.
        """
        msg = message or f"Cannot resolve period expression: '{period}'"
        super().__init__(msg, {"period": period, "suggestions": suggestions or []})
        self.period = period
        self.suggestions = suggestions or []


class CalendarNotFoundError(DateAgentError):
    """Raised when a requested calendar system is not available.

    This typically means:
    - The calendar system is not implemented
    - Holiday data is missing for the requested year
    """

    def __init__(
        self,
        calendar_system: str,
        year: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            calendar_system: The calendar system that was requested.
            year: Optional year for which data is missing.
            message: Optional custom error message.
        """
        if year:
            msg = message or f"Calendar '{calendar_system}' not available for year {year}"
        else:
            msg = message or f"Calendar system '{calendar_system}' not found"
        super().__init__(msg, {"calendar_system": calendar_system, "year": year})
        self.calendar_system = calendar_system
        self.year = year


class DateOutOfRangeError(DateAgentError):
    """Raised when a date is outside the allowed range.

    Financial systems often restrict historical queries (e.g., 6-month lookback).
    This exception is raised when a query exceeds those limits.
    """

    def __init__(
        self,
        date: str,
        min_date: Optional[str] = None,
        max_date: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            date: The date that is out of range.
            min_date: The minimum allowed date (if applicable).
            max_date: The maximum allowed date (if applicable).
            message: Optional custom error message.
        """
        if min_date and max_date:
            msg = message or f"Date '{date}' is outside allowed range [{min_date}, {max_date}]"
        elif min_date:
            msg = message or f"Date '{date}' is before the minimum allowed date {min_date}"
        elif max_date:
            msg = message or f"Date '{date}' is after the maximum allowed date {max_date}"
        else:
            msg = message or f"Date '{date}' is outside the allowed range"

        super().__init__(
            msg,
            {"date": date, "min_date": min_date, "max_date": max_date},
        )
        self.date = date
        self.min_date = min_date
        self.max_date = max_date


class AmbiguousQueryError(DateAgentError):
    """Raised when a query has multiple possible interpretations.

    When this is raised, the agent should ask the user for clarification
    rather than guessing.

    Example: "next Monday" could mean:
    - The coming Monday (if today is Tuesday)
    - The Monday after next (if today is Monday)
    """

    def __init__(
        self,
        query: str,
        interpretations: list[str],
        message: Optional[str] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            query: The ambiguous query.
            interpretations: List of possible interpretations.
            message: Optional custom error message.
        """
        msg = message or f"Ambiguous query: '{query}'. Possible interpretations: {interpretations}"
        super().__init__(
            msg,
            {"query": query, "interpretations": interpretations},
        )
        self.query = query
        self.interpretations = interpretations


class ToolExecutionError(DateAgentError):
    """Raised when a tool fails to execute.

    Wraps the original error with tool context for debugging.
    """

    def __init__(
        self,
        tool_name: str,
        original_error: Exception,
        parameters: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            tool_name: Name of the tool that failed.
            original_error: The original exception that was raised.
            parameters: The parameters that were passed to the tool.
        """
        msg = f"Tool '{tool_name}' failed: {original_error}"
        super().__init__(
            msg,
            {
                "tool_name": tool_name,
                "original_error_type": type(original_error).__name__,
                "original_error_message": str(original_error),
                "parameters": parameters or {},
            },
        )
        self.tool_name = tool_name
        self.original_error = original_error
        self.parameters = parameters or {}


class ConfigurationError(DateAgentError):
    """Raised when the agent is misconfigured.

    Examples:
    - Missing Azure OpenAI credentials
    - Invalid timezone
    - Invalid calendar system
    """

    def __init__(
        self,
        config_key: str,
        message: Optional[str] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            config_key: The configuration key that is invalid or missing.
            message: Optional custom error message.
        """
        msg = message or f"Invalid or missing configuration: '{config_key}'"
        super().__init__(msg, {"config_key": config_key})
        self.config_key = config_key
