"""Semantic parser for natural language date queries.

Uses Azure OpenAI for semantic understanding, with pattern-based
fallback for common expressions.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Optional dependency - only needed if using Azure OpenAI
try:
    from openai import AsyncAzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    AsyncAzureOpenAI = None  # type: ignore
    OPENAI_AVAILABLE = False

from date_agent.core.config import DateAgentConfig
from date_agent.localization.spanish import SPANISH_PERIOD_PATTERNS, parse_spanish_period
from date_agent.localization.english import ENGLISH_PERIOD_PATTERNS, parse_english_period


@dataclass
class ParsedIntent:
    """Result of semantic parsing.

    Represents the structured understanding of a date query.
    """

    # Primary intent
    intent_type: str  # "resolve_period", "get_holidays", "compute_date", "mixed"

    # Period information
    period: Optional[str] = None  # e.g., "last_week", "Q3 2024"
    period_raw: Optional[str] = None  # Original text

    # Calendar system
    calendar_system: Optional[str] = None  # e.g., "PERU_BANKING"

    # Holiday/business day related
    exclude_holidays: bool = False
    include_weekends: bool = False
    business_days_only: bool = False

    # Date operations
    operation: Optional[str] = None  # e.g., "subtract_business_days"
    operation_value: Optional[int] = None

    # Compositional query info
    is_compositional: bool = False
    iteration_target: Optional[str] = None  # e.g., "month_end"
    iteration_range: Optional[str] = None  # e.g., "last_6_months"

    # Locale
    locale: str = "es"

    # Confidence (0-1)
    confidence: float = 1.0

    # Raw extraction
    extracted_values: Dict[str, Any] = field(default_factory=dict)


# System prompt for Azure OpenAI semantic parsing
SEMANTIC_PARSER_SYSTEM_PROMPT = """You are a date query parser for a financial date reasoning system.
Your job is to extract structured information from natural language date queries.

IMPORTANT: You only EXTRACT information. You do NOT compute dates.

For each query, extract:
1. intent_type: One of "resolve_period", "get_holidays", "compute_date", "mixed"
2. period: The time period mentioned (e.g., "last_week", "Q3 2024", "ultimo mes")
3. calendar_system: If mentioned (e.g., "PERU_BANKING" for Peru banking holidays)
4. exclude_holidays: true if holidays should be excluded
5. business_days_only: true if only business days are requested
6. operation: Date operation if mentioned (e.g., "subtract_business_days")
7. operation_value: Numeric value for operation (e.g., 3 for "3 days before")
8. is_compositional: true if query requires iteration (e.g., "for each month-end")
9. iteration_target: Target for iteration (e.g., "month_end")
10. iteration_range: Range for iteration (e.g., "last_6_months")

Respond with valid JSON only. Example:
{
  "intent_type": "resolve_period",
  "period": "last_quarter",
  "calendar_system": "PERU_BANKING",
  "exclude_holidays": true,
  "business_days_only": false,
  "operation": null,
  "operation_value": null,
  "is_compositional": false,
  "iteration_target": null,
  "iteration_range": null,
  "confidence": 0.95
}"""


class SemanticParser:
    """Parses natural language date queries into structured intents.

    Uses a hybrid approach:
    1. Pattern matching for common expressions (fast, no LLM call)
    2. Azure OpenAI for complex queries (semantic understanding)
    """

    def __init__(
        self,
        config: Optional[DateAgentConfig] = None,
        locale: str = "es",
    ):
        """Initialize the semantic parser.

        Args:
            config: Agent configuration (for Azure OpenAI).
            locale: Default locale for parsing.
        """
        self.config = config
        self.locale = locale
        self.logger = logging.getLogger("SemanticParser")

        # Azure OpenAI client (initialized lazily)
        self._openai_client: Optional[AsyncAzureOpenAI] = None

    @property
    def openai_client(self):
        """Get or initialize the Azure OpenAI client."""
        if not OPENAI_AVAILABLE:
            return None
        if self._openai_client is None and self.config:
            if self.config.azure_openai_endpoint and self.config.azure_openai_api_key:
                self._openai_client = AsyncAzureOpenAI(
                    azure_endpoint=self.config.azure_openai_endpoint,
                    api_key=self.config.azure_openai_api_key,
                    api_version=self.config.azure_openai_api_version,
                )
        return self._openai_client

    async def parse(self, query: str) -> ParsedIntent:
        """Parse a natural language date query.

        Args:
            query: The user's query (e.g., "show me last week's transactions").

        Returns:
            ParsedIntent with extracted information.
        """
        # First, try pattern-based parsing (fast path)
        intent = self._try_pattern_parse(query)
        if intent and intent.confidence >= 0.8:
            self.logger.debug(f"Pattern match succeeded: {intent.intent_type}")
            return intent

        # If pattern matching failed or low confidence, try LLM
        if self.openai_client:
            try:
                llm_intent = await self._parse_with_llm(query)
                if llm_intent:
                    return llm_intent
            except Exception as e:
                self.logger.warning(f"LLM parsing failed: {e}")

        # Fallback to pattern result or basic intent
        if intent:
            return intent

        return ParsedIntent(
            intent_type="resolve_period",
            period_raw=query,
            locale=self.locale,
            confidence=0.3,
        )

    def _try_pattern_parse(self, query: str) -> Optional[ParsedIntent]:
        """Try to parse using pattern matching.

        Args:
            query: The query to parse.

        Returns:
            ParsedIntent if patterns matched, None otherwise.
        """
        normalized = query.lower().strip()

        # Extract calendar system mentions
        calendar_system = None
        if any(kw in normalized for kw in ["peru", "perú", "bancario", "banking"]):
            calendar_system = "PERU_BANKING"

        # Check for holiday/business day keywords
        exclude_holidays = any(
            kw in normalized
            for kw in [
                "excluyendo feriados",
                "excluding holidays",
                "sin feriados",
                "no holidays",
            ]
        )

        business_days_only = any(
            kw in normalized
            for kw in [
                "dias habiles",
                "días hábiles",
                "business days",
                "dias bancarios",
                "días bancarios",
                "banking days",
            ]
        )

        # Check for compositional patterns
        is_compositional = any(
            kw in normalized
            for kw in [
                "cada fin de mes",
                "each month-end",
                "por cada mes",
                "for each month",
                "para los ultimos",
                "for the last",
            ]
        )

        # Try to extract period using locale-specific patterns
        period = None
        period_type = None
        extracted = {}

        try:
            if self.locale == "es":
                period_type, extracted = parse_spanish_period(normalized)
            else:
                period_type, extracted = parse_english_period(normalized)
            period = period_type
        except ValueError:
            # Try other locale
            try:
                if self.locale != "es":
                    period_type, extracted = parse_spanish_period(normalized)
                else:
                    period_type, extracted = parse_english_period(normalized)
                period = period_type
            except ValueError:
                pass

        # Check for "N days before/after" pattern
        operation = None
        operation_value = None

        days_before = re.search(
            r"(\d+)\s*(dias?|days?)\s*(antes|before|previos?)", normalized
        )
        if days_before:
            operation = "subtract_business_days" if business_days_only else "subtract_calendar_days"
            operation_value = int(days_before.group(1))

        days_after = re.search(
            r"(\d+)\s*(dias?|days?)\s*(despues|after|siguientes?)", normalized
        )
        if days_after:
            operation = "add_business_days" if business_days_only else "add_calendar_days"
            operation_value = int(days_after.group(1))

        # Determine intent type
        intent_type = "resolve_period"
        if operation:
            intent_type = "compute_date" if period else "mixed"
        if exclude_holidays or business_days_only:
            if period:
                intent_type = "mixed"
            else:
                intent_type = "get_holidays"

        # Calculate confidence
        confidence = 0.5
        if period:
            confidence += 0.3
        if calendar_system or exclude_holidays or business_days_only:
            confidence += 0.1
        if operation:
            confidence += 0.1

        return ParsedIntent(
            intent_type=intent_type,
            period=period,
            period_raw=query,
            calendar_system=calendar_system,
            exclude_holidays=exclude_holidays,
            include_weekends=False,
            business_days_only=business_days_only,
            operation=operation,
            operation_value=operation_value,
            is_compositional=is_compositional,
            locale=self.locale,
            confidence=min(confidence, 1.0),
            extracted_values=extracted,
        )

    async def _parse_with_llm(self, query: str) -> Optional[ParsedIntent]:
        """Parse query using Azure OpenAI.

        Args:
            query: The query to parse.

        Returns:
            ParsedIntent if successful, None otherwise.
        """
        if not self.openai_client or not self.config:
            return None

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.config.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": SEMANTIC_PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            if not content:
                return None

            # Parse JSON response
            data = json.loads(content)

            return ParsedIntent(
                intent_type=data.get("intent_type", "resolve_period"),
                period=data.get("period"),
                period_raw=query,
                calendar_system=data.get("calendar_system"),
                exclude_holidays=data.get("exclude_holidays", False),
                include_weekends=data.get("include_weekends", False),
                business_days_only=data.get("business_days_only", False),
                operation=data.get("operation"),
                operation_value=data.get("operation_value"),
                is_compositional=data.get("is_compositional", False),
                iteration_target=data.get("iteration_target"),
                iteration_range=data.get("iteration_range"),
                locale=self.locale,
                confidence=data.get("confidence", 0.8),
            )

        except Exception as e:
            self.logger.error(f"LLM parsing error: {e}")
            return None
