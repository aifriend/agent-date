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
    intent_type: str  # "resolve_period", "get_holidays", "compute_date", "mixed", "comparison", "event_lookup"

    # Period information
    period: Optional[str] = None  # e.g., "last_week", "Q3 2024"
    period_raw: Optional[str] = None  # Original text

    # For comparison queries (two periods)
    period_2: Optional[str] = None  # Second period for comparison

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

    # Day-of-week filter (e.g., 0=Monday for "lunes del último mes")
    day_of_week_filter: Optional[int] = None

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
        # Check if this is an event query (not a date period query)
        if self._is_event_query(query):
            self.logger.debug("Detected event query - no period resolution needed")
            return ParsedIntent(
                intent_type="event_lookup",
                period=None,
                period_raw=query,
                locale=self.locale,
                confidence=0.9,
            )

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

        # First try exact match
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

        # If no match yet, try to find period expressions within the query
        if not period:
            period = self._extract_period_from_query(normalized)

        # Handle special composite period types extracted from query
        period_2 = None
        day_of_week_filter = None

        if period and period.startswith("comparison:"):
            # Comparison query: "comparison:q1_2024:q2_2024"
            parts = period.split(":")
            period = parts[1]  # First period
            period_2 = parts[2]  # Second period

        if period and period.startswith("dow_filter:"):
            # Day-of-week filter: "dow_filter:0:last_month"
            parts = period.split(":")
            day_of_week_filter = int(parts[1])
            period = parts[2]  # Base period (e.g., "last_month")

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
        if period_2:
            intent_type = "comparison"
        elif operation:
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
            period_2=period_2,
            period_raw=query,
            calendar_system=calendar_system,
            exclude_holidays=exclude_holidays,
            include_weekends=False,
            business_days_only=business_days_only,
            operation=operation,
            operation_value=operation_value,
            is_compositional=is_compositional,
            day_of_week_filter=day_of_week_filter,
            locale=self.locale,
            confidence=min(confidence, 1.0),
            extracted_values=extracted,
        )

    # Spanish word-to-number mapping for period expressions
    _SPANISH_WORD_NUMBERS = {
        "un": 1, "una": 1, "uno": 1,
        "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
        "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
        "diez": 10, "once": 11, "doce": 12, "quince": 15,
        "veinte": 20, "treinta": 30,
    }

    def _extract_period_from_query(self, query: str) -> Optional[str]:
        """Extract period expression from within a longer query.

        Args:
            query: Normalized query text.

        Returns:
            Extracted period type, or None.
        """
        # Common period expressions to search for within queries (Spanish + English)
        period_expressions = [
            # Explicit date range: "entre el 1 y 15 de enero 2025", "del 1 al 15 de marzo 2024"
            (r"entre\s+(?:el\s+)?(\d{1,2})\s+(?:y|al)\s+(?:el\s+)?(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+|del?\s+)?(\d{4})", "explicit_date_range_same_month"),
            (r"del?\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+|del?\s+)?(\d{4})", "explicit_date_range_same_month"),
            # Explicit date range with ISO dates
            (r"(\d{4}-\d{2}-\d{2})\s+(?:to|a|al|hasta)\s+(\d{4}-\d{2}-\d{2})", "explicit_iso_range"),
            # YTD expressions
            (r"hasta\s+el\s+momento", "ytd"),
            (r"hasta\s+ahora", "ytd"),
            (r"hasta\s+la\s+fecha", "ytd"),
            (r"al\s+d[ií]a\s+de\s+hoy", "ytd"),
            (r"acumulado\s+del\s+a[ñn]o", "ytd"),
            (r"en\s+lo\s+que\s+va\s+del\s+a[ñn]o", "ytd"),
            (r"desde\s+(?:el\s+)?inicio\s+del?\s+a[ñn]o", "ytd"),
            (r"desde\s+(?:el\s+)?comienzo\s+del?\s+a[ñn]o", "ytd"),
            (r"desde\s+(?:el\s+)?principio\s+del?\s+a[ñn]o", "ytd"),
            (r"year\s+to\s+date", "ytd"),
            (r"\bytd\b", "ytd"),
            # Weekend expressions (before week to avoid partial matches)
            (r"fin\s+de\s+semana\s+pasado", "last_weekend"),
            (r"el\s+fin\s+de\s+semana\s+pasado", "last_weekend"),
            (r"finde\s+pasado", "last_weekend"),
            (r"last\s+weekend", "last_weekend"),
            # Week expressions
            (r"esta\s+semana", "this_week"),
            (r"semana\s+pasada", "last_week"),
            (r"la\s+semana\s+pasada", "last_week"),
            (r"[úu]ltima\s+semana", "last_week"),
            (r"semana\s+antepasada", "week_before_last"),
            (r"last\s+week", "last_week"),
            (r"this\s+week", "this_week"),
            # Day-of-week filter (BEFORE month expressions to avoid partial matching)
            (r"(?:los\s+)?(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bados?|domingos?)\s+del?\s+(?:el\s+)?(?:[úu]ltimo\s+mes|mes\s+pasado|mes\s+anterior)", "dow_filter_last_month"),
            (r"(?:los\s+)?(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bados?|domingos?)\s+del?\s+(?:el\s+)?(?:este\s+mes|mes\s+actual)", "dow_filter_this_month"),
            (r"(?:los\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\s+(?:of|in|from)\s+(?:the\s+)?(?:last|previous)\s+month", "dow_filter_last_month"),
            # Month expressions
            (r"este\s+mes", "this_month"),
            (r"mes\s+pasado", "last_month"),
            (r"el\s+mes\s+pasado", "last_month"),
            (r"mes\s+anterior", "last_month"),
            (r"[úu]ltimo\s+mes", "last_month"),
            (r"last\s+month", "last_month"),
            (r"this\s+month", "this_month"),
            # Quarter expressions
            (r"este\s+trimestre", "this_quarter"),
            (r"trimestre\s+pasado", "last_quarter"),
            (r"el\s+trimestre\s+pasado", "last_quarter"),
            (r"trimestre\s+anterior(?:\s+al\s+actual)?", "last_quarter"),
            (r"[úu]ltimo\s+trimestre", "last_quarter"),
            (r"last\s+quarter", "last_quarter"),
            (r"previous\s+quarter", "last_quarter"),
            (r"this\s+quarter", "this_quarter"),
            # Year expressions
            (r"este\s+a[ñn]o", "this_year"),
            (r"a[ñn]o\s+pasado", "last_year"),
            (r"last\s+year", "last_year"),
            (r"this\s+year", "this_year"),
            # Comparison: "entre Q1 y Q2 de 2024", "diferencia entre Q1 y Q2 2024"
            (r"(?:entre|diferencia\s+(?:de\s+)?(?:consumo\s+)?entre)\s+q([1-4])\s+y\s+q([1-4])\s+(?:de\s+|del?\s+)?(\d{4})", "comparison_quarters"),
            # Named quarters
            (r"q([1-4])\s*(\d{4})", "named_quarter"),
            # Dynamic "last N X" with business days - Spanish
            (r"[úu]ltimos?\s+(\d+)\s+d[ií]as?\s+h[áa]biles?", "last_n_business_days"),
            (r"(?:los|las)\s+[úu]ltimos?\s+(\d+)\s+d[ií]as?\s+h[áa]biles?", "last_n_business_days"),
            # Dynamic "last N X" with business days - English
            (r"last\s+(\d+)\s+business\s+days?", "last_n_business_days"),
            # Dynamic "last N X" expressions - Spanish (digits)
            (r"[úu]ltimos?\s+(\d+)\s+d[ií]as?", "last_n_days"),
            (r"[úu]ltimos?\s+(\d+)\s+semanas?", "last_n_weeks"),
            (r"[úu]ltimos?\s+(\d+)\s+meses?", "last_n_months"),
            (r"(?:los|las)\s+[úu]ltimos?\s+(\d+)\s+d[ií]as?", "last_n_days"),
            (r"(?:los|las)\s+[úu]ltimos?\s+(\d+)\s+semanas?", "last_n_weeks"),
            (r"(?:los|las)\s+[úu]ltimos?\s+(\d+)\s+meses?", "last_n_months"),
            # Dynamic "last N X" expressions - English (digits)
            (r"last\s+(\d+)\s+days?", "last_n_days"),
            (r"last\s+(\d+)\s+weeks?", "last_n_weeks"),
            (r"last\s+(\d+)\s+months?", "last_n_months"),
            # Recency - "últimos consumos/transacciones" without a specific period
            (r"[úu]ltimos?\s+(?:consumos?|transacciones?|compras?|gastos?|movimientos?)", "recent"),
            (r"(?:mis|los|las)\s+[úu]ltimos?\s+(?:consumos?|transacciones?|compras?|gastos?|movimientos?)", "recent"),
            # Bare month name: "en agosto", "en marzo", "in august"
            (r"(?:en|in)\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|january|february|march|april|may|june|july|august|september|october|november|december)\b", "bare_month"),
            # Bare year: "del 2024", "en 2024", "de 2024", or standalone "2024"
            (r"(?:del?|en)\s+(\d{4})\b", "bare_year"),
            # Today/yesterday
            (r"\bhoy\b", "today"),
            (r"\bayer\b", "yesterday"),
            (r"\btoday\b", "today"),
            (r"\byesterday\b", "yesterday"),
        ]

        for pattern, period_type in period_expressions:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                # Handle dynamic last_N_X patterns
                if period_type.startswith("last_n_"):
                    n = int(match.group(1))
                    unit = period_type.replace("last_n_", "")
                    return f"last_{n}_{unit}"
                # Handle named_quarter: extract Q and year
                if period_type == "named_quarter":
                    q = match.group(1)
                    yr = match.group(2)
                    return f"q{q}_{yr}"
                # Handle comparison quarters
                if period_type == "comparison_quarters":
                    q1 = match.group(1)
                    q2 = match.group(2)
                    yr = match.group(3)
                    return f"comparison:q{q1}_{yr}:q{q2}_{yr}"
                # Handle explicit date range (same month)
                if period_type == "explicit_date_range_same_month":
                    day1 = int(match.group(1))
                    day2 = int(match.group(2))
                    month_name = match.group(3).lower()
                    yr = int(match.group(4))
                    month_num = self._spanish_month_to_number(month_name)
                    if month_num:
                        start_d = f"{yr}-{month_num:02d}-{day1:02d}"
                        end_d = f"{yr}-{month_num:02d}-{day2:02d}"
                        return f"custom:{start_d}:{end_d}"
                # Handle explicit ISO date range
                if period_type == "explicit_iso_range":
                    start_d = match.group(1)
                    end_d = match.group(2)
                    return f"custom:{start_d}:{end_d}"
                # Handle day-of-week filter
                if period_type.startswith("dow_filter_"):
                    day_name = match.group(1).lower()
                    dow = self._day_name_to_number(day_name)
                    base_period = "last_month" if "last_month" in period_type else "this_month"
                    if dow is not None:
                        return f"dow_filter:{dow}:{base_period}"
                # Handle bare month
                if period_type == "bare_month":
                    month_name = match.group(1).lower()
                    month_num = self._month_name_to_number(month_name)
                    if month_num:
                        return f"named_month_{month_num}"
                # Handle bare year
                if period_type == "bare_year":
                    yr = match.group(1)
                    return f"year_{yr}"
                return period_type

        # Try Spanish word-number patterns: "últimas dos semanas", "últimos tres meses"
        word_num_pattern = re.search(
            r"(?:los|las)?\s*[úu]ltim[ao]s?\s+(\w+)\s+(d[ií]as?\s+h[áa]biles?|d[ií]as?|semanas?|meses?)",
            query, re.IGNORECASE,
        )
        if word_num_pattern:
            word = word_num_pattern.group(1).lower()
            n = self._SPANISH_WORD_NUMBERS.get(word)
            if n is not None:
                raw_unit = word_num_pattern.group(2).lower()
                if "hábil" in raw_unit or "habil" in raw_unit:
                    return f"last_{n}_business_days"
                unit_map = {"día": "days", "dia": "days", "días": "days", "dias": "days",
                            "semana": "weeks", "semanas": "weeks",
                            "mes": "months", "meses": "months"}
                unit = unit_map.get(raw_unit, "days")
                return f"last_{n}_{unit}"

        # Bare year at the end of query as fallback: "... del 2024", "... 2024"
        bare_year_match = re.search(r"\b(20\d{2})\b", query)
        if bare_year_match:
            # Only use bare year if it's not part of a date or quarter expression
            yr = bare_year_match.group(1)
            # Avoid matching dates like "2024-01-15"
            if not re.search(r"\d{4}-\d{2}-\d{2}", query):
                return f"year_{yr}"

        return None

    # Combined Spanish + English month name mapping
    _MONTH_NAMES_MAP = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        # English
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }

    @classmethod
    def _spanish_month_to_number(cls, month_name: str) -> Optional[int]:
        """Convert a Spanish/English month name to its number."""
        return cls._MONTH_NAMES_MAP.get(month_name.lower())

    @classmethod
    def _month_name_to_number(cls, name: str) -> Optional[int]:
        """Convert a bare month name (any language) to its number."""
        return cls._MONTH_NAMES_MAP.get(name.lower().strip())

    @staticmethod
    def _day_name_to_number(day_name: str) -> Optional[int]:
        """Convert a day name (Spanish/English) to weekday number (0=Monday, 6=Sunday)."""
        days = {
            "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
            "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5,
            "sábados": 5, "sabados": 5, "domingo": 6, "domingos": 6,
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }
        return days.get(day_name.lower())

    def _is_event_query(self, query: str) -> bool:
        """Detect queries asking about specific events, not date periods."""
        event_patterns = [
            r"cuál\s+(ha\s+sido|fue)\s+mi\s+últim[ao]",
            r"cual\s+(ha\s+sido|fue)\s+mi\s+ultim[ao]",
            r"cuando\s+fue\s+(la\s+)?últim[ao]\s+vez",
            r"cuando\s+fue\s+(la\s+)?ultim[ao]\s+vez",
            r"cu[áa]ndo\s+fue\s+(la\s+)?[úu]ltim[ao]\s+vez",
            r"cuándo\s+fue\s+mi\s+primer[ao]",
            r"cuando\s+fue\s+mi\s+primer[ao]",
            r"primera\s+vez\s+que",
            r"[úu]ltima\s+vez\s+que",
            # Lifecycle / duration queries
            r"cu[áa]nto\s+tiempo\s+llevo",
            r"cu[áa]ntos\s+meses\s+llevo",
            r"desde\s+(?:que|cuando)\s+tengo",
            r"desde\s+que\s+(?:abr[ií]|activ[ée]|obtuve|inici[ée])",
            r"desde\s+que\s+tengo\s+(?:la\s+)?tarjeta",
            r"desde\s+que\s+tengo",
            r"desde\s+que\s+inici[ée]",
            # "primera compra/transacción con la tarjeta"
            r"primer[ao]\s+(?:compra|transacci[óo]n|uso)\s+(?:con|de|en)\s+(?:la\s+)?tarjeta",
            # "cuándo fue la última vez que subí de nivel"
            r"sub[ií]\s+de\s+nivel",
            # "desde cuándo estoy en el nivel actual"
            r"desde\s+cu[áa]ndo\s+estoy",
            # Banking / card event queries
            r"[úu]ltimo\s+d[ií]a\s+para\s+pagar",
            r"cu[áa]ndo\s+(?:es|ser[áa])\s+(?:el\s+)?[úu]ltimo\s+d[ií]a\s+para\s+pagar",
            r"cu[áa]ndo\s+se\s+realiza\s+(?:el\s+)?d[ée]bito",
            r"d[ée]bito\s+autom[áa]tico",
            r"fecha\s+de\s+corte",
            r"cu[áa]ntos\s+d[ií]as\s+faltan\s+para\s+(?:mi\s+)?fecha\s+de\s+corte",
            r"cu[áa]ndo\s+fue\s+mi\s+[úu]ltimo\s+pago",
            r"[úu]ltimo\s+pago\s+de\s+tarjeta",
            r"cu[áa]ndo\s+(?:es|ser[áa])\s+mi\s+(?:pr[óo]xim[ao]\s+)?(?:fecha\s+de\s+)?(?:pago|corte|vencimiento)",
            # Statement / estado de cuenta queries
            r"(?:fecha\s+(?:de|del)\s+)?(?:mi\s+)?[úu]ltimo\s+estado\s+de\s+cuenta",
            r"estado\s+de\s+cuenta",
            r"cu[áa]l\s+fue\s+la\s+fecha\s+de\s+mi\s+[úu]ltimo\s+estado",
            # "hace cuánto tiempo que no pago" / "since last full payment"
            r"hace\s+cu[áa]nto\s+(?:tiempo\s+)?que\s+no\s+pago",
            r"cu[áa]nto\s+tiempo\s+(?:llevo|ha\s+pasado)\s+sin\s+pagar",
            r"desde\s+cu[áa]ndo\s+no\s+pago",
            # Campaign / campaña queries
            r"cu[áa]ndo\s+(?:termina|empieza|inicia|comienza|acaba)\s+(?:la\s+)?campa[ñn]a",
            r"campa[ñn]a\s+(?:actual|vigente)\s+de\s+cashback",
            r"campa[ñn]a\s+(?:de\s+)?cashback\s+(?:doble|triple)",
            r"cu[áa]ntas\s+campa[ñn]as\s+(?:he\s+)?completado",
            # "hace cuánto tiempo que no uso" / inactivity queries
            r"hace\s+cu[áa]nto\s+(?:tiempo\s+)?que\s+no\s+uso",
            r"cu[áa]nto\s+tiempo\s+(?:llevo|ha\s+pasado)\s+sin\s+usar",
            r"hace\s+cu[áa]nto\s+(?:tiempo\s+)?(?:que\s+)?no\s+(?:uso|utilizo|ocupo)",
            # "cuántos días/tiempo han pasado desde mi última X"
            r"cu[áa]ntos\s+d[ií]as\s+han\s+pasado\s+desde",
            r"cu[áa]nto\s+(?:tiempo\s+)?ha\s+pasado\s+desde",
            r"desde\s+mi\s+[úu]ltim[ao]\s+(?:transacci[óo]n|compra|pago|uso)",
            # Anniversary / "cumple un año" queries
            r"cumple\s+(?:un\s+)?a[ñn]o",
            r"aniversario\s+de\s+(?:mi\s+)?tarjeta",
            r"cu[áa]ndo\s+cumple\s+(?:un\s+)?a[ñn]o",
            r"en\s+qu[ée]\s+fecha\s+cumple",
            # "cuántas transacciones he hecho desde que activé"
            r"cu[áa]ntas\s+transacciones\s+(?:he\s+)?hecho\s+desde",
        ]
        normalized = query.lower()
        return any(re.search(p, normalized) for p in event_patterns)

    def _normalize_period_type(self, period: Optional[str]) -> Optional[str]:
        """Normalize period type names from LLM output.

        The LLM may return variations like "year_to_date" instead of "ytd".
        This normalizes them to the canonical form used by tools.

        Args:
            period: Period type from LLM.

        Returns:
            Normalized period type.
        """
        if not period:
            return None

        normalized = period.lower().strip()

        # Event-based patterns - return None to signal no period resolution needed
        event_patterns = [
            "last_redemption", "last_usage", "last_time_cashback_used",
            "last_purchase", "first_purchase", "last_level_up",
            "first_transaction", "last_transaction",
            "mondays_of_last_month", "tuesdays_of_last_month",  # day-of-week filters
            # Lifecycle / duration / since-opening patterns from LLM
            "since_card_opening", "since_account_opening", "since_activation",
            "since_card_activation", "card_opening_date", "account_opening_date",
            "current_loyalty_level_duration", "loyalty_level_duration",
            "time_in_current_level", "level_duration",
            "last_time_level_up", "last_level_change", "last_upgrade",
            "last_time_upgraded", "last_tier_change",
            # Banking / card date event patterns from LLM
            "current_level_start_date", "level_start_date",
            "payment_due_date", "next_payment_date", "due_date",
            "last_payment_date", "last_payment", "previous_payment_date",
            "fecha_de_corte", "billing_cycle_date", "statement_date",
            "cut_off_date", "cutoff_date", "billing_date",
            "next_due_date", "next_billing_date", "next_statement_date",
            "débito automático", "debito automatico", "auto_debit_date",
            "automatic_debit", "direct_debit_date",
            # Statement / estado de cuenta patterns from LLM
            "last_statement_date", "statement_date", "last_statement",
            "previous_statement_date", "ultimo_estado_de_cuenta",
            # Since last full payment patterns from LLM
            "since_last_full_payment", "since_last_payment",
            "last_full_payment", "last_full_payment_date",
            "time_since_last_payment", "time_since_full_payment",
            # Campaign / cashback patterns from LLM
            "current_cashback_double_campaign", "current_campaign",
            "cashback_double_campaign", "cashback_campaign_end_date",
            "current_campaign_end_date", "campaign_end_date",
            "campaigns_completed", "completed_campaigns",
            # Card issued / opening from LLM
            "since_card_issued", "card_issued_date", "card_issue_date",
            "since_card_issuance",
            # Inception / first usage patterns from LLM
            "since_inception", "since_beginning", "since_start",
            "since_first_use", "since_first_transaction",
            "first_purchase_with_card", "first_purchase_date",
            "first_card_purchase", "first_use_date",
            # Card usage duration from LLM
            "card_usage_duration", "months_with_card", "time_with_card",
            "card_age", "account_age",
            # Anniversary / milestone patterns from LLM
            "one_year_anniversary_of_card_issue_date",
            "card_anniversary", "card_anniversary_date",
            "one_year_anniversary", "anniversary_date",
            # Last usage / inactivity patterns from LLM
            "last_card_usage", "last_physical_card_usage",
            "time_since_last_use", "time_since_last_card_use",
            "since_last_transaction", "days_since_last_transaction",
            "since_last_use", "last_usage_date",
            "first_purchase_with_card",
        ]
        if normalized in event_patterns:
            return None  # Will trigger event_lookup intent

        # Also catch event patterns via regex for broader coverage
        event_regex_patterns = [
            r"^since_",          # since_card_opening, since_activation, etc.
            r"_duration$",       # current_loyalty_level_duration, etc.
            r"^time_in_",        # time_in_current_level, etc.
            r"_opening_date$",   # card_opening_date, account_opening_date
            r"_due_date$",       # payment_due_date, next_due_date, etc.
            r"_payment_date$",   # last_payment_date, next_payment_date, etc.
            r"_start_date$",     # current_level_start_date, etc.
            r"^next_",           # next_payment_date, next_billing_date, etc.
            r"_billing_",        # billing_cycle_date, billing_date, etc.
            r"_debit",           # auto_debit_date, direct_debit_date, etc.
            r"fecha_de_",        # fecha_de_corte, etc.
            r"^cut_?off",        # cut_off_date, cutoff_date
            r"_statement",       # last_statement_date, statement_date, etc.
            r"_campaign",        # current_cashback_double_campaign, campaign_end_date, etc.
            r"^campaign",        # campaign_end_date, campaigns_completed, etc.
            r"_full_payment",    # since_last_full_payment, last_full_payment_date, etc.
            r"_issued",          # since_card_issued, card_issued_date, etc.
            r"_issuance",        # since_card_issuance
            r"^completed_",      # completed_campaigns
            r"_inception",       # since_inception
            r"^first_",          # first_purchase_with_card, first_purchase_date, etc.
            r"_age$",            # card_age, account_age
            r"_with_card$",      # first_purchase_with_card, months_with_card, etc.
            r"_anniversary",     # one_year_anniversary, card_anniversary, etc.
            r"_last_use$",       # time_since_last_use, since_last_use, etc.
            r"_last_usage",      # last_card_usage, last_physical_card_usage, etc.
            r"^days_since_",     # days_since_last_transaction, etc.
            r"^time_since_",     # time_since_last_use, time_since_last_card_use, etc.
            r"^last_.*_usage",   # last_card_usage, last_physical_card_usage
        ]
        if any(re.search(p, normalized) for p in event_regex_patterns):
            return None

        # Comprehensive mapping of LLM variations to canonical period types
        normalization_map = {
            # YTD variations
            "year_to_date": "ytd",
            "year-to-date": "ytd",
            "yeartodate": "ytd",
            "start_of_year_to_now": "ytd",
            "start_of_year": "ytd",
            "beginning_of_year": "ytd",
            "from_start_of_year": "ytd",
            "desde_inicio_del_año": "ytd",
            "desde_inicio_del_ano": "ytd",
            "hasta el momento": "ytd",
            "hasta ahora": "ytd",
            "hasta la fecha": "ytd",

            # Week variations
            "this_week": "this_week",
            "last_week": "last_week",
            "previous_week": "last_week",
            "last_weekend": "last_weekend",

            # Month variations
            "this_month": "this_month",
            "last_month": "last_month",
            "previous_month": "last_month",

            # Quarter variations
            "this_quarter": "this_quarter",
            "last_quarter": "last_quarter",
            "previous_quarter": "last_quarter",

            # Year variations
            "this_year": "this_year",
            "last_year": "last_year",
            "previous_year": "last_year",

            # Recent = last week
            "recent": "last_week",
        }

        # Direct match
        if normalized in normalization_map:
            return normalization_map[normalized]

        # Handle bare month names (Spanish/English): "agosto", "march", etc.
        month_num = self._month_name_to_number(normalized)
        if month_num is not None:
            return f"named_month_{month_num}"

        # Handle "last_N_business_days" patterns
        biz_match = re.match(r"last[_\s]?(\d+)[_\s]?business[_\s]?days?", normalized)
        if biz_match:
            n = int(biz_match.group(1))
            return f"last_{n}_business_days"

        # Handle "last_N_X" patterns dynamically
        last_n_match = re.match(r"last[_\s]?(\d+)[_\s]?(days?|weeks?|months?)", normalized)
        if last_n_match:
            n = int(last_n_match.group(1))
            unit = last_n_match.group(2).rstrip('s')  # Remove plural
            return f"last_{n}_{unit}s"

        # Handle comma-separated periods (comparison queries from LLM)
        if "," in normalized:
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) == 2:
                # Return as comparison format that _parse_with_llm can handle
                return f"comparison:{parts[0]}:{parts[1]}"

        # Handle bare year: "2024"
        if re.match(r"^\d{4}$", normalized):
            return f"year_{normalized}"

        # Handle explicit date range from LLM: "2025-01-01 to 2025-01-15"
        range_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(?:to|a|al|-)\s+(\d{4}-\d{2}-\d{2})$", normalized)
        if range_match:
            return f"custom:{range_match.group(1)}:{range_match.group(2)}"

        return period

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

            # Normalize period types from LLM output
            raw_period = data.get("period")
            period = self._normalize_period_type(raw_period)

            # If period was normalized to None (event query), set intent accordingly
            intent_type = data.get("intent_type", "resolve_period")
            period_2 = None
            day_of_week_filter = None

            if period is None and raw_period is not None:
                # Check if the raw period can be handled by pattern extraction
                extracted_period = self._extract_period_from_query(raw_period.lower())
                if extracted_period:
                    period = extracted_period
                else:
                    intent_type = "event_lookup"

            # Handle comparison format from normalization
            if period and period.startswith("comparison:"):
                parts = period.split(":")
                period = parts[1]
                period_2 = parts[2]
                intent_type = "comparison"

            # Handle custom date ranges
            if period and period.startswith("custom:"):
                pass  # Keep as-is, resolve_period_tool will handle it

            # Handle day-of-week filter patterns from LLM
            if period and period.startswith("dow_filter:"):
                parts = period.split(":")
                day_of_week_filter = int(parts[1])
                period = parts[2]

            return ParsedIntent(
                intent_type=intent_type,
                period=period,
                period_2=period_2,
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
                day_of_week_filter=day_of_week_filter,
                locale=self.locale,
                confidence=data.get("confidence", 0.8),
            )

        except Exception as e:
            self.logger.error(f"LLM parsing error: {e}")
            return None
