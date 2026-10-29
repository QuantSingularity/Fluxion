#!/bin/bash
# build_web_frontend.sh: Builds the Fluxion web frontend for production.

# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error.
# Exit if any command in a pipeline fails.
set -euo pipefail

# Define project root (assuming script is run from the project root or a known location)
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==================================================="
echo " Building Fluxion Web Frontend"
echo "==================================================="

WEB_FRONTEND_DIR="${PROJECT_DIR}/web-frontend"

if [ ! -d "${WEB_FRONTEND_DIR}" ]; then
    echo "Error: Web Frontend directory not found at ${WEB_FRONTEND_DIR}. Cannot build frontend." >&2
    exit 1
fi

cd "${WEB_FRONTEND_DIR}"
echo "Changed directory to $(pwd) for web frontend build."

if ! command -v npm &> /dev/null; then
    echo "Error: npm command could not be found. Please ensure Node.js and npm are installed and in your PATH." >&2
    exit 1
elif [ ! -f "package.json" ]; then
    echo "Error: package.json not found in ${WEB_FRONTEND_DIR}. Cannot build frontend." >&2
    exit 1
else
    echo "Running 'npm run build' to create production assets..."
    npm run build || { echo "Error: Web Frontend build failed." >&2; exit 1; }
    echo "Web Frontend build completed successfully."
fi

cd "${PROJECT_DIR}" # Return to the main project directory

echo "==================================================="
echo " Web Frontend build finished."
echo "==================================================="
