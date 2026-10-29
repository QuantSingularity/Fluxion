#!/bin/bash
set -euo pipefail
# Run script for Fluxion project
# This script starts the application components (backend + web frontend).
# Run it from the repository root: ./scripts/run_fluxion.sh

# Resolve the repo root regardless of where the script is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Fluxion application...${NC}"

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo -e "${BLUE}Creating Python virtual environment...${NC}"
  python3 -m venv venv
fi

# Activate virtual environment and install backend dependencies
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r code/backend/requirements.txt > /dev/null

# Start backend application
echo -e "${BLUE}Starting backend service...${NC}"
cd code/backend
uvicorn app.main:app --host 0.0.0.0 --port 5000 &
APP_PID=$!
cd "$ROOT_DIR"

# Start web frontend application
echo -e "${BLUE}Starting frontend service...${NC}"
cd web-frontend
npm install > /dev/null
npm run dev &
FRONTEND_PID=$!
cd "$ROOT_DIR"

echo -e "${GREEN}Fluxion application is running!${NC}"
echo -e "${GREEN}Backend running with PID: ${APP_PID}${NC}"
echo -e "${GREEN}Frontend running with PID: ${FRONTEND_PID}${NC}"
echo -e "${GREEN}Backend API: http://localhost:5000${NC}"
echo -e "${GREEN}Frontend UI: http://localhost:3000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"

# Handle graceful shutdown
cleanup() {
  echo -e "${BLUE}Stopping services...${NC}"
  kill "$APP_PID" 2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
  echo -e "${GREEN}All services stopped${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running
wait
