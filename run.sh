#!/bin/bash
#
# Date Reasoning Agent - Startup Script
#
# This script starts both the backend server and Gradio frontend.
#
# Usage:
#   ./run.sh           # Start both backend and frontend
#   ./run.sh --backend # Start only the backend
#   ./run.sh --frontend # Start only the frontend (assumes backend is running)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=${DATE_AGENT_PORT:-8000}
FRONTEND_PORT=${GRADIO_PORT:-7860}
VENV_PATH=".venv"

print_banner() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}     ${GREEN}📅 High-Precision Date Reasoning Agent${NC}                        ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}     ${YELLOW}Financial Operations Date Calculator${NC}                         ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv "$VENV_PATH"
    fi

    # Activate venv
    source "$VENV_PATH/bin/activate"

    # Check for required packages
    if ! python -c "import pydantic" 2>/dev/null; then
        echo -e "${YELLOW}Installing dependencies...${NC}"
        pip install --quiet pydantic python-dateutil fastapi uvicorn httpx gradio
    fi
}

start_backend() {
    echo -e "${GREEN}Starting backend server on port $BACKEND_PORT...${NC}"
    python server.py &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"

    # Wait for backend to be ready
    echo -e "${YELLOW}Waiting for backend to initialize...${NC}"
    for i in {1..30}; do
        if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend is ready!${NC}"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}✗ Backend failed to start${NC}"
    return 1
}

start_frontend() {
    echo -e "${GREEN}Starting Gradio frontend on port $FRONTEND_PORT...${NC}"
    python app.py &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
}

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"

    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # Kill any remaining processes
    pkill -f "python server.py" 2>/dev/null || true
    pkill -f "python app.py" 2>/dev/null || true

    echo -e "${GREEN}Done.${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main logic
print_banner

case "${1:-}" in
    --backend)
        check_venv
        start_backend
        echo ""
        echo -e "${GREEN}Backend running at: http://localhost:$BACKEND_PORT${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        wait $BACKEND_PID
        ;;
    --frontend)
        check_venv
        echo -e "${YELLOW}Make sure backend is running first!${NC}"
        start_frontend
        echo ""
        echo -e "${GREEN}Frontend running at: http://localhost:$FRONTEND_PORT${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        wait $FRONTEND_PID
        ;;
    *)
        check_venv
        start_backend
        sleep 2
        start_frontend

        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  ✓ Date Reasoning Agent is running!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  Backend API:  ${BLUE}http://localhost:$BACKEND_PORT${NC}"
        echo -e "  Frontend UI:  ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
        echo ""
        echo -e "  ${YELLOW}Press Ctrl+C to stop both services${NC}"
        echo ""

        # Wait for both processes
        wait
        ;;
esac
