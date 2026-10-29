#!/bin/bash
# build_mobile_frontend.sh: Builds the Fluxion mobile frontend for production.

# Exit immediately if a command exits with a non-zero status.
# Treat unset variables as an error.
# Exit if any command in a pipeline fails.
set -euo pipefail

# Define project root (assuming script is run from the project root or a known location)
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==================================================="
echo " Building Fluxion Mobile Frontend"
echo "==================================================="

MOBILE_FRONTEND_DIR="${PROJECT_DIR}/mobile-frontend"

if [ ! -d "${MOBILE_FRONTEND_DIR}" ]; then
    echo "Error: Mobile Frontend directory not found at ${MOBILE_FRONTEND_DIR}. Cannot build mobile frontend." >&2
    exit 1
fi

cd "${MOBILE_FRONTEND_DIR}"
echo "Changed directory to $(pwd) for mobile frontend build."

if ! command -v npm &> /dev/null; then
    echo "Error: npm command could not be found. Please ensure Node.js and npm are installed and in your PATH." >&2
    exit 1
elif [ ! -f "package.json" ]; then
    echo "Error: package.json not found in ${MOBILE_FRONTEND_DIR}. Cannot build mobile frontend." >&2
    exit 1
else
    echo "Running 'npm run build' for mobile frontend..."
    # Note: Mobile builds often require specific environment setup (e.g., Expo, native tools).
    # This assumes a standard npm build script is defined in package.json.
    npm run build || { echo "Error: Mobile Frontend build failed. Check native environment setup." >&2; exit 1; }
    echo "Mobile Frontend build completed successfully."
fi

cd "${PROJECT_DIR}" # Return to the main project directory

echo "==================================================="
echo " Mobile Frontend build finished."
echo "==================================================="
