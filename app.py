"""Gradio Frontend for the Date Reasoning Agent.

A modern, interactive UI for testing the Date Reasoning Agent.

Usage:
    # Make sure the backend server is running first:
    python server.py

    # Then run the Gradio frontend:
    python app.py
"""

import httpx
import gradio as gr
import json
import os
from datetime import datetime
from typing import Optional, List, Tuple

# Backend server URL (internal communication within container)
# In Cloud Run: backend runs on internal port 8000, Gradio runs on public port 8080
BACKEND_URL = os.getenv("DATE_AGENT_BACKEND_URL", "http://localhost:8000")


# =============================================================================
# QUERY EXAMPLES BY CATEGORY
# =============================================================================

# Only queries with temporal/date intents
CASHBACK_QUERIES = [
    # Simple temporal
    "cuánto cashback he ganado hasta el momento?",
    "cuantos puntos he ganado la última semana?",
    "cuánto cashback por campañas he ganado este mes?",
    "cuánto cashback he redimido el último mes?",
    "¿Cuánto cashback he ganado con mi tarjeta io en el último mes?",
    "Cuánto cashback generé esta semana?",
    "Cuánto cashback he usado en lo que va del año?",
    "cuál ha sido mi última redención?",
    "qué monto de cashback acumulé esta semana?",
    "Cuantas millas gané el último mes por delivery?",
    "cuánto cashback he ganado de febrero hasta hoy?",
    "cuando fue la última vez que usé cashback?",
    # Complex temporal - comparisons
    "gané más cashback este mes que el mes pasado?",
    "comparar mi cashback del Q3 2024 vs Q2 2024",
    "cuánto cashback acumulé entre enero y marzo de este año?",
    # Complex temporal - specific periods
    "cuánto cashback gané en los últimos 3 meses excluyendo feriados?",
    "qué día de la semana pasada generé más cashback?",
    "cuántos puntos acumulé del 15 al 30 del mes pasado?",
    "cuál fue mi mejor mes en cashback este año?",
    # Complex temporal - relative + absolute
    "cuánto cashback he ganado desde julio 2024 hasta hoy?",
    "dame el cashback acumulado en el trimestre anterior al actual",
    "cuántas millas gané la semana antepasada por compras en supermercados?",
]

# Only queries with temporal/date intents
CONSUMOS_QUERIES = [
    # Simple temporal
    "¿Cuáles han sido mis últimos consumos?",
    "quiero saber cuanto he gastado en restaurantes en el último mes",
    "Cuanto he consumido en los últimos 15 días?",
    "en qué categorías he consumido más en el último mes?",
    "cuánto he gastado en todo lo que lleva del año con mi tc?",
    "en qué comercio gasté más en el último mes?",
    "cuánto gasté en delivery este último mes?",
    "Gasté más este mes que el anterior?",
    "cuál fue mi compra más alta del último mes?",
    "cuántas compras hice este mes?",
    "cuánto gasté el fin de semana pasado?",
    "cuánto fue mi gasto promedio por día de este mes?",
    "cuánto he consumido en soles vs dólares este mes?",
    "cuánto he consumido con mi tarjeta en los últimos 7 días?",
    "cuál ha sido mi gasto total en las últimas dos semanas?",
    "cuales fueron las categorias de mayor gasto el mes pasado?",
    "qué compra fue la de mayor monto en el último mes?",
    "cuánto he consumido con mi tarjeta en delivery este mes?",
    # Complex temporal - comparisons
    "mi gasto en restaurantes subió o bajó comparando este mes con el anterior?",
    "cuál fue la diferencia de consumo entre Q1 y Q2 de 2024?",
    "en qué trimestre del año pasado gasté más?",
    # Complex temporal - specific periods
    "cuánto gasté en los últimos 5 días hábiles?",
    "dame mis consumos del primer día hábil de cada mes de este año",
    "cuánto gasté cada semana del mes pasado?",
    "cuál fue mi gasto total en días de feriado del 2024?",
    # Complex temporal - ranges and business days
    "cuántos días hábiles de este mes he realizado compras?",
    "cuánto he gastado en promedio por día hábil este trimestre?",
    "dame el total de consumos entre el 1 y 15 de enero 2025",
    "cuánto gasté la última quincena del mes pasado?",
    # Complex temporal - patterns
    "cuánto gasto en promedio los fines de semana de este mes?",
    "mis gastos de los lunes del último mes",
    "cuál ha sido mi consumo más alto en un solo día desde que tengo la tarjeta?",
]

# Only queries with temporal/date intents
LOYALTY_QUERIES = [
    # Simple temporal
    "En agosto en qué nivel de loyalty me encontraba?",
    "En qué nivel estaba el mes pasado?",
    # Complex temporal
    "cuánto tiempo llevo en mi nivel actual de loyalty?",
    "cuándo fue la última vez que subí de nivel?",
    "en qué mes del año pasado alcancé el nivel oro?",
    "cuántos meses me faltan para subir de nivel al ritmo actual?",
    "cuál era mi nivel en el Q3 2024?",
    "he mantenido el mismo nivel durante los últimos 3 meses?",
    "desde cuándo estoy en el nivel actual?",
]

# Only queries with temporal/date intents
KNOWLEDGE_BASE_QUERIES = [
    # Simple temporal
    "¿Cuándo es el último día para pagar mi tarjeta io?",
    "¿Cuándo se realiza el débito automático?",
    "¿Cuánto debo pagar en mi tarjeta io este mes?",
    # Complex temporal
    "cuántos días faltan para mi fecha de corte?",
    "cuándo fue mi último pago de tarjeta?",
    "cuántos días tengo para pagar antes de que me cobren intereses?",
    "cuál fue la fecha de mi último estado de cuenta?",
    "cuándo vence el pago mínimo de este mes?",
    "hace cuánto tiempo que no pago el total de mi tarjeta?",
    "cuántos días hábiles quedan para pagar sin mora?",
]

# Only queries with temporal/date intents
CAMPAIGN_QUERIES = [
    # Simple temporal
    "qué campañas tengo activas este mes?",
    "cuánto cashback acumulé por la campaña del mes pasado?",
    # Complex temporal
    "cuándo termina la campaña actual de cashback doble?",
    "qué campañas tuve activas en el Q4 2024?",
    "cuántos días faltan para que termine mi campaña de desafío?",
    "cuánto cashback extra gané por campañas en los últimos 3 meses?",
    "hubo alguna campaña activa la semana pasada que me perdí?",
    "cuál fue la campaña que más cashback me dio este año?",
    "cuántas campañas he completado desde que tengo la tarjeta?",
]

# Only queries with temporal/date intents
OTHER_QUERIES = [
    # Simple temporal
    "Cuanto he redimido desde que inicié?",
    "cuánto he gastado desde el inicio del año?",
    # Complex temporal
    "cuántos meses llevo usando mi tarjeta io?",
    "cuándo fue mi primera compra con la tarjeta?",
    "hace cuánto tiempo que no uso mi tarjeta física?",
    "cuántas transacciones he hecho desde que activé la tarjeta?",
    "en qué fecha cumple un año mi tarjeta?",
    "cuántos días han pasado desde mi última transacción?",
]

DATE_QUERIES = [
    "hoy",
    "ayer",
    "semana pasada",
    "semana antepasada",
    "mes anterior",
    "este mes",
    "trimestre pasado",
    "este año",
    "Q1 2024",
    "Q2 2024",
    "Q3 2024",
    "Q4 2024",
    "julio 2024",
    "feriados julio 2024",
    "last week",
    "last month",
    "last quarter",
    "ytd",
    "today",
    "yesterday",
]

# Build category choices for dropdown
def build_example_choices() -> List[Tuple[str, str]]:
    """Build list of (display_label, query) tuples for dropdown."""
    choices = []

    # Add a placeholder
    choices.append(("-- Seleccionar ejemplo --", ""))

    # Date queries
    choices.append(("═══ 📅 FECHAS / DATES ═══", ""))
    for q in DATE_QUERIES:
        choices.append((f"📅 {q}", q))

    # Cashback queries
    choices.append(("═══ 💰 CASHBACK ═══", ""))
    for q in CASHBACK_QUERIES:
        label = q[:60] + "..." if len(q) > 60 else q
        choices.append((f"💰 {label}", q))

    # Consumos queries
    choices.append(("═══ 🛒 CONSUMOS ═══", ""))
    for q in CONSUMOS_QUERIES:
        label = q[:60] + "..." if len(q) > 60 else q
        choices.append((f"🛒 {label}", q))

    # Loyalty queries
    choices.append(("═══ ⭐ LOYALTY / NIVELES ═══", ""))
    for q in LOYALTY_QUERIES:
        label = q[:60] + "..." if len(q) > 60 else q
        choices.append((f"⭐ {label}", q))

    # Knowledge base queries
    choices.append(("═══ 📚 KNOWLEDGE BASE ═══", ""))
    for q in KNOWLEDGE_BASE_QUERIES:
        label = q[:60] + "..." if len(q) > 60 else q
        choices.append((f"📚 {label}", q))

    # Campaign queries
    choices.append(("═══ 🎯 CAMPAÑAS ═══", ""))
    for q in CAMPAIGN_QUERIES:
        label = q[:60] + "..." if len(q) > 60 else q
        choices.append((f"🎯 {label}", q))

    # Other queries
    choices.append(("═══ 🔧 OTROS ═══", ""))
    for q in OTHER_QUERIES:
        label = q[:60] + "..." if len(q) > 60 else q
        choices.append((f"🔧 {label}", q))

    return choices


EXAMPLE_CHOICES = build_example_choices()


# =============================================================================
# BACKEND COMMUNICATION
# =============================================================================

async def check_backend_health():
    """Check if backend is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None


async def process_query(
    query: str,
    timezone: str = "America/Lima",
) -> tuple[str, str, str]:
    """Send query to backend and format the response.

    Returns:
        Tuple of (main_result, details, raw_json)
    """
    if not query or not query.strip():
        return (
            "⚠️ Please enter a query",
            "",
            "",
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/query",
                json={
                    "query": query.strip(),
                    "timezone": timezone,
                },
            )

            if response.status_code != 200:
                return (
                    f"❌ Server error: {response.status_code}",
                    "",
                    response.text,
                )

            result = response.json()

            # Format main result
            if result.get("success"):
                main_result = format_success_result(result)
                details = format_details(result)
            else:
                main_result = f"❌ Error: {result.get('error', 'Unknown error')}"
                details = f"Error Type: {result.get('error_type', 'Unknown')}"

            # Raw JSON
            raw_json = json.dumps(result, indent=2, ensure_ascii=False)

            return main_result, details, raw_json

    except httpx.ConnectError:
        return (
            "❌ Cannot connect to backend server.\n\nMake sure to run: `python server.py` first",
            "",
            "",
        )
    except Exception as e:
        return (
            f"❌ Error: {str(e)}",
            "",
            "",
        )


def format_success_result(result: dict) -> str:
    """Format a successful result for display."""
    lines = ["✅ **Query Processed Successfully**", ""]

    # Original query
    if result.get("query"):
        lines.append(f"🔍 **Query:** {result['query']}")
        lines.append("")

    # Main date range
    if result.get("start_date") and result.get("end_date"):
        start = result["start_date"]
        end = result["end_date"]
        lines.append(f"📅 **Date Range:** `{start}` → `{end}`")

        if result.get("calendar_days"):
            lines.append(f"📊 **Calendar Days:** {result['calendar_days']}")

        if result.get("business_days"):
            lines.append(f"💼 **Business Days:** {result['business_days']}")
    elif result.get("start_date"):
        lines.append(f"📅 **Date:** `{result['start_date']}`")

    # Period type
    if result.get("period_type"):
        lines.append(f"🏷️ **Period Type:** {result['period_type']}")

    # Description
    if result.get("description"):
        lines.append(f"📝 **Description:** {result['description']}")

    # Holidays
    if result.get("holidays"):
        lines.append("")
        lines.append(f"🎉 **Holidays ({len(result['holidays'])}):**")
        for h in result["holidays"][:5]:  # Show max 5
            date = h.get("date", "")
            name = h.get("name_localized") or h.get("name", "")
            lines.append(f"  • {date}: {name}")
        if len(result["holidays"]) > 5:
            lines.append(f"  • ... and {len(result['holidays']) - 5} more")

    return "\n".join(lines)


def format_details(result: dict) -> str:
    """Format additional details."""
    lines = []

    # Reference info
    if result.get("reference_date"):
        lines.append(f"🕐 Reference Date: {result['reference_date']}")
    if result.get("timezone"):
        lines.append(f"🌍 Timezone: {result['timezone']}")

    # Computation trace
    trace = result.get("computation_trace", {})
    if trace:
        lines.append("")
        lines.append("**Computation Trace:**")
        if trace.get("intent_type"):
            lines.append(f"  • Intent: {trace['intent_type']}")
        if trace.get("confidence"):
            lines.append(f"  • Confidence: {trace['confidence']:.2%}")
        if trace.get("plan_steps"):
            lines.append(f"  • Steps: {trace['plan_steps']}")
        if trace.get("is_compositional"):
            lines.append("  • Compositional: Yes")

    # Audit ID
    if result.get("audit_id"):
        lines.append("")
        lines.append(f"🔍 Audit ID: `{result['audit_id'][:8]}...`")

    return "\n".join(lines)


async def get_holidays_for_display(calendar: str, year: int, month: Optional[int] = None):
    """Fetch holidays and format for display."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "calendar_system": calendar,
                "year": year,
            }
            if month:
                payload["month"] = month

            response = await client.post(f"{BACKEND_URL}/holidays", json=payload)

            if response.status_code != 200:
                return f"Error: {response.text}"

            result = response.json()
            holidays = result.get("holidays", [])

            if not holidays:
                return "No holidays found for the selected period."

            lines = [f"**{calendar} Holidays - {year}**", ""]
            lines.append("| Date | Holiday |")
            lines.append("|------|---------|")

            for h in holidays:
                date = h.get("date", "")
                name = h.get("name_localized") or h.get("name", "")
                lines.append(f"| {date} | {name} |")

            return "\n".join(lines)

    except httpx.ConnectError:
        return "❌ Cannot connect to backend server."
    except Exception as e:
        return f"Error: {str(e)}"


def on_example_select(choice):
    """Handle example selection from dropdown."""
    # Find the query for this choice
    for label, query in EXAMPLE_CHOICES:
        if label == choice:
            return query if query else ""
    return ""


# =============================================================================
# UI CREATION
# =============================================================================

def create_ui():
    """Create the Gradio interface."""

    # Count total examples
    total_examples = (
        len(DATE_QUERIES) + len(CASHBACK_QUERIES) + len(CONSUMOS_QUERIES) +
        len(LOYALTY_QUERIES) + len(KNOWLEDGE_BASE_QUERIES) +
        len(CAMPAIGN_QUERIES) + len(OTHER_QUERIES)
    )

    with gr.Blocks(
        title="Date Reasoning Agent",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="gray",
        ),
        css="""
        .result-box { font-family: monospace; }
        .example-btn { margin: 2px !important; }
        .category-header { font-weight: bold; background-color: #f0f0f0; }
        """,
    ) as demo:
        gr.Markdown(
            f"""
            # 📅 High-Precision Date Reasoning Agent

            **Financial Operations Date Calculator** - Peru Banking Calendar with Spanish/English Support

            Enter a natural language query or select from **{total_examples} example queries** below.
            """
        )

        with gr.Row():
            # Left column - Input
            with gr.Column(scale=2):
                # Example selector dropdown
                example_dropdown = gr.Dropdown(
                    choices=[label for label, _ in EXAMPLE_CHOICES],
                    value="-- Seleccionar ejemplo --",
                    label="📋 Query Examples (select to load)",
                    info="Choose from 145+ example queries organized by category",
                )

                query_input = gr.Textbox(
                    label="Date Query",
                    placeholder="e.g., 'Q3 2024', 'semana pasada', 'cuánto cashback he ganado este mes?'",
                    lines=3,
                )

                with gr.Row():
                    timezone_input = gr.Dropdown(
                        choices=[
                            "America/Lima",
                            "America/New_York",
                            "America/Los_Angeles",
                            "Europe/London",
                            "UTC",
                        ],
                        value="America/Lima",
                        label="Timezone",
                        scale=1,
                    )
                    submit_btn = gr.Button(
                        "🔍 Process Query",
                        variant="primary",
                        scale=2,
                    )

                # Quick date examples
                gr.Markdown("### ⚡ Quick Date Examples")

                with gr.Row():
                    gr.Button("hoy", size="sm", elem_classes="example-btn").click(
                        lambda: "hoy", outputs=query_input
                    )
                    gr.Button("ayer", size="sm", elem_classes="example-btn").click(
                        lambda: "ayer", outputs=query_input
                    )
                    gr.Button("semana pasada", size="sm", elem_classes="example-btn").click(
                        lambda: "semana pasada", outputs=query_input
                    )
                    gr.Button("mes anterior", size="sm", elem_classes="example-btn").click(
                        lambda: "mes anterior", outputs=query_input
                    )

                with gr.Row():
                    gr.Button("Q3 2024", size="sm", elem_classes="example-btn").click(
                        lambda: "Q3 2024", outputs=query_input
                    )
                    gr.Button("trimestre pasado", size="sm", elem_classes="example-btn").click(
                        lambda: "trimestre pasado", outputs=query_input
                    )
                    gr.Button("este mes", size="sm", elem_classes="example-btn").click(
                        lambda: "este mes", outputs=query_input
                    )
                    gr.Button("ytd", size="sm", elem_classes="example-btn").click(
                        lambda: "ytd", outputs=query_input
                    )

                # Stats
                gr.Markdown(
                    f"""
                    ---
                    **Query Categories:**
                    - 📅 Dates: {len(DATE_QUERIES)}
                    - 💰 Cashback: {len(CASHBACK_QUERIES)}
                    - 🛒 Consumos: {len(CONSUMOS_QUERIES)}
                    - ⭐ Loyalty: {len(LOYALTY_QUERIES)}
                    - 📚 Knowledge Base: {len(KNOWLEDGE_BASE_QUERIES)}
                    - 🎯 Campaigns: {len(CAMPAIGN_QUERIES)}
                    - 🔧 Other: {len(OTHER_QUERIES)}
                    """
                )

            # Right column - Results
            with gr.Column(scale=3):
                result_output = gr.Markdown(
                    label="Result",
                    value="*Select an example or enter a query and click 'Process Query'*",
                )

                with gr.Accordion("Details & Computation Trace", open=False):
                    details_output = gr.Markdown()

                with gr.Accordion("Raw JSON Response", open=False):
                    json_output = gr.Code(
                        language="json",
                        label="JSON",
                    )

        # Holidays tab
        with gr.Tab("📆 Holiday Calendar"):
            gr.Markdown("### Peru Banking Holidays Reference")

            with gr.Row():
                cal_select = gr.Dropdown(
                    choices=["PERU_BANKING", "GREGORIAN"],
                    value="PERU_BANKING",
                    label="Calendar System",
                )
                year_select = gr.Dropdown(
                    choices=[2024, 2025, 2026],
                    value=2025,
                    label="Year",
                )
                month_select = gr.Dropdown(
                    choices=[None, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                    value=None,
                    label="Month (optional)",
                )
                fetch_holidays_btn = gr.Button("📅 Fetch Holidays", variant="primary")

            holidays_output = gr.Markdown()

            fetch_holidays_btn.click(
                fn=get_holidays_for_display,
                inputs=[cal_select, year_select, month_select],
                outputs=holidays_output,
            )

        # About tab
        with gr.Tab("ℹ️ About"):
            gr.Markdown(
                f"""
                ## Architecture

                This Date Reasoning Agent follows the principle:
                **"The agent handles SEMANTIC UNDERSTANDING only. All date calculations are performed by deterministic TOOLS."**

                ```
                User Query → Semantic Parser → Query Decomposer → Tools (compute) → Response
                ```

                ### Core Tools

                | Tool | Purpose |
                |------|---------|
                | `get_current_date_info` | Establishes immutable reference point |
                | `resolve_period` | Converts period expressions to date ranges |
                | `get_holiday_calendar` | Returns holidays for a calendar system |
                | `compute_date_range` | Performs date arithmetic |

                ### Supported Period Expressions

                **Spanish:** hoy, ayer, semana pasada, semana antepasada, mes anterior, trimestre pasado, Q1-Q4 YYYY

                **English:** today, yesterday, last week, last month, last quarter, ytd, Q1-Q4 YYYY

                ### Peru Banking Calendar

                Includes all official Peruvian banking holidays:
                - Año Nuevo (Jan 1)
                - Fiestas Patrias (Jul 28-29)
                - And many more...

                ### Test Query Examples

                This UI includes **{total_examples} example queries** across categories:
                - **Cashback**: Questions about cashback balance, earnings, redemption
                - **Consumos**: Spending analysis, categories, trends
                - **Loyalty**: Level status, benefits, progression
                - **Knowledge Base**: Card info, payments, general questions
                - **Campaigns**: Active campaigns, conditions
                - **Other**: Miscellaneous queries

                ---
                Built for high-precision financial date calculations with full audit trail support.
                """
            )

        # Wire up the example dropdown
        example_dropdown.change(
            fn=on_example_select,
            inputs=[example_dropdown],
            outputs=[query_input],
        )

        # Wire up the main query processing
        submit_btn.click(
            fn=process_query,
            inputs=[query_input, timezone_input],
            outputs=[result_output, details_output, json_output],
        )

        # Also process on Enter key
        query_input.submit(
            fn=process_query,
            inputs=[query_input, timezone_input],
            outputs=[result_output, details_output, json_output],
        )

    return demo


if __name__ == "__main__":
    # Gradio runs on the main public port (8080 for Cloud Run, 7860 for local dev)
    port = int(os.getenv("GRADIO_SERVER_PORT", os.getenv("PORT", "7860")))

    total_examples = (
        len(DATE_QUERIES) + len(CASHBACK_QUERIES) + len(CONSUMOS_QUERIES) +
        len(LOYALTY_QUERIES) + len(KNOWLEDGE_BASE_QUERIES) +
        len(CAMPAIGN_QUERIES) + len(OTHER_QUERIES)
    )

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║           Date Reasoning Agent - Gradio Frontend                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  IMPORTANT: Make sure the backend server is running first!       ║
║                                                                  ║
║  Start backend:  python server.py                                ║
║  Then run this:  python app.py                                   ║
║                                                                  ║
║  Backend URL: {BACKEND_URL:<43} ║
║  Frontend URL: http://localhost:{port:<27} ║
║                                                                  ║
║  Example Queries: {total_examples:<42} ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
    )
