"""Configuration classes for the Date Reasoning Agent."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import os


@dataclass
class DateAgentConfig:
    """Configuration for the Date Reasoning Agent.

    Attributes:
        agent_id: Unique identifier for this agent instance.
        azure_openai_endpoint: Azure OpenAI endpoint URL.
        azure_openai_api_key: Azure OpenAI API key.
        azure_openai_api_version: Azure OpenAI API version.
        azure_openai_deployment: Azure OpenAI deployment name (model).
        default_timezone: Default timezone for date calculations (IANA format).
        default_calendar_system: Default calendar system (GREGORIAN, PERU_BANKING).
        default_locale: Default locale for parsing (es, en).
        max_lookback_months: Maximum months allowed for historical queries.
        enable_audit_trail: Whether to log all operations for compliance.
        audit_log_path: Path to store audit logs (if enabled).
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """

    agent_id: str = "date-agent-001"

    # Azure OpenAI Configuration
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment: str = "gpt-4"

    # Default settings (Peru-focused from BIO project)
    default_timezone: str = "America/Lima"
    default_calendar_system: str = "GREGORIAN"
    default_locale: str = "es"

    # Financial constraints (from BIO)
    max_lookback_months: int = 6

    # Audit settings
    enable_audit_trail: bool = True
    audit_log_path: Optional[str] = None

    # Logging
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        """Load configuration from environment variables if not provided."""
        if self.azure_openai_endpoint is None:
            self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if self.azure_openai_api_key is None:
            self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if os.getenv("AZURE_OPENAI_API_VERSION"):
            self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        if os.getenv("AZURE_OPENAI_DEPLOYMENT"):
            self.azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if os.getenv("DATE_AGENT_DEFAULT_TIMEZONE"):
            self.default_timezone = os.getenv("DATE_AGENT_DEFAULT_TIMEZONE")
        if os.getenv("DATE_AGENT_DEFAULT_LOCALE"):
            self.default_locale = os.getenv("DATE_AGENT_DEFAULT_LOCALE")
        if os.getenv("DATE_AGENT_MAX_LOOKBACK_MONTHS"):
            self.max_lookback_months = int(os.getenv("DATE_AGENT_MAX_LOOKBACK_MONTHS"))
        if os.getenv("DATE_AGENT_ENABLE_AUDIT"):
            self.enable_audit_trail = os.getenv("DATE_AGENT_ENABLE_AUDIT", "").lower() == "true"
        if os.getenv("LOG_LEVEL"):
            self.log_level = os.getenv("LOG_LEVEL")


@dataclass
class ToolExecutionContext:
    """Immutable context for tool execution - ensures traceability.

    This context is passed to every tool execution and establishes:
    - The reference point for all calculations
    - The timezone and calendar system to use
    - Correlation IDs for audit trail

    Attributes:
        execution_id: Unique ID for this execution.
        reference_date: The immutable anchor point for all calculations.
        timezone: Timezone for date calculations (IANA format).
        calendar_system: Calendar system to use (GREGORIAN, PERU_BANKING).
        locale: Locale for date formatting and parsing.
        session_id: Optional session identifier.
        correlation_id: Optional correlation ID for tracing.
        audit_enabled: Whether to record this execution in audit trail.
    """

    execution_id: str
    reference_date: datetime
    timezone: str
    calendar_system: str
    locale: str = "es"
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    audit_enabled: bool = True

    def __post_init__(self) -> None:
        """Ensure reference_date is timezone-aware."""
        if self.reference_date.tzinfo is None:
            raise ValueError("reference_date must be timezone-aware")

    @classmethod
    def create_default(
        cls,
        execution_id: str,
        config: DateAgentConfig,
        reference_date: Optional[datetime] = None,
    ) -> "ToolExecutionContext":
        """Create a context with default configuration.

        Args:
            execution_id: Unique ID for this execution.
            config: Agent configuration.
            reference_date: Optional override for reference date.
                           If not provided, uses current UTC time.

        Returns:
            A new ToolExecutionContext with default settings.
        """
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)

        return cls(
            execution_id=execution_id,
            reference_date=reference_date,
            timezone=config.default_timezone,
            calendar_system=config.default_calendar_system,
            locale=config.default_locale,
            audit_enabled=config.enable_audit_trail,
        )
