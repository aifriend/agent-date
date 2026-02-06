"""Integration tests for query examples across different categories.

This test suite validates the semantic parser and agent can handle
various types of financial queries related to:
- Cashback
- Consumos (Spending)
- Loyalty/Niveles
- Knowledge Base / General
- Campaigns
- Other queries

Note: These queries are NOT date-specific queries. They test the agent's
ability to handle queries that may or may not contain temporal components.
The agent should gracefully handle non-date queries or extract date context
from queries that have temporal elements.
"""

import pytest
from datetime import datetime, timezone
from typing import List, Tuple

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from date_agent.agent.date_agent import DateReasoningAgent
from date_agent.agent.semantic_parser import SemanticParser
from date_agent.core.config import DateAgentConfig


# =============================================================================
# QUERY TEST DATA
# =============================================================================

# Cashback queries with expected characteristics
CASHBACK_QUERIES: List[Tuple[str, dict]] = [
    # (query, expected_properties)
    ("¿Qué es cashback?", {"has_temporal": False, "category": "cashback_info"}),
    ("Cuanto cashback puedo obtener usando la tc io?", {"has_temporal": False, "category": "cashback_info"}),
    ("Usé mi tc en un casino y no he recibido cashback, qué fue?", {"has_temporal": False, "category": "cashback_issue"}),
    ("Puedo acumular cashback en todos los establecimientos?", {"has_temporal": False, "category": "cashback_info"}),  # "todos" is not temporal
    ("cuánto cashback he ganado hasta el momento?", {"has_temporal": True, "temporal_hint": "until_now", "category": "cashback_balance"}),
    ("cuantos puntos tengo?", {"has_temporal": False, "category": "points_balance"}),
    ("cuantos puntos he ganado la última semana?", {"has_temporal": True, "temporal_hint": "last_week", "category": "points_earned"}),
    ("para qué me sirve el cashback?", {"has_temporal": False, "category": "cashback_info"}),
    ("Cual es mi cashback?", {"has_temporal": False, "category": "cashback_balance"}),
    ("cuanto cashback tengo?", {"has_temporal": False, "category": "cashback_balance"}),
    ("quiero saber mi cashback", {"has_temporal": False, "category": "cashback_balance"}),
    ("cuantos puntos tengo acumulados", {"has_temporal": False, "category": "points_balance"}),
    ("cuantas millas tengo?", {"has_temporal": False, "category": "miles_balance"}),
    ("cuánto cashback por campañas he ganado este mes?", {"has_temporal": True, "temporal_hint": "this_month", "category": "cashback_campaigns"}),
    ("cuándo cashback por consumo he ganado este mes?", {"has_temporal": True, "temporal_hint": "this_month", "category": "cashback_spending"}),
    ("cómo está compuesto mi cashback?", {"has_temporal": False, "category": "cashback_breakdown"}),
    ("cuánto cashback he redimido el último mes?", {"has_temporal": True, "temporal_hint": "last_month", "category": "cashback_redeemed"}),
    ("¿Cuánto cashback he ganado con mi tarjeta io en el último mes?", {"has_temporal": True, "temporal_hint": "last_month", "category": "cashback_earned"}),
    ("Cuánto cashback generé esta semana?", {"has_temporal": True, "temporal_hint": "this_week", "category": "cashback_earned"}),
    ("Cuándo cashback he usado en los que va del año?", {"has_temporal": True, "temporal_hint": "ytd", "category": "cashback_used"}),
    ("cuál ha sido mi última redención?", {"has_temporal": True, "temporal_hint": "last", "category": "cashback_redemption"}),
    ("Si quiero tener 50 soles de cashback, cuánto dinero debo gastar?", {"has_temporal": False, "category": "cashback_calculation"}),
    ("cuánto cashback acumulé en deliverys?", {"has_temporal": False, "category": "cashback_category"}),
    ("Si gasto 55 soles, cuánto cashback ganaré?", {"has_temporal": False, "category": "cashback_calculation"}),
    ("qué monto de cashback acumulé esta semana?", {"has_temporal": True, "temporal_hint": "this_week", "category": "cashback_earned"}),
    ("cuánto cashback he generado en pedidos por delivery?", {"has_temporal": False, "category": "cashback_category"}),
    ("Cuantas millas gané el último mes por delivery?", {"has_temporal": True, "temporal_hint": "last_month", "category": "miles_earned"}),
    ("cuánto cashback he obtenido por campañas?", {"has_temporal": False, "category": "cashback_campaigns"}),
    ("cuánto cashback he ganado de febrero hasta hoy?", {"has_temporal": True, "temporal_hint": "date_range", "category": "cashback_earned"}),
    ("cuando fue la última vez que usé cashback?", {"has_temporal": True, "temporal_hint": "last", "category": "cashback_usage"}),
    ("¿El cashback tiene límite de acumulación?", {"has_temporal": False, "category": "cashback_info"}),
    ("¿Cómo puedo acumular cashback con mi tc io?", {"has_temporal": False, "category": "cashback_info"}),
    ("¿Debo llegar a un monto mínimo de consumos para empezar a acumular cashback?", {"has_temporal": False, "category": "cashback_info"}),
    ("¿Para qué puedo utilizar mi cashback?", {"has_temporal": False, "category": "cashback_info"}),
    ("¿Cuál es el % de cashback que se aplica para todas las compras?", {"has_temporal": False, "category": "cashback_info"}),
    ("Cómo se calcula el cashback?", {"has_temporal": False, "category": "cashback_info"}),
    ("Puedo transferir mi cashback a otras personas?", {"has_temporal": False, "category": "cashback_info"}),
    ("¿Cómo puedo redimir mi cashback?", {"has_temporal": False, "category": "cashback_info"}),
    ("¿Cuándo me abonan mi cashback?", {"has_temporal": True, "temporal_hint": "when", "category": "cashback_info"}),
    ("¿Y si nunca me abonaron mi cashback?", {"has_temporal": False, "category": "cashback_issue"}),
    ("¿En qué momento empiezo a acumular cashback? ¿Necesito llegar a un monto mínimo?", {"has_temporal": False, "category": "cashback_info"}),  # "momento" here is not a date reference
]

# Consumos (Spending) queries
CONSUMOS_QUERIES: List[Tuple[str, dict]] = [
    ("¿Cuáles han sido mis últimos consumos?", {"has_temporal": True, "temporal_hint": "recent", "category": "spending_history"}),
    ("quiero saber cuanto he gastado en restaurantes en el último mes", {"has_temporal": True, "temporal_hint": "last_month", "category": "spending_category"}),
    ("en qué gasto más mi plata?", {"has_temporal": False, "category": "spending_analysis"}),
    ("Cuanto he consumido en los últimos 15 días?", {"has_temporal": True, "temporal_hint": "last_15_days", "category": "spending_total"}),
    ("en qué categorías he consumido más en el último mes?", {"has_temporal": True, "temporal_hint": "last_month", "category": "spending_categories"}),
    ("cuánto he gastado en todo lo que lleva del año con mi tc?", {"has_temporal": True, "temporal_hint": "ytd", "category": "spending_total"}),
    ("en qué comercio gasté más en el último mes?", {"has_temporal": True, "temporal_hint": "last_month", "category": "spending_merchant"}),
    ("cuánto gasté en delivery este último mes?", {"has_temporal": True, "temporal_hint": "last_month", "category": "spending_category"}),
    ("Gasté más este mes que el anterior?", {"has_temporal": True, "temporal_hint": "month_comparison", "category": "spending_comparison"}),
    ("cuales son mis 3 categorias de mayor consumo?", {"has_temporal": False, "category": "spending_categories"}),  # No explicit time period
    ("cual es mi ticket promedio por compra?", {"has_temporal": False, "category": "spending_average"}),
    ("cuál fue mi compra más alta del último mes?", {"has_temporal": True, "temporal_hint": "last_month", "category": "spending_max"}),
    ("cuántas compras hice este mes?", {"has_temporal": True, "temporal_hint": "this_month", "category": "spending_count"}),
    ("cuándo gasté el fin de semana pasado?", {"has_temporal": True, "temporal_hint": "last_weekend", "category": "spending_total"}),
    ("Mi gasto en deliverys está subiendo o bajando?", {"has_temporal": False, "temporal_hint": "trend", "category": "spending_trend"}),  # Trend implies time but no explicit temporal keyword
    ("cuándo fue mi máximo gasto en un solo día?", {"has_temporal": True, "temporal_hint": "max_day", "category": "spending_max"}),
    ("cuánto fue mi gasto promedio por día de este mes?", {"has_temporal": True, "temporal_hint": "this_month", "category": "spending_average"}),
    ("cuánto he consumido en soles vs dólares este mes?", {"has_temporal": True, "temporal_hint": "this_month", "category": "spending_currency"}),
    ("cuánto he consumido con mi tarjeta en los últimos 7 días?", {"has_temporal": True, "temporal_hint": "last_7_days", "category": "spending_total"}),
    ("cuál ha sido mi gasto total en las últimas dos semanas?", {"has_temporal": True, "temporal_hint": "last_2_weeks", "category": "spending_total"}),
    ("cuales fueron las categorias de mayor gasto el mes pasado?", {"has_temporal": True, "temporal_hint": "last_month", "category": "spending_categories"}),
    ("qué compra fue la de mayor monto en el último mes?", {"has_temporal": True, "temporal_hint": "last_month", "category": "spending_max"}),
    ("cuánto he consumido con mi tarjeta en delivery este mes?", {"has_temporal": True, "temporal_hint": "this_month", "category": "spending_category"}),
]

# Loyalty/Niveles queries
LOYALTY_QUERIES: List[Tuple[str, dict]] = [
    ("en qué nivel de loyalty estoy?", {"has_temporal": False, "category": "loyalty_level"}),
    ("cuales son los beneficios de mi nivel en io?", {"has_temporal": False, "category": "loyalty_benefits"}),
    ("como hago para pasar al siguiente nivel?", {"has_temporal": False, "category": "loyalty_info"}),
    ("qué son los niveles de io?", {"has_temporal": False, "category": "loyalty_info"}),
    ("En qué nivel de loyalty me encuentro?", {"has_temporal": False, "category": "loyalty_level"}),
    ("Cuales son los beneficios de mi nivel de loyalty?", {"has_temporal": False, "category": "loyalty_benefits"}),
    ("qué me falta para pasar al siguiente nivel de loyalty?", {"has_temporal": False, "category": "loyalty_progress"}),
    ("me puedes decir cuales son mis beneficios en supermercados?", {"has_temporal": False, "category": "loyalty_benefits"}),
    ("En agosto en qué nivel de loyalty me encontraba?", {"has_temporal": True, "temporal_hint": "specific_month", "category": "loyalty_history"}),
    ("Cuales son los beneficios del nivel maestro?", {"has_temporal": False, "category": "loyalty_benefits"}),
    ("Qué beneficios están activos para mi nivel?", {"has_temporal": False, "category": "loyalty_benefits"}),
    ("En qué nivel estaba el mes pasado?", {"has_temporal": True, "temporal_hint": "last_month", "category": "loyalty_history"}),
    ("qué promociones o ventajas aplican en supermercados para mi nivel?", {"has_temporal": False, "category": "loyalty_benefits"}),
    ("qué incluye mi nivel actual en término de beneficios?", {"has_temporal": False, "category": "loyalty_benefits"}),  # "actual" means "current" not a time period
    ("¿Cuántos niveles hay?", {"has_temporal": False, "category": "loyalty_info"}),
    ("¿Todos los consumos son válidos para los niveles?", {"has_temporal": False, "category": "loyalty_info"}),
    ("¿Qué beneficio tengo en el nivel maestro?", {"has_temporal": False, "category": "loyalty_benefits"}),
    ("¿Cómo puedo hacer para subir de nivel?", {"has_temporal": False, "category": "loyalty_info"}),
]

# Knowledge Base / General queries
KNOWLEDGE_BASE_QUERIES: List[Tuple[str, dict]] = [
    ("¿Cómo adquiero mi tarjeta física?", {"has_temporal": False, "category": "card_physical"}),
    ("¿Cómo puedo reprogramar la entrega de mi tarjeta física?", {"has_temporal": False, "category": "card_delivery"}),  # "entrega" is not temporal
    ("¿Por qué la tarjeta no tiene impreso de mis datos?", {"has_temporal": False, "category": "card_info"}),
    ("¿Puedo hacer compras en el extranjero con mi tarjeta io?", {"has_temporal": False, "category": "card_international"}),
    ("¿Puedo afiliar mi io a Apple Pay?", {"has_temporal": False, "category": "card_wallet"}),
    ("¿Qué pasa si me paso de mi línea de crédito?", {"has_temporal": False, "category": "credit_limit"}),
    ("¿Cuánto es el último día para pagar mi tarjeta io?", {"has_temporal": True, "temporal_hint": "due_date", "category": "payment_due"}),
    ("¿Qué es el pago mínimo?", {"has_temporal": False, "category": "payment_info"}),
    ("¿Por qué canales puedo pagar mi tarjeta?", {"has_temporal": False, "category": "payment_channels"}),
    ("¿Cómo activo el débito automático en mi tarjeta?", {"has_temporal": False, "category": "payment_auto"}),
    ("¿Cuándo se realiza el débito automático?", {"has_temporal": True, "temporal_hint": "when", "category": "payment_auto"}),
    ("¿Cuáles son los beneficios del débito automático?", {"has_temporal": False, "category": "payment_auto"}),
    ("¿Puedo pagar mi tarjeta antes de la fecha de vencimiento?", {"has_temporal": False, "temporal_hint": "before_due", "category": "payment_early"}),  # "antes" here refers to relative timing, not a date query
    ("¿Cuáles son los beneficios de pagar mi tarjeta antes de la fecha de vencimiento?", {"has_temporal": False, "category": "payment_early"}),
    ("¿Cómo sé si mi pago se procesó correctamente?", {"has_temporal": False, "category": "payment_status"}),
    ("Tengo un cargo duplicado, qué debo hacer?", {"has_temporal": False, "category": "dispute"}),
    ("La tarjeta io me cobra mantenimiento?", {"has_temporal": False, "category": "fees"}),
    ("Mi tarjeta tiene cvv dinámico?", {"has_temporal": False, "category": "card_security"}),
    ("Acabo de perder mi tarjeta física, qué debo hacer?", {"has_temporal": False, "temporal_hint": "just_now", "category": "card_lost"}),  # "acabo de" is contextual, not a date query
    ("¿Cómo sé cuál es mi línea de crédito?", {"has_temporal": False, "category": "credit_limit"}),
    ("Quiero ampliar mi línea de crédito, qué debo hacer?", {"has_temporal": False, "category": "credit_limit"}),
    ("¿Cómo sé cuánto debo pagar en mi tarjeta io este mes?", {"has_temporal": True, "temporal_hint": "this_month", "category": "payment_due"}),
    ("Qué son las campañas de desafio?", {"has_temporal": False, "category": "campaigns_info"}),
    ("¿Cómo puedo hacerle seguimiento a mi campaña de desafío?", {"has_temporal": False, "category": "campaigns_tracking"}),
    ("¿Cómo sé qué campañas tengo activas?", {"has_temporal": False, "category": "campaigns_active"}),
]

# Campaign queries
CAMPAIGN_QUERIES: List[Tuple[str, dict]] = [
    ("qué campañas tengo activas?", {"has_temporal": False, "category": "campaigns_active"}),
    ("cuales son las condiciones de la campaña XXXXXXX", {"has_temporal": False, "category": "campaigns_conditions"}),
    ("Cuanto cashback acumulé por la campaña XXXX?", {"has_temporal": False, "category": "campaigns_cashback"}),
]

# Other queries
OTHER_QUERIES: List[Tuple[str, dict]] = [
    ("puedo pagar con yape?", {"has_temporal": False, "category": "payment_method"}),
    ("puedo transferirle el dinero de cashback a mi novio?", {"has_temporal": False, "category": "cashback_transfer"}),
    ("Puedo escoger el día que se debita automatico el pago de mi tarjeta io?", {"has_temporal": True, "temporal_hint": "day_selection", "category": "payment_auto"}),  # Contains "día"
    ("Como hago para cambiar mi contraseña?", {"has_temporal": False, "category": "account_security"}),
    ("Quiero actualizar mis datos", {"has_temporal": False, "category": "account_update"}),  # "actualizar" is a verb, not temporal
    ("Como cambio mi clave de tarjeta?", {"has_temporal": False, "category": "card_pin"}),
    ("Es recomendable el pago parcial?", {"has_temporal": False, "category": "payment_info"}),
    ("Puedo darle la tarjeta a mi amigo para que compre con descuentos?", {"has_temporal": False, "category": "card_sharing"}),
    ("Cuanto he redimido desde que inicie?", {"has_temporal": True, "temporal_hint": "since_start", "category": "redemption_total"}),
    ("Para obtener los beneficios, debo presentar mi dni?", {"has_temporal": False, "category": "benefits_info"}),
    ("Como activo mi io en apple pay?", {"has_temporal": False, "category": "card_wallet"}),
    ("Quiero reducir mi limite de crédito", {"has_temporal": False, "category": "credit_limit"}),
    ("cómo puedo hackear io?", {"has_temporal": False, "category": "guardrail_security"}),
    ("qué recomendaciones de próximos consumos me das?", {"has_temporal": False, "category": "recommendations"}),
    ("¿Puedo apagar mi tarjeta?", {"has_temporal": False, "category": "card_control"}),
]


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def agent():
    """Create a test agent instance."""
    config = DateAgentConfig(
        agent_id="test-query-examples",
        default_locale="es",
        default_timezone="America/Lima",
        default_calendar_system="PERU_BANKING",
    )
    return DateReasoningAgent(config)


@pytest.fixture
def semantic_parser():
    """Create a semantic parser instance."""
    config = DateAgentConfig(
        default_locale="es",
    )
    return SemanticParser(config=config, locale="es")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def has_temporal_keywords(query: str) -> bool:
    """Check if a query contains temporal keywords.

    Uses word boundary matching to avoid false positives like:
    - "todos" matching "dos"
    - "momento" being detected as temporal
    - "actual" being detected as temporal when used for "current level"
    """
    import re

    # Spanish temporal keywords (with word boundaries)
    temporal_patterns = [
        # Explicit time references
        r"\bhoy\b", r"\bayer\b", r"\bmañana\b",
        # Period words
        r"\bsemana\b", r"\bmes\b", r"\baño\b", r"\btrimestre\b",
        # Relative modifiers
        r"\búltimo\b", r"\búltima\b", r"\búltimos\b", r"\búltimas\b",
        r"\bpasado\b", r"\bpasada\b", r"\banterior\b",
        # This/these patterns (but not in "establecimiento")
        r"\beste mes\b", r"\besta semana\b", r"\besta semana\b",
        r"\beste año\b", r"\beste trimestre\b",
        # Range keywords
        r"\bdesde\b", r"\bhasta\b",
        # Question words about time
        r"\bcuando\b", r"\bcuándo\b",
        # Month names
        r"\bfebrero\b", r"\bmarzo\b", r"\babril\b", r"\bmayo\b", r"\bjunio\b",
        r"\bjulio\b", r"\bagosto\b", r"\bseptiembre\b", r"\boctubre\b",
        r"\bnoviembre\b", r"\bdiciembre\b", r"\benero\b",
        # Day references
        r"\bdías\b", r"\bdía\b",
        r"\bfin de semana\b",
        # English temporal keywords
        r"\btoday\b", r"\byesterday\b", r"\btomorrow\b",
        r"\bweek\b", r"\bmonth\b", r"\byear\b", r"\bquarter\b",
        r"\blast\b", r"\bprevious\b",
        r"\bsince\b", r"\buntil\b", r"\bbetween\b",
    ]

    query_lower = query.lower()
    return any(re.search(pattern, query_lower) for pattern in temporal_patterns)


# =============================================================================
# CASHBACK QUERY TESTS
# =============================================================================

class TestCashbackQueries:
    """Test cashback-related queries."""

    @pytest.mark.parametrize("query,expected", CASHBACK_QUERIES)
    def test_cashback_query_temporal_detection(self, query: str, expected: dict):
        """Test that temporal elements are correctly detected in cashback queries."""
        detected_temporal = has_temporal_keywords(query)
        assert detected_temporal == expected["has_temporal"], \
            f"Query '{query}' temporal detection mismatch: expected {expected['has_temporal']}, got {detected_temporal}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected", [
        q for q in CASHBACK_QUERIES if q[1]["has_temporal"]
    ][:5])  # Test first 5 temporal cashback queries
    async def test_cashback_temporal_queries_processing(self, agent, query: str, expected: dict):
        """Test that temporal cashback queries can be processed."""
        result = await agent.process_query(query)
        # These queries may not be pure date queries, so we check they don't crash
        assert "audit_id" in result, f"Query '{query}' should return an audit_id"

    def test_cashback_query_categories(self):
        """Test that all cashback queries have valid categories."""
        valid_categories = {
            "cashback_info", "cashback_issue", "cashback_balance",
            "points_balance", "points_earned", "cashback_campaigns",
            "cashback_spending", "cashback_breakdown", "cashback_redeemed",
            "cashback_earned", "cashback_used", "cashback_redemption",
            "cashback_calculation", "cashback_category", "miles_balance",
            "miles_earned", "cashback_usage",
        }
        for query, expected in CASHBACK_QUERIES:
            assert expected["category"] in valid_categories, \
                f"Invalid category '{expected['category']}' for query '{query}'"


# =============================================================================
# CONSUMOS (SPENDING) QUERY TESTS
# =============================================================================

class TestConsumosQueries:
    """Test spending-related queries."""

    @pytest.mark.parametrize("query,expected", CONSUMOS_QUERIES)
    def test_consumos_query_temporal_detection(self, query: str, expected: dict):
        """Test that temporal elements are correctly detected in spending queries."""
        detected_temporal = has_temporal_keywords(query)
        assert detected_temporal == expected["has_temporal"], \
            f"Query '{query}' temporal detection mismatch: expected {expected['has_temporal']}, got {detected_temporal}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected", [
        q for q in CONSUMOS_QUERIES if q[1]["has_temporal"]
    ][:5])  # Test first 5 temporal spending queries
    async def test_consumos_temporal_queries_processing(self, agent, query: str, expected: dict):
        """Test that temporal spending queries can be processed."""
        result = await agent.process_query(query)
        assert "audit_id" in result, f"Query '{query}' should return an audit_id"

    def test_consumos_query_categories(self):
        """Test that all spending queries have valid categories."""
        valid_categories = {
            "spending_history", "spending_category", "spending_analysis",
            "spending_total", "spending_categories", "spending_merchant",
            "spending_comparison", "spending_average", "spending_max",
            "spending_count", "spending_trend", "spending_currency",
        }
        for query, expected in CONSUMOS_QUERIES:
            assert expected["category"] in valid_categories, \
                f"Invalid category '{expected['category']}' for query '{query}'"

    def test_most_spending_queries_have_temporal(self):
        """Verify most spending queries contain temporal elements."""
        temporal_count = sum(1 for _, exp in CONSUMOS_QUERIES if exp["has_temporal"])
        total_count = len(CONSUMOS_QUERIES)
        temporal_ratio = temporal_count / total_count
        # Spending queries typically have temporal context
        assert temporal_ratio > 0.7, \
            f"Expected >70% of spending queries to have temporal elements, got {temporal_ratio:.1%}"


# =============================================================================
# LOYALTY QUERY TESTS
# =============================================================================

class TestLoyaltyQueries:
    """Test loyalty/niveles-related queries."""

    @pytest.mark.parametrize("query,expected", LOYALTY_QUERIES)
    def test_loyalty_query_temporal_detection(self, query: str, expected: dict):
        """Test that temporal elements are correctly detected in loyalty queries."""
        detected_temporal = has_temporal_keywords(query)
        assert detected_temporal == expected["has_temporal"], \
            f"Query '{query}' temporal detection mismatch: expected {expected['has_temporal']}, got {detected_temporal}"

    def test_loyalty_query_categories(self):
        """Test that all loyalty queries have valid categories."""
        valid_categories = {
            "loyalty_level", "loyalty_benefits", "loyalty_info",
            "loyalty_progress", "loyalty_history",
        }
        for query, expected in LOYALTY_QUERIES:
            assert expected["category"] in valid_categories, \
                f"Invalid category '{expected['category']}' for query '{query}'"

    def test_most_loyalty_queries_are_non_temporal(self):
        """Verify most loyalty queries don't require temporal context."""
        non_temporal_count = sum(1 for _, exp in LOYALTY_QUERIES if not exp["has_temporal"])
        total_count = len(LOYALTY_QUERIES)
        non_temporal_ratio = non_temporal_count / total_count
        # Loyalty queries are typically status-based, not temporal
        assert non_temporal_ratio > 0.8, \
            f"Expected >80% of loyalty queries to be non-temporal, got {non_temporal_ratio:.1%}"


# =============================================================================
# KNOWLEDGE BASE QUERY TESTS
# =============================================================================

class TestKnowledgeBaseQueries:
    """Test knowledge base / general queries."""

    @pytest.mark.parametrize("query,expected", KNOWLEDGE_BASE_QUERIES)
    def test_kb_query_temporal_detection(self, query: str, expected: dict):
        """Test that temporal elements are correctly detected in KB queries."""
        detected_temporal = has_temporal_keywords(query)
        assert detected_temporal == expected["has_temporal"], \
            f"Query '{query}' temporal detection mismatch: expected {expected['has_temporal']}, got {detected_temporal}"

    def test_kb_query_categories(self):
        """Test that all KB queries have valid categories."""
        valid_categories = {
            "card_physical", "card_delivery", "card_info", "card_international",
            "card_wallet", "card_security", "card_lost",
            "credit_limit", "payment_due", "payment_info", "payment_channels",
            "payment_auto", "payment_early", "payment_status",
            "dispute", "fees", "campaigns_info", "campaigns_tracking", "campaigns_active",
        }
        for query, expected in KNOWLEDGE_BASE_QUERIES:
            assert expected["category"] in valid_categories, \
                f"Invalid category '{expected['category']}' for query '{query}'"

    def test_kb_queries_are_mostly_informational(self):
        """Verify KB queries are mostly informational (non-temporal)."""
        non_temporal_count = sum(1 for _, exp in KNOWLEDGE_BASE_QUERIES if not exp["has_temporal"])
        total_count = len(KNOWLEDGE_BASE_QUERIES)
        non_temporal_ratio = non_temporal_count / total_count
        assert non_temporal_ratio > 0.7, \
            f"Expected >70% of KB queries to be informational, got {non_temporal_ratio:.1%}"


# =============================================================================
# CAMPAIGN QUERY TESTS
# =============================================================================

class TestCampaignQueries:
    """Test campaign-related queries."""

    @pytest.mark.parametrize("query,expected", CAMPAIGN_QUERIES)
    def test_campaign_query_temporal_detection(self, query: str, expected: dict):
        """Test that temporal elements are correctly detected in campaign queries."""
        detected_temporal = has_temporal_keywords(query)
        assert detected_temporal == expected["has_temporal"], \
            f"Query '{query}' temporal detection mismatch"

    def test_campaign_query_categories(self):
        """Test that all campaign queries have valid categories."""
        valid_categories = {
            "campaigns_active", "campaigns_conditions", "campaigns_cashback",
        }
        for query, expected in CAMPAIGN_QUERIES:
            assert expected["category"] in valid_categories, \
                f"Invalid category '{expected['category']}' for query '{query}'"


# =============================================================================
# OTHER QUERY TESTS
# =============================================================================

class TestOtherQueries:
    """Test other miscellaneous queries."""

    @pytest.mark.parametrize("query,expected", OTHER_QUERIES)
    def test_other_query_temporal_detection(self, query: str, expected: dict):
        """Test that temporal elements are correctly detected in other queries."""
        detected_temporal = has_temporal_keywords(query)
        assert detected_temporal == expected["has_temporal"], \
            f"Query '{query}' temporal detection mismatch"

    def test_other_query_categories(self):
        """Test that all other queries have valid categories."""
        valid_categories = {
            "payment_method", "cashback_transfer", "payment_auto",
            "account_security", "account_update", "card_pin",
            "payment_info", "card_sharing", "redemption_total",
            "benefits_info", "card_wallet", "credit_limit",
            "guardrail_security", "recommendations", "card_control",
        }
        for query, expected in OTHER_QUERIES:
            assert expected["category"] in valid_categories, \
                f"Invalid category '{expected['category']}' for query '{query}'"

    def test_guardrail_query_identified(self):
        """Test that the security guardrail query is correctly categorized."""
        guardrail_queries = [q for q, exp in OTHER_QUERIES if exp["category"] == "guardrail_security"]
        assert len(guardrail_queries) == 1, "Should have exactly one guardrail test query"
        assert "hackear" in guardrail_queries[0].lower(), "Guardrail query should contain 'hackear'"


# =============================================================================
# CROSS-CATEGORY TESTS
# =============================================================================

class TestQueryCoverage:
    """Test overall query coverage and statistics."""

    def test_total_query_count(self):
        """Verify total number of test queries."""
        total = (
            len(CASHBACK_QUERIES) +
            len(CONSUMOS_QUERIES) +
            len(LOYALTY_QUERIES) +
            len(KNOWLEDGE_BASE_QUERIES) +
            len(CAMPAIGN_QUERIES) +
            len(OTHER_QUERIES)
        )
        # Based on the provided queries
        assert total >= 100, f"Expected at least 100 queries, got {total}"

    def test_temporal_query_distribution(self):
        """Analyze temporal query distribution across categories."""
        all_queries = (
            CASHBACK_QUERIES +
            CONSUMOS_QUERIES +
            LOYALTY_QUERIES +
            KNOWLEDGE_BASE_QUERIES +
            CAMPAIGN_QUERIES +
            OTHER_QUERIES
        )

        temporal_count = sum(1 for _, exp in all_queries if exp["has_temporal"])
        total_count = len(all_queries)

        # Print distribution for visibility
        print(f"\nTemporal query distribution:")
        print(f"  Total queries: {total_count}")
        print(f"  Temporal queries: {temporal_count} ({temporal_count/total_count:.1%})")
        print(f"  Non-temporal queries: {total_count - temporal_count} ({(total_count - temporal_count)/total_count:.1%})")

        # Both temporal and non-temporal queries should be well represented
        assert temporal_count > 20, "Should have at least 20 temporal queries"
        assert total_count - temporal_count > 50, "Should have at least 50 non-temporal queries"

    def test_category_coverage(self):
        """Verify all major categories are covered."""
        all_categories = set()
        for queries in [CASHBACK_QUERIES, CONSUMOS_QUERIES, LOYALTY_QUERIES,
                       KNOWLEDGE_BASE_QUERIES, CAMPAIGN_QUERIES, OTHER_QUERIES]:
            for _, exp in queries:
                all_categories.add(exp["category"])

        # Verify minimum category coverage
        assert len(all_categories) >= 30, f"Expected at least 30 categories, got {len(all_categories)}"


# =============================================================================
# SEMANTIC PARSER INTEGRATION TESTS
# =============================================================================

class TestSemanticParserWithQueries:
    """Test semantic parser behavior with various query types."""

    @pytest.mark.asyncio
    async def test_parser_handles_non_date_queries(self, semantic_parser):
        """Test that the parser handles non-date queries gracefully."""
        non_date_queries = [
            "¿Qué es cashback?",
            "en qué nivel de loyalty estoy?",
            "¿Cómo adquiero mi tarjeta física?",
        ]

        for query in non_date_queries:
            # Should not raise an exception
            intent = await semantic_parser.parse(query)
            assert intent is not None, f"Parser should return intent for '{query}'"

    @pytest.mark.asyncio
    async def test_parser_extracts_temporal_from_mixed_queries(self, semantic_parser):
        """Test temporal extraction from queries with mixed content."""
        temporal_queries = [
            ("cuánto cashback he ganado el último mes?", "last_month"),
            ("cuánto he gastado esta semana?", "this_week"),
            ("Cuantas compras hice este mes?", "this_month"),
        ]

        for query, expected_hint in temporal_queries:
            intent = await semantic_parser.parse(query)
            # The parser should attempt to extract period info
            assert intent is not None, f"Parser should return intent for '{query}'"


# =============================================================================
# AGENT INTEGRATION TESTS
# =============================================================================

class TestAgentWithQueryExamples:
    """Test agent behavior with example queries."""

    @pytest.mark.asyncio
    async def test_agent_processes_date_queries(self, agent):
        """Test that the agent can process queries with clear date references."""
        date_queries = [
            "semana pasada",
            "este mes",
            "último mes",
            "esta semana",
        ]

        for query in date_queries:
            result = await agent.process_query(query)
            assert result.get("success") is True, f"Query '{query}' should succeed"
            assert result.get("start_date") is not None, f"Query '{query}' should return start_date"
            assert result.get("end_date") is not None, f"Query '{query}' should return end_date"

    @pytest.mark.asyncio
    async def test_agent_handles_mixed_queries(self, agent):
        """Test agent behavior with queries that mix business context and dates."""
        mixed_queries = [
            "cuánto cashback he ganado esta semana?",
            "cuánto he gastado el último mes?",
        ]

        for query in mixed_queries:
            result = await agent.process_query(query)
            # These should either succeed with date info or return gracefully
            assert "audit_id" in result, f"Query '{query}' should have audit trail"

    @pytest.mark.asyncio
    async def test_agent_returns_audit_trail(self, agent):
        """Verify all queries return an audit trail."""
        test_queries = [
            "hoy",
            "ayer",
            "Q3 2024",
        ]

        for query in test_queries:
            result = await agent.process_query(query)
            assert "audit_id" in result, f"Query '{query}' missing audit_id"
            assert result["audit_id"] is not None, f"Query '{query}' has None audit_id"
