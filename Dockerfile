# Date Reasoning Agent - Cloud Run Deployment
# Single container: Gradio UI (public) + FastAPI backend (internal)
#
# Architecture:
#   [Internet] --> [Cloud Run :8080] --> [Gradio UI :8080]
#                                              |
#                                              v (internal)
#                                        [FastAPI Backend :8000]

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY server.py app.py ./

# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# =============================================================================
# Port Configuration:
# - Gradio UI runs on public port 8080 (Cloud Run default)
# - FastAPI backend runs on internal port 8000 (not exposed)
# =============================================================================
ENV PORT=8080
ENV GRADIO_SERVER_PORT=8080
ENV DATE_AGENT_BACKEND_PORT=8000
ENV DATE_AGENT_BACKEND_URL=http://localhost:8000

# Default agent configuration
ENV DATE_AGENT_DEFAULT_TIMEZONE=America/Lima
ENV DATE_AGENT_DEFAULT_LOCALE=es
ENV DATE_AGENT_DEFAULT_CALENDAR=PERU_BANKING
ENV DATE_AGENT_MAX_LOOKBACK_MONTHS=6
ENV DATE_AGENT_ENABLE_AUDIT=true

# Expose main port (Cloud Run routes traffic here → Gradio UI)
EXPOSE 8080

# Health check targets Gradio (public endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8080/ > /dev/null || exit 1

# Start both services
CMD ["./start.sh"]
