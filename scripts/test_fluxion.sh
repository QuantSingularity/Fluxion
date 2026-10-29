#!/bin/bash
set -euo pipefail

# Test script for Fluxion application
# This script runs smoke tests for the backend and builds the web frontend.
# Run it from anywhere; paths are resolved relative to the repo root.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Track a backend we may start ourselves so we can stop it at the end.
BACKEND_PID=""

API_BASE="http://localhost:5000"
HEALTH_URL="${API_BASE}/api/v1/health/"

echo -e "${BLUE}Starting Fluxion test suite...${NC}"

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo -e "${BLUE}Creating Python virtual environment...${NC}"
  python3 -m venv venv
fi

# Activate virtual environment and install backend dependencies
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r code/backend/requirements.txt > /dev/null

# Test backend health (start it if it is not already running).
echo -e "${BLUE}Running API health check...${NC}"
if curl -sf "$HEALTH_URL" > /dev/null; then
  echo -e "${GREEN}Backend API is running and healthy${NC}"
else
  echo -e "${BLUE}Backend not responding; starting it for testing...${NC}"
  (cd code/backend && uvicorn app.main:app --host 0.0.0.0 --port 5000 &)
  BACKEND_PID=$!
  # Wait for the API to become healthy (up to ~15s).
  for _ in $(seq 1 15); do
    if curl -sf "$HEALTH_URL" > /dev/null; then break; fi
    sleep 1
  done
  if curl -sf "$HEALTH_URL" > /dev/null; then
    echo -e "${GREEN}Backend API started successfully${NC}"
  else
    echo -e "${RED}Failed to start backend API${NC}"
    exit 1
  fi
fi

# Test web frontend build
echo -e "${BLUE}Testing frontend build...${NC}"
cd web-frontend
npm install > /dev/null
if npm run build; then
  echo -e "${GREEN}Frontend build successful${NC}"
else
  echo -e "${RED}Frontend build failed${NC}"
  exit 1
fi
cd "$ROOT_DIR"

# Test integration (root endpoint identifies the API)
echo -e "${BLUE}Testing API integration...${NC}"
if curl -sf "${API_BASE}/" | grep -q "Fluxion"; then
  echo -e "${GREEN}API integration test passed${NC}"
else
  echo -e "${RED}API integration test failed${NC}"
fi

# Clean up a backend we started.
if [ -n "$BACKEND_PID" ]; then
  echo -e "${BLUE}Stopping test backend...${NC}"
  kill "$BACKEND_PID" 2>/dev/null || true
fi

echo -e "${GREEN}All tests completed!${NC}"
