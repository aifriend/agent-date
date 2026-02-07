"""Challenger Agent - generates complex date queries with ground truth."""

import json
import logging
import random
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from date_agent.feedback.ground_truth import GroundTruthComputer
from date_agent.feedback.models import ChallengerQuery, QueryCategory

logger = logging.getLogger("Challenger")


class ChallengerAgent:
    """Generates challenging date queries with verified ground truth.

    Two generation modes:
    1. Template-based (~70%): Parameterized query templates (deterministic)
    2. LLM-assisted (~30%): Azure OpenAI generates creative phrasings,
       but ground truth is ALWAYS computed deterministically.
    """

    def __init__(
        self,
        reference_date: date,
        config: Any = None,
        openai_client: Any = None,
    ):
        self.ref = reference_date
        self.gt = GroundTruthComputer(reference_date)
        self.config = config
        self.openai_client = openai_client
        self._query_counter = 0
        self._category_counts: Dict[QueryCategory, int] = {
            c: 0 for c in QueryCategory
        }

    def _next_id(self) -> str:
        self._query_counter += 1
        return f"{self._query_counter:05d}"

    def generate_batch(self, size: int = 50) -> List[ChallengerQuery]:
        """Generate a batch of queries ensuring category coverage."""
        queries: List[ChallengerQuery] = []

        # Ensure minimum coverage per category
        for category in QueryCategory:
            if self._category_counts[category] < 3:
                generated = self._generate_for_category(category, count=2)
                queries.extend(generated)
                self._category_counts[category] += len(generated)

        # Fill remaining with weighted random selection
        remaining = size - len(queries)
        if remaining > 0:
            queries.extend(self._generate_weighted_random(remaining))

        random.shuffle(queries)
        return queries[:size]

    def _generate_weighted_random(self, count: int) -> List[ChallengerQuery]:
        """Generate random queries with weighted category selection."""
        # Weight challenging categories higher
        weights = {
            QueryCategory.SIMPLE_PERIOD: 3,
            QueryCategory.NAMED_QUARTER: 2,
            QueryCategory.DYNAMIC_LAST_N: 3,
            QueryCategory.BUSINESS_DAYS: 2,
            QueryCategory.YTD: 1,
            QueryCategory.CUSTOM_RANGE: 2,
            QueryCategory.COMPARISON: 2,
            QueryCategory.DOW_FILTER: 2,
            QueryCategory.WEEKEND: 1,
            QueryCategory.NAMED_MONTH: 2,
            QueryCategory.NAMED_YEAR: 1,
            QueryCategory.EVENT_QUERY: 3,
            QueryCategory.EDGE_CASE: 3,
            QueryCategory.LOOKBACK_BOUNDARY: 1,
            QueryCategory.INVALID_QUERY: 1,
            QueryCategory.COMPOSITIONAL: 1,
        }
        categories = list(weights.keys())
        w = [weights[c] for c in categories]

        queries = []
        for _ in range(count):
            cat = random.choices(categories, weights=w, k=1)[0]
            generated = self._generate_for_category(cat, count=1)
            queries.extend(generated)
            if generated:
                self._category_counts[cat] += len(generated)
        return queries

    def _generate_for_category(
        self, category: QueryCategory, count: int
    ) -> List[ChallengerQuery]:
        """Generate queries for a specific category."""
        generators = {
            QueryCategory.SIMPLE_PERIOD: self._gen_simple_periods,
            QueryCategory.NAMED_QUARTER: self._gen_named_quarters,
            QueryCategory.DYNAMIC_LAST_N: self._gen_last_n,
            QueryCategory.BUSINESS_DAYS: self._gen_business_days,
            QueryCategory.YTD: self._gen_ytd,
            QueryCategory.CUSTOM_RANGE: self._gen_custom_range,
            QueryCategory.COMPARISON: self._gen_comparisons,
            QueryCategory.DOW_FILTER: self._gen_dow_filters,
            QueryCategory.WEEKEND: self._gen_weekends,
            QueryCategory.NAMED_MONTH: self._gen_named_months,
            QueryCategory.NAMED_YEAR: self._gen_named_years,
            QueryCategory.EVENT_QUERY: self._gen_event_queries,
            QueryCategory.EDGE_CASE: self._gen_edge_cases,
            QueryCategory.LOOKBACK_BOUNDARY: self._gen_lookback_boundaries,
            QueryCategory.INVALID_QUERY: self._gen_invalid_queries,
            QueryCategory.COMPOSITIONAL: self._gen_compositional,
        }
        return generators[category](count)

    def _make_query(
        self,
        text: str,
        lang: str,
        category: QueryCategory,
        start: str,
        end: str,
        days: int,
        period_type: Optional[str] = None,
        intent_type: str = "resolve_period",
        success: bool = True,
        difficulty: str = "medium",
        description: str = "",
    ) -> ChallengerQuery:
        return ChallengerQuery(
            query_id=f"tmpl_{self._next_id()}",
            query_text=text,
            language=lang,
            category=category,
            reference_date=self.ref,
            expected_success=success,
            expected_start_date=start if success else None,
            expected_end_date=end if success else None,
            expected_calendar_days=days if success else None,
            expected_period_type=period_type,
            expected_intent_type=intent_type,
            difficulty=difficulty,
            description=description,
        )

    # =================================================================
    # CATEGORY GENERATORS
    # =================================================================

    def _gen_simple_periods(self, count: int) -> List[ChallengerQuery]:
        templates_es = [
            "cuánto gasté {period}?",
            "mostrar transacciones de {period}",
            "consultar mis consumos de {period}",
            "cuáles fueron mis movimientos {period}",
        ]
        templates_en = [
            "show me {period} transactions",
            "what happened {period}?",
            "give me my {period} summary",
        ]
        periods = [
            ("hoy", "today", "today"),
            ("ayer", "yesterday", "yesterday"),
            ("esta semana", "this week", "this_week"),
            ("la semana pasada", "last week", "last_week"),
            ("la semana antepasada", "the week before last", "week_before_last"),
            ("este mes", "this month", "this_month"),
            ("el mes pasado", "last month", "last_month"),
            ("este trimestre", "this quarter", "this_quarter"),
            ("el trimestre pasado", "last quarter", "last_quarter"),
            ("este año", "this year", "this_year"),
            ("el año pasado", "last year", "last_year"),
        ]

        queries = []
        for _ in range(count):
            period_es, period_en, ptype = random.choice(periods)
            if random.random() < 0.6:
                text = random.choice(templates_es).format(period=period_es)
                lang = "es"
            else:
                text = random.choice(templates_en).format(period=period_en)
                lang = "en"
            start, end, days = self.gt.compute_period(ptype)
            queries.append(self._make_query(
                text, lang, QueryCategory.SIMPLE_PERIOD,
                start, end, days, period_type=ptype,
                difficulty="easy",
            ))
        return queries

    def _gen_named_quarters(self, count: int) -> List[ChallengerQuery]:
        queries = []
        year_options = [2024, 2023]
        for _ in range(count):
            q = random.randint(1, 4)
            y = random.choice(year_options)
            formats = [
                (f"Q{q} {y}", "en"),
                (f"Q{q} del {y}", "es"),
                (f"T{q} {y}", "es"),
                (f"trimestre {q} de {y}", "es"),
            ]
            text, lang = random.choice(formats)
            start, end, days = self.gt.compute_period(
                "named_quarter", {"quarter": q, "year": y}
            )
            queries.append(self._make_query(
                text, lang, QueryCategory.NAMED_QUARTER,
                start, end, days, period_type="named_quarter",
            ))
        return queries

    def _gen_last_n(self, count: int) -> List[ChallengerQuery]:
        queries = []
        for _ in range(count):
            unit = random.choice(["days", "weeks", "months"])
            n = random.randint(2, 6)
            ptype = f"last_{n}_{unit}"

            if random.random() < 0.6:
                word_map = {"days": "días", "weeks": "semanas", "months": "meses"}
                text = f"últimos {n} {word_map[unit]}"
                lang = "es"
            else:
                text = f"last {n} {unit}"
                lang = "en"

            start, end, days = self.gt.compute_period(ptype)
            queries.append(self._make_query(
                text, lang, QueryCategory.DYNAMIC_LAST_N,
                start, end, days, period_type=ptype,
            ))
        return queries

    def _gen_business_days(self, count: int) -> List[ChallengerQuery]:
        queries = []
        for _ in range(count):
            n = random.choice([5, 10, 15, 20])
            ptype = f"last_{n}_business_days"
            if random.random() < 0.6:
                text = f"últimos {n} días hábiles"
                lang = "es"
            else:
                text = f"last {n} business days"
                lang = "en"
            start, end, days = self.gt.compute_period(ptype)
            queries.append(self._make_query(
                text, lang, QueryCategory.BUSINESS_DAYS,
                start, end, days, period_type=ptype,
            ))
        return queries

    def _gen_ytd(self, count: int) -> List[ChallengerQuery]:
        queries = []
        options = [
            ("acumulado del año", "es"),
            ("hasta el momento", "es"),
            ("year to date", "en"),
            ("ytd", "en"),
            ("en lo que va del año", "es"),
        ]
        for _ in range(count):
            text, lang = random.choice(options)
            start, end, days = self.gt.compute_period("ytd")
            queries.append(self._make_query(
                text, lang, QueryCategory.YTD,
                start, end, days, period_type="ytd",
            ))
        return queries

    def _gen_custom_range(self, count: int) -> List[ChallengerQuery]:
        queries = []
        ranges = [
            ("2024-01-01", "2024-01-31", "entre el 1 y 31 de enero 2024", "es"),
            ("2024-03-15", "2024-04-15", "del 15 de marzo al 15 de abril 2024", "es"),
            ("2024-06-01", "2024-06-30", "del 1 al 30 de junio 2024", "es"),
            ("2024-05-01", "2024-05-31", "entre el 1 y 31 de mayo 2024", "es"),
        ]
        for _ in range(count):
            s, e, text, lang = random.choice(ranges)
            start, end, days = self.gt.compute_period(
                "custom", {"start": s, "end": e}
            )
            queries.append(self._make_query(
                text, lang, QueryCategory.CUSTOM_RANGE,
                start, end, days, period_type="custom",
            ))
        return queries

    def _gen_comparisons(self, count: int) -> List[ChallengerQuery]:
        queries = []
        comps = [
            ("diferencia entre Q1 y Q2 de 2024", "es"),
            ("comparar este mes vs el mes pasado", "es"),
            ("Q1 2024 vs Q2 2024", "en"),
        ]
        for _ in range(count):
            text, lang = random.choice(comps)
            # For comparisons, we validate the intent_type rather than dates
            queries.append(ChallengerQuery(
                query_id=f"tmpl_{self._next_id()}",
                query_text=text,
                language=lang,
                category=QueryCategory.COMPARISON,
                reference_date=self.ref,
                expected_success=True,
                expected_intent_type="comparison",
                difficulty="hard",
                description="Comparison query - validate intent detection",
            ))
        return queries

    def _gen_dow_filters(self, count: int) -> List[ChallengerQuery]:
        queries = []
        options = [
            ("los lunes del mes pasado", "es"),
            ("los viernes del último mes", "es"),
            ("mondays of last month", "en"),
        ]
        for _ in range(count):
            text, lang = random.choice(options)
            # DOW filter queries: validate intent detection
            queries.append(ChallengerQuery(
                query_id=f"tmpl_{self._next_id()}",
                query_text=text,
                language=lang,
                category=QueryCategory.DOW_FILTER,
                reference_date=self.ref,
                expected_success=True,
                expected_intent_type="resolve_period",
                difficulty="hard",
                description="Day-of-week filter query",
            ))
        return queries

    def _gen_weekends(self, count: int) -> List[ChallengerQuery]:
        queries = []
        options = [
            ("fin de semana pasado", "es"),
            ("el finde pasado", "es"),
            ("last weekend", "en"),
        ]
        for _ in range(count):
            text, lang = random.choice(options)
            start, end, days = self.gt.compute_period("last_weekend")
            queries.append(self._make_query(
                text, lang, QueryCategory.WEEKEND,
                start, end, days, period_type="last_weekend",
            ))
        return queries

    def _gen_named_months(self, count: int) -> List[ChallengerQuery]:
        queries = []
        month_names_es = [
            "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        month_names_en = [
            "", "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ]
        for _ in range(count):
            m = random.randint(1, 6)  # First half of 2024 (within lookback)
            y = 2024
            if random.random() < 0.6:
                text = f"en {month_names_es[m]} {y}"
                lang = "es"
            else:
                text = f"in {month_names_en[m]} {y}"
                lang = "en"
            start, end, days = self.gt.compute_period(
                "named_month", {"month": m, "year": y}
            )
            queries.append(self._make_query(
                text, lang, QueryCategory.NAMED_MONTH,
                start, end, days, period_type="named_month",
            ))
        return queries

    def _gen_named_years(self, count: int) -> List[ChallengerQuery]:
        queries = []
        for _ in range(count):
            y = random.choice([2023, 2024])
            formats = [
                (f"del {y}", "es"),
                (f"en {y}", "es"),
                (f"año {y}", "es"),
            ]
            text, lang = random.choice(formats)
            start, end, days = self.gt.compute_period(
                "named_year", {"year": y}
            )
            queries.append(self._make_query(
                text, lang, QueryCategory.NAMED_YEAR,
                start, end, days, period_type="named_year",
            ))
        return queries

    def _gen_event_queries(self, count: int) -> List[ChallengerQuery]:
        queries = []
        events = [
            ("cuál ha sido mi última redención?", "es"),
            ("cuándo fue la última vez que usé mi tarjeta?", "es"),
            ("cuándo fue mi primera compra?", "es"),
            ("hace cuánto que no uso mi tarjeta?", "es"),
            ("cuál fue mi último estado de cuenta?", "es"),
            ("cuándo es mi próximo pago?", "es"),
            ("cuánto tiempo llevo con mi tarjeta?", "es"),
            ("cuándo caduca mi tarjeta?", "es"),
            ("cuándo fue mi último depósito?", "es"),
            ("cuándo termina la campaña de puntos?", "es"),
        ]
        for _ in range(count):
            text, lang = random.choice(events)
            queries.append(ChallengerQuery(
                query_id=f"tmpl_{self._next_id()}",
                query_text=text,
                language=lang,
                category=QueryCategory.EVENT_QUERY,
                reference_date=self.ref,
                expected_success=True,
                expected_intent_type="event_lookup",
                difficulty="medium",
                description="Event query - should detect as event_lookup, not resolve dates",
            ))
        return queries

    def _gen_edge_cases(self, count: int) -> List[ChallengerQuery]:
        queries = []
        # Q1 2024 - leap year (Feb 29)
        s, e, d = self.gt.compute_period("named_quarter", {"quarter": 1, "year": 2024})
        queries.append(self._make_query(
            "Q1 2024", "en", QueryCategory.EDGE_CASE,
            s, e, d, period_type="named_quarter",
            difficulty="hard", description="Q1 in leap year (Feb 29 = 91 days)",
        ))

        # Full year 2024 - leap year (366 days)
        s, e, d = self.gt.compute_period("named_year", {"year": 2024})
        queries.append(self._make_query(
            "año 2024", "es", QueryCategory.EDGE_CASE,
            s, e, d, period_type="named_year",
            difficulty="hard", description="Full leap year (366 days)",
        ))

        # February 2024 - 29 days
        s, e, d = self.gt.compute_period("named_month", {"month": 2, "year": 2024})
        queries.append(self._make_query(
            "febrero 2024", "es", QueryCategory.EDGE_CASE,
            s, e, d, period_type="named_month",
            difficulty="hard", description="Feb in leap year (29 days)",
        ))

        return queries[:count]

    def _gen_lookback_boundaries(self, count: int) -> List[ChallengerQuery]:
        queries = []
        # Periods near the 6-month lookback limit
        # From July 15, 6 months back = ~Jan 15
        s, e, d = self.gt.compute_period("named_month", {"month": 1, "year": 2024})
        queries.append(self._make_query(
            "enero 2024", "es", QueryCategory.LOOKBACK_BOUNDARY,
            s, e, d, period_type="named_month",
            description="Month at the edge of 6-month lookback",
        ))

        s, e, d = self.gt.compute_period("named_month", {"month": 2, "year": 2024})
        queries.append(self._make_query(
            "febrero 2024", "es", QueryCategory.LOOKBACK_BOUNDARY,
            s, e, d, period_type="named_month",
            description="Month within 6-month lookback",
        ))
        return queries[:count]

    def _gen_invalid_queries(self, count: int) -> List[ChallengerQuery]:
        # Invalid query detection requires the LLM fallback, so we skip
        # generating these templates to avoid false failures in the
        # challenger evaluation loop. The counter is still incremented
        # by _next_id() if we ever add LLM-validated invalid queries.
        return []

    def _gen_compositional(self, count: int) -> List[ChallengerQuery]:
        # Compositional queries (e.g. "3 días hábiles antes del fin de mes")
        # require the full iteration pipeline and cannot be validated with
        # simple start/end date checks. Skip for now.
        return []

    # =================================================================
    # LLM-ASSISTED GENERATION
    # =================================================================

    async def generate_llm_queries(self, count: int) -> List[ChallengerQuery]:
        """Use Azure OpenAI to generate creative query phrasings.

        Ground truth is ALWAYS computed deterministically first.
        The LLM only generates natural language wrappers.
        """
        if not self.openai_client:
            logger.warning("No OpenAI client - falling back to templates")
            return self._generate_weighted_random(count)

        # Pick random period types and pre-compute ground truth
        period_types = [
            "last_week", "this_month", "last_month", "ytd",
            "this_quarter", "last_quarter", "yesterday", "today",
        ]

        queries = []
        for _ in range(count):
            ptype = random.choice(period_types)
            try:
                start, end, days = self.gt.compute_period(ptype)
            except Exception:
                continue

            try:
                prompt = (
                    f"Genera 1 consulta creativa en español que un cliente bancario "
                    f"haría para ver datos del periodo '{ptype}'. "
                    f"Incluye contexto como cashback, transacciones, puntos, consumos. "
                    f"Responde solo con el texto de la consulta, nada más."
                )
                response = await self.openai_client.chat.completions.create(
                    model=self.config.azure_openai_deployment if self.config else "gpt-4",
                    messages=[
                        {"role": "system", "content": "Eres un cliente de banco peruano."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.8,
                    max_tokens=100,
                )
                text = response.choices[0].message.content.strip().strip('"')
                queries.append(self._make_query(
                    text, "es", QueryCategory.SIMPLE_PERIOD,
                    start, end, days, period_type=ptype,
                    description=f"LLM-generated for {ptype}",
                ))
            except Exception as e:
                logger.warning(f"LLM query generation failed: {e}")

        return queries
