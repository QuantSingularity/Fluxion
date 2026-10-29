#!/bin/bash

# Fluxion Project Setup Script (Comprehensive)

# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

# Prerequisites (ensure these are installed and configured based on README.md):
# - Node.js (for frontend and blockchain components)
# - npm (Node package manager)
# - Python 3.x (the script will use python3.11 available in the environment for backend/ML)
# - pip (Python package installer)
# - Foundry (for blockchain development - `forge` command)
# - Docker & Docker Compose (for infra/services like zkEVM, TimescaleDB, Redis)
# - Celery (for backend task queue)
# - Access to Polygon zkEVM, Chainlink CCIP, The Graph (for full deployment)
# - Potentially other tools like Terraform, kubectl, graph-cli for full deployment cycle.

echo "Starting Fluxion project setup..."

PROJECT_DIR="/Fluxion"

if [ ! -d "${PROJECT_DIR}" ]; then
  echo "Error: Project directory ${PROJECT_DIR} not found."
  echo "Please ensure the project is extracted correctly."
  exit 1
fi

cd "${PROJECT_DIR}"
echo "Changed directory to $(pwd)"

# --- Blockchain Setup (Solidity/Foundry) ---
echo ""
echo "Setting up Fluxion Blockchain component..."
BLOCKCHAIN_DIR="${PROJECT_DIR}/code/blockchain"

if [ ! -d "${BLOCKCHAIN_DIR}" ]; then
    echo "Error: Blockchain directory ${BLOCKCHAIN_DIR} not found. Skipping blockchain setup."
else
    cd "${BLOCKCHAIN_DIR}"
    echo "Changed directory to $(pwd) for blockchain setup."

    if ! command -v forge &> /dev/null; then
        echo "Warning: forge command not found. Please install Foundry (https://getfoundry.sh) to manage blockchain dependencies."
    else
        echo "Installing blockchain dependencies using Foundry (forge install)..."
        forge install
        echo "Blockchain dependencies installed."
    fi
    echo "Foundry configuration file: foundry.toml"
    echo "Refer to README.md for contract deployment steps (e.g., using 'forge create')."
    cd "${PROJECT_DIR}" # Return to the main project directory
fi

# --- Backend Setup (Python/Flask or FastAPI) ---
echo ""
echo "Setting up Fluxion Backend..."
# FastAPI backend; dependencies and app live under code/backend.
BACKEND_CODE_DIR="${PROJECT_DIR}/code/backend"

if [ ! -d "${BACKEND_CODE_DIR}" ]; then
    echo "Error: Backend code directory ${BACKEND_CODE_DIR} not found. Skipping backend setup."
else
    cd "${BACKEND_CODE_DIR}"
    echo "Changed directory to $(pwd) for backend Python setup."

    if [ ! -f "requirements.txt" ]; then
        echo "Error: requirements.txt not found in ${BACKEND_CODE_DIR}. Cannot install backend dependencies."
    else
        echo "Creating Python virtual environment for backend (venv_fluxion_backend_py)..."
        if ! python3.11 -m venv venv_fluxion_backend_py; then
            echo "Failed to create backend virtual environment. Please check your Python installation."
        else
            # shellcheck source=/dev/null
            source venv_fluxion_backend_py/bin/activate
            echo "Backend Python virtual environment created and activated."

            echo "Installing backend Python dependencies from requirements.txt..."
            pip3 install -r requirements.txt
            echo "Backend dependencies installed."

            echo "To activate the backend virtual environment later, run: source ${BACKEND_CODE_DIR}/venv_fluxion_backend_py/bin/activate"
            echo "To run the backend (FastAPI): cd ${BACKEND_CODE_DIR} && uvicorn app.main:app --host 0.0.0.0 --port 5000"
            deactivate
            echo "Backend Python virtual environment deactivated."
        fi
    fi
    cd "${PROJECT_DIR}" # Return to the main project directory
fi

# --- Web Frontend Setup (React/Vite) ---
echo ""
echo "Setting up Fluxion Web Frontend..."
WEB_FRONTEND_DIR="${PROJECT_DIR}/web-frontend"

if [ ! -d "${WEB_FRONTEND_DIR}" ]; then
    echo "Error: Web Frontend directory ${WEB_FRONTEND_DIR} not found. Skipping Web Frontend setup."
else
    cd "${WEB_FRONTEND_DIR}"
    echo "Changed directory to $(pwd) for Web Frontend setup."

    if [ ! -f "package.json" ]; then
        echo "Error: package.json not found in ${WEB_FRONTEND_DIR}. Cannot install Web Frontend dependencies."
    else
        echo "Installing Web Frontend Node.js dependencies using npm..."
        if ! command -v npm &> /dev/null; then echo "npm command not found."; else npm install; fi
        echo "Web Frontend dependencies installed."
        echo "To start the Web Frontend development server (from ${WEB_FRONTEND_DIR}): npm run dev"
        echo "To build the Web Frontend (from ${WEB_FRONTEND_DIR}): npm run build"
    fi
    cd "${PROJECT_DIR}" # Return to the main project directory
fi

# --- Mobile Frontend Setup (React Native/Expo) ---
echo ""
echo "Setting up Fluxion Mobile Frontend..."
MOBILE_FRONTEND_DIR="${PROJECT_DIR}/mobile-frontend"

if [ ! -d "${MOBILE_FRONTEND_DIR}" ]; then
    echo "Error: Mobile Frontend directory ${MOBILE_FRONTEND_DIR} not found. Skipping Mobile Frontend setup."
else
    cd "${MOBILE_FRONTEND_DIR}"
    echo "Changed directory to $(pwd) for Mobile Frontend setup."

    if [ ! -f "package.json" ]; then
        echo "Error: package.json not found in ${MOBILE_FRONTEND_DIR}. Cannot install Mobile Frontend dependencies."
    else
        echo "Installing Mobile Frontend Node.js dependencies using npm..."
        if ! command -v npm &> /dev/null; then echo "npm command not found."; else npm install; fi
        echo "Mobile Frontend dependencies installed."
        echo "To start the Mobile Frontend (from ${MOBILE_FRONTEND_DIR}): npm start (or expo start, as per package.json)"
        echo "Ensure Expo CLI is installed globally ('npm install -g expo-cli' or 'yarn global add expo-cli') or use npx."
    fi
    cd "${PROJECT_DIR}" # Return to the main project directory
fi

# --- Environment Variables & Docker ---
echo ""
echo "Important Configuration Reminders from README.md:"
echo "1. Environment Variables: Copy '.env.example' to '.env' in relevant project root(s) and add blockchain RPC URLs and API keys."
# Check if .env.example exists at root
if [ -f ".env.example" ]; then
    echo "   Found .env.example at project root. Consider copying: cp .env.example .env"
fi
echo "2. Docker Services: The README mentions starting services with 'docker-compose -f infra/docker-compose.zk.yml up -d'."
echo "   Ensure Docker and Docker Compose are installed. This likely starts zkEVM, TimescaleDB, Redis etc."

# --- Further Deployment Steps (from README) ---
echo ""
echo "Further Deployment Steps mentioned in README.md (manual execution required):"
echo "- Train ML Models: e.g., 'python ml_models/train_liquidity_model.py ...' (check for 'ml_models' dir in 'code/')"
echo "- Deploy Smart Contracts: e.g., 'forge create ...'"
echo "- Deploy Subgraph: e.g., 'graph deploy ...'"
echo "- Apply Infrastructure (Terraform): e.g., 'cd infra/terraform && terraform init && terraform apply ...'"
echo "- Apply Kubernetes manifests: e.g., 'kubectl apply -f k8s/synthetic-engine.yaml' (check for 'k8s' dir in 'infra/')"

echo ""
echo "Fluxion project setup script finished."
echo "Please ensure all prerequisites are installed and review the README.md for detailed operational and deployment instructions."
echo "Pay attention to the backend framework discrepancy (Flask in requirements vs FastAPI in README tech stack)."
