"""Backend server for the Date Reasoning Agent.

Runs the agent and exposes it via FastAPI for the Gradio frontend to consume.

Usage:
    python server.py
    # or with custom port
    DATE_AGENT_PORT=8001 python server.py
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from date_agent.agent.date_agent import DateReasoningAgent
from date_agent.core.config import DateAgentConfig
from date_agent.calendars import get_calendar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DateAgentServer")

# Global agent instance
agent: Optional[DateReasoningAgent] = None


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str
    timezone: Optional[str] = None
    locale: Optional[str] = None
    calendar_system: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    success: bool
    query: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    calendar_days: Optional[int] = None
    business_days: Optional[int] = None
    period_type: Optional[str] = None
    description: Optional[str] = None
    reference_date: Optional[str] = None
    timezone: Optional[str] = None
    holidays: Optional[list] = None
    computation_trace: Optional[dict] = None
    audit_id: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    agent_id: str
    timestamp: str
    available_tools: list


class HolidaysRequest(BaseModel):
    """Request for holidays endpoint."""
    calendar_system: str = "PERU_BANKING"
    year: int
    month: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent on startup."""
    global agent

    logger.info("Initializing Date Reasoning Agent...")

    config = DateAgentConfig(
        agent_id="gradio-server",
        default_timezone=os.getenv("DATE_AGENT_TIMEZONE", "America/Lima"),
        default_locale=os.getenv("DATE_AGENT_LOCALE", "es"),
        default_calendar_system=os.getenv("DATE_AGENT_CALENDAR", "PERU_BANKING"),
        max_lookback_months=int(os.getenv("DATE_AGENT_LOOKBACK", "6")),
        enable_audit_trail=os.getenv("DATE_AGENT_AUDIT", "true").lower() == "true",
    )

    agent = DateReasoningAgent(config)

    logger.info(f"Agent initialized: {config.agent_id}")
    logger.info(f"Timezone: {config.default_timezone}")
    logger.info(f"Locale: {config.default_locale}")
    logger.info(f"Calendar: {config.default_calendar_system}")
    logger.info(f"Tools: {list(agent.tools.keys())}")

    yield

    logger.info("Shutting down Date Reasoning Agent...")


# Create FastAPI app
app = FastAPI(
    title="Date Reasoning Agent API",
    description="High-Precision Date Reasoning Agent for Financial Operations",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS for Gradio frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return HealthResponse(
        status="healthy",
        agent_id=agent.config.agent_id,
        timestamp=datetime.now().isoformat(),
        available_tools=list(agent.tools.keys()),
    )


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a natural language date query."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    logger.info(f"Processing query: {request.query}")

    # Build context from request
    context = {}
    if request.timezone:
        context["timezone"] = request.timezone

    # Process the query
    result = await agent.process_query(request.query, context if context else None)

    logger.info(f"Query result: success={result.get('success')}")

    return QueryResponse(**result)


@app.get("/tools")
async def get_tools():
    """Get available tools and their definitions."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return {
        "tools": agent.get_available_tools(),
    }


@app.post("/holidays")
async def get_holidays(request: HolidaysRequest):
    """Get holidays for a specific year/month."""
    try:
        calendar = get_calendar(request.calendar_system)
        holidays = calendar.get_holidays(request.year)

        # Filter by month if specified
        if request.month:
            holidays = [h for h in holidays if h.date.month == request.month]

        return {
            "calendar_system": request.calendar_system,
            "year": request.year,
            "month": request.month,
            "holidays": [
                {
                    "date": h.date.isoformat(),
                    "name": h.name,
                    "name_localized": h.name_localized,
                    "type": h.holiday_type if isinstance(h.holiday_type, str) else (h.holiday_type.value if h.holiday_type else None),
                }
                for h in holidays
            ],
            "count": len(holidays),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/calendars")
async def get_calendars():
    """Get available calendar systems."""
    return {
        "calendars": [
            {
                "id": "GREGORIAN",
                "name": "Gregorian",
                "description": "Standard calendar with weekends only",
            },
            {
                "id": "PERU_BANKING",
                "name": "Peru Banking",
                "description": "Peru banking calendar with official holidays",
            },
        ]
    }


@app.get("/examples")
async def get_examples():
    """Get example queries for the UI."""
    return {
        "examples": [
            # Spanish examples
            {"query": "hoy", "description": "Today's date"},
            {"query": "ayer", "description": "Yesterday"},
            {"query": "semana pasada", "description": "Last week"},
            {"query": "semana antepasada", "description": "Week before last"},
            {"query": "mes anterior", "description": "Last month"},
            {"query": "trimestre pasado", "description": "Last quarter"},
            {"query": "Q3 2024", "description": "Third quarter 2024"},
            {"query": "julio 2024", "description": "July 2024"},
            {"query": "feriados julio 2024", "description": "Holidays in July 2024"},
            # English examples
            {"query": "today", "description": "Today's date"},
            {"query": "last week", "description": "Last week"},
            {"query": "last month", "description": "Last month"},
            {"query": "last quarter", "description": "Last quarter"},
            {"query": "ytd", "description": "Year to date"},
        ]
    }


if __name__ == "__main__":
    import uvicorn

    # Backend runs on internal port (not exposed to public)
    # Use DATE_AGENT_BACKEND_PORT for internal backend port (default 8000)
    port = int(os.getenv("DATE_AGENT_BACKEND_PORT", os.getenv("DATE_AGENT_PORT", "8000")))
    host = os.getenv("DATE_AGENT_HOST", "0.0.0.0")

    logger.info(f"Starting backend server on {host}:{port} (internal)")

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
