# High-Precision Date Reasoning Agent for Financial Operations

A Python-based agent that converts natural language temporal queries into precise date ranges for financial operations. Designed for the Peru banking context with Spanish language support.

## Architecture Philosophy

**Core Principle**: The agent handles **semantic understanding only**. All date calculations are performed by deterministic **tools** (source of truth).

```
User Query → Semantic Parser → Tool Orchestrator → Tools (compute) → Response
```

The agent **never computes dates directly**. This ensures:
- Deterministic, reproducible results
- Full audit trail for compliance
- Clear separation between language understanding and calculation

## Features

- **Natural Language Parsing**: Understands queries in Spanish and English
- **Peru Banking Calendar**: Includes all official Peruvian banking holidays (Fiestas Patrias, etc.)
- **Business Day Calculations**: Correctly handles weekends and holidays
- **Named Periods**: "Q3 2024", "last month", "semana pasada", "trimestre anterior"
- **Compositional Queries**: "3 business days before each month-end"
- **Audit Trail**: Every calculation is traceable for compliance
- **Azure OpenAI Integration**: Optional LLM for complex semantic parsing

## Project Structure

```
agent_date/
├── src/date_agent/
│   ├── core/                    # Config, exceptions, constants, audit
│   ├── models/                  # Pydantic schemas
│   ├── tools/                   # Date calculation tools (SOURCE OF TRUTH)
│   │   ├── current_date_tool.py      # get_current_date_info
│   │   ├── resolve_period_tool.py    # resolve_period
│   │   ├── holiday_calendar_tool.py  # get_holiday_calendar
│   │   └── compute_date_range_tool.py # compute_date_range
│   ├── calendars/               # Calendar implementations
│   │   ├── gregorian.py         # Standard (weekends only)
│   │   └── peru_banking.py      # Peru banking holidays
│   ├── localization/            # Spanish/English support
│   └── agent/                   # Semantic parser, orchestrator
├── tests/
│   ├── unit/                    # Tool-level tests
│   └── integration/             # Full agent pipeline tests
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Setup

1. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows
   ```

2. **Install dependencies**:
   ```bash
   # For basic usage
   pip install pydantic python-dateutil

   # For development (includes testing tools)
   pip install pydantic python-dateutil pytest pytest-asyncio

   # Optional: For Azure OpenAI semantic parsing
   pip install openai azure-identity
   ```

3. **Configure environment** (optional, for Azure OpenAI):
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

## Running Tests

### Run All Tests

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests with verbose output
PYTHONPATH=src pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Calendar tests (Gregorian + Peru Banking)
PYTHONPATH=src pytest tests/unit/test_calendars.py -v

# Current date tool tests
PYTHONPATH=src pytest tests/unit/test_current_date_tool.py -v

# Period resolution tests (Spanish + English)
PYTHONPATH=src pytest tests/unit/test_resolve_period_tool.py -v

# Full agent integration tests
PYTHONPATH=src pytest tests/integration/test_agent.py -v
```

### Expected Test Results

```
======================= 65 passed, 10 warnings in 0.07s ========================
```

| Test Suite | Tests | Description |
|------------|-------|-------------|
| `test_calendars.py` | 25 | Calendar systems, business days, holidays |
| `test_current_date_tool.py` | 10 | Reference date, boundaries, lookback |
| `test_resolve_period_tool.py` | 19 | Period expressions in Spanish/English |
| `test_agent.py` | 11 | Full agent pipeline integration |

## Running the Web Interface (Gradio)

The agent includes a Gradio-based web interface for interactive testing.

### Quick Start

```bash
# Make sure you're in the project directory with venv activated
source .venv/bin/activate

# Install additional dependencies for the UI
pip install fastapi uvicorn httpx gradio

# Option 1: Use the startup script (recommended)
./run.sh

# Option 2: Start backend and frontend separately
# Terminal 1 - Start the backend server
python server.py

# Terminal 2 - Start the Gradio frontend
python app.py
```

### Access the Interface

Once running, open your browser:
- **Frontend UI**: http://localhost:7860
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Startup Script Options

```bash
./run.sh            # Start both backend and frontend
./run.sh --backend  # Start only the backend server
./run.sh --frontend # Start only the frontend (requires backend running)
```

### Environment Variables

```bash
# Backend
DATE_AGENT_PORT=8000           # Backend server port
DATE_AGENT_HOST=0.0.0.0        # Backend server host
DATE_AGENT_TIMEZONE=America/Lima
DATE_AGENT_LOCALE=es
DATE_AGENT_CALENDAR=PERU_BANKING

# Frontend
GRADIO_PORT=7860               # Gradio frontend port
DATE_AGENT_BACKEND_URL=http://localhost:8000
```

### Features

The web interface provides:
- **Query Input**: Enter natural language date queries
- **Quick Examples**: One-click buttons for common queries
- **Results Display**: Formatted date ranges and details
- **Holiday Calendar**: Browse Peru banking holidays by year/month
- **Raw JSON**: View the full API response
- **Computation Trace**: See how the agent processed your query

## Usage (Programmatic)

### Basic Usage (Python)

```python
import asyncio
from date_agent.agent.date_agent import DateReasoningAgent
from date_agent.core.config import DateAgentConfig

# Create agent with default configuration (Peru timezone, Spanish locale)
config = DateAgentConfig()
agent = DateReasoningAgent(config)

async def main():
    # Simple period resolution
    result = await agent.process_query("Q3 2024")
    print(result)
    # {'success': True, 'start_date': '2024-07-01', 'end_date': '2024-09-30', ...}

    # Spanish query
    result = await agent.process_query("semana pasada")
    print(result)
    # Returns last week's date range

    # With holiday awareness
    result = await agent.process_query("julio 2024 excluyendo feriados bancarios")
    print(result)
    # Returns July 2024 range with Peru banking holidays marked

asyncio.run(main())
```

### Using Individual Tools

```python
import asyncio
from datetime import datetime, timezone
from date_agent.tools import ResolvePeriodTool, GetHolidayCalendarTool
from date_agent.core.config import ToolExecutionContext

# Create execution context
context = ToolExecutionContext(
    execution_id="example-001",
    reference_date=datetime.now(timezone.utc),
    timezone="America/Lima",
    calendar_system="PERU_BANKING",
    locale="es",
)

async def main():
    # Resolve a period
    tool = ResolvePeriodTool()
    result = await tool.execute(context, period="trimestre pasado")
    print(f"Last quarter: {result.output.start_date} to {result.output.end_date}")

    # Get holidays
    holiday_tool = GetHolidayCalendarTool()
    result = await holiday_tool.execute(
        context,
        calendar_system="PERU_BANKING",
        start_date="2024-07-01",
        end_date="2024-07-31",
    )
    print(f"Holidays in July 2024: {len(result.output.holidays)}")
    for h in result.output.holidays:
        print(f"  - {h.date}: {h.name_localized}")

asyncio.run(main())
```

### Using Calendars Directly

```python
from datetime import date
from date_agent.calendars import get_calendar

# Get Peru banking calendar
cal = get_calendar("PERU_BANKING")

# Check if a date is a business day
is_bd = cal.is_business_day(date(2024, 7, 28))  # False (Fiestas Patrias)

# Get holiday info
holiday = cal.get_holiday_info(date(2024, 7, 28))
print(f"{holiday.name} ({holiday.name_localized})")  # Independence Day (Fiestas Patrias)

# Add business days
result = cal.add_business_days(date(2024, 7, 25), 3)
print(f"3 business days after July 25: {result}")  # Skips Fiestas Patrias

# Count business days in a range
count = cal.count_business_days(date(2024, 7, 1), date(2024, 7, 31))
print(f"Business days in July 2024: {count}")
```

## Supported Period Expressions

### Spanish

| Expression | Period Type |
|------------|-------------|
| `hoy` | Today |
| `ayer` | Yesterday |
| `semana pasada` | Last week |
| `la semana pasada` | Last week |
| `semana antepasada` | Week before last |
| `mes anterior` | Last month |
| `ultimo mes` | Last month |
| `trimestre pasado` | Last quarter |
| `este año` | This year |
| `Q3 2024` / `T3 2024` | Named quarter |

### English

| Expression | Period Type |
|------------|-------------|
| `today` | Today |
| `yesterday` | Yesterday |
| `last week` | Last week |
| `last month` | Last month |
| `last quarter` | Last quarter |
| `this year` | This year |
| `Q3 2024` | Named quarter |
| `ytd` | Year to date |

## Calendar Systems

### GREGORIAN

Standard calendar with weekends only (no holidays).

### PERU_BANKING

Peru banking calendar including official holidays:

| Date | Holiday (Spanish) |
|------|-------------------|
| Jan 1 | Año Nuevo |
| Maundy Thursday | Jueves Santo |
| Good Friday | Viernes Santo |
| May 1 | Día del Trabajo |
| Jun 7 | Día de la Batalla de Arica |
| Jun 29 | San Pedro y San Pablo |
| Jul 23 | Día de la Fuerza Aérea |
| Jul 28-29 | Fiestas Patrias |
| Aug 6 | Batalla de Junín |
| Aug 30 | Santa Rosa de Lima |
| Oct 8 | Combate de Angamos |
| Nov 1 | Día de Todos los Santos |
| Dec 8 | Inmaculada Concepción |
| Dec 9 | Batalla de Ayacucho |
| Dec 25 | Navidad |

## Configuration

### Environment Variables

```bash
# Azure OpenAI (optional)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Agent defaults
DATE_AGENT_DEFAULT_TIMEZONE=America/Lima
DATE_AGENT_DEFAULT_LOCALE=es
DATE_AGENT_MAX_LOOKBACK_MONTHS=6
DATE_AGENT_ENABLE_AUDIT=true

# Logging
LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from date_agent.core.config import DateAgentConfig

config = DateAgentConfig(
    agent_id="my-agent",
    default_timezone="America/Lima",
    default_locale="es",
    default_calendar_system="PERU_BANKING",
    max_lookback_months=6,
    enable_audit_trail=True,
)
```

## Tools Reference

### get_current_date_info

Establishes the immutable reference point for all calculations.

**Input**:
- `timezone`: IANA timezone (default: "America/Lima")
- `include_boundaries`: Include week/month boundaries (default: true)
- `lookback_months`: Financial lookback limit (default: 6)

**Output**: Current date, week/month/quarter boundaries, ISO week info, lookback limit

### resolve_period

Converts semantic period expressions to date ranges.

**Input**:
- `period`: Period expression ("Q3 2024", "semana pasada", etc.)
- `locale`: Language for parsing ("es", "en")
- `calendar_system`: Calendar to use

**Output**: `start_date`, `end_date`, `calendar_days`, descriptions

### get_holiday_calendar

Returns holidays for a calendar system within a date range.

**Input**:
- `calendar_system`: "GREGORIAN" or "PERU_BANKING"
- `start_date`, `end_date`: Date range
- `include_weekends`: Include weekend dates in output

**Output**: List of holidays, business day counts

### compute_date_range

Performs date arithmetic with calendar awareness.

**Input**:
- `base_date`: Starting date
- `operation`: Operation to perform (add_business_days, month_end, etc.)
- `value`: Numeric value for operation
- `calendar_system`: Calendar for business day calculations

**Operations**:
- `add_calendar_days`, `subtract_calendar_days`
- `add_business_days`, `subtract_business_days`
- `add_weeks`, `subtract_weeks`
- `add_months`, `subtract_months`
- `month_start`, `month_end`
- `quarter_start`, `quarter_end`
- `next_business_day`, `previous_business_day`

## Audit Trail

Every query creates an audit entry containing:
- Execution ID and timestamp
- Original query
- Reference date used
- Tool calls with input/output
- Computation steps
- Duration

```python
result = await agent.process_query("Q3 2024")
print(result["audit_id"])  # UUID for this execution
```

## Development

### Running Tests with Coverage

```bash
pip install pytest-cov
PYTHONPATH=src pytest tests/ --cov=date_agent --cov-report=html
```

### Type Checking

```bash
pip install mypy
mypy src/date_agent
```

### Code Formatting

```bash
pip install black ruff
black src/ tests/
ruff check src/ tests/
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request
