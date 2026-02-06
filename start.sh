#!/bin/bash
# Cloud Run startup script for Date Reasoning Agent
#
# Architecture:
#   - Gradio UI runs on public port 8080 (Cloud Run exposes this)
#   - FastAPI backend runs on internal port 8000 (not exposed)
#   - Gradio communicates with backend via http://localhost:8000

set -e

# Port configuration
PUBLIC_PORT=${PORT:-8080}
BACKEND_PORT=${DATE_AGENT_BACKEND_PORT:-8000}

echo "============================================"
echo "Starting Date Reasoning Agent"
echo "============================================"
echo "Architecture:"
echo "  [Internet] --> [:${PUBLIC_PORT}] --> [Gradio UI]"
echo "                                          |"
echo "                                          v (internal)"
echo "                                    [Backend :${BACKEND_PORT}]"
echo "============================================"
echo "Timezone: ${DATE_AGENT_DEFAULT_TIMEZONE:-America/Lima}"
echo "Locale: ${DATE_AGENT_DEFAULT_LOCALE:-es}"
echo "============================================"

# 1. Start backend (FastAPI) on INTERNAL port (not exposed to internet)
echo ""
echo "[1/2] Starting backend server on internal port ${BACKEND_PORT}..."
DATE_AGENT_BACKEND_PORT=${BACKEND_PORT} python server.py &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
sleep 3

# Verify backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "ERROR: Backend failed to start"
    exit 1
fi

# Check backend health (internal)
for i in {1..10}; do
    if curl -sf http://localhost:${BACKEND_PORT}/health > /dev/null 2>&1; then
        echo "Backend is healthy on internal port ${BACKEND_PORT}!"
        break
    fi
    echo "Waiting for backend health check... ($i/10)"
    sleep 1
done

# 2. Start frontend (Gradio) on PUBLIC port (Cloud Run exposes this)
echo ""
echo "[2/2] Starting Gradio UI on public port ${PUBLIC_PORT}..."
export GRADIO_SERVER_PORT=${PUBLIC_PORT}
export DATE_AGENT_BACKEND_URL="http://localhost:${BACKEND_PORT}"
python app.py &
FRONTEND_PID=$!

# Wait a moment for frontend to initialize
sleep 3

# Verify frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "ERROR: Frontend failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "============================================"
echo "Date Reasoning Agent is running!"
echo ""
echo "PUBLIC ENDPOINT (Gradio UI):"
echo "  http://localhost:${PUBLIC_PORT}"
echo ""
echo "INTERNAL ONLY (Backend API):"
echo "  http://localhost:${BACKEND_PORT}"
echo "============================================"

# Trap signals for graceful shutdown
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGTERM SIGINT

# Wait for either process to exit
wait -n $BACKEND_PID $FRONTEND_PID
EXIT_CODE=$?

# If we get here, one of the processes exited
echo "One of the services stopped (exit code: $EXIT_CODE), shutting down..."
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
exit $EXIT_CODE
