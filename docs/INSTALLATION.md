# Installation Guide

This guide provides step-by-step instructions for installing Fluxion on various platforms and environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Component Installation](#component-installation)
- [Verification](#verification)
- [Next Steps](#next-steps)

## Prerequisites

### System Requirements

| Component   | Minimum   | Recommended | Notes                                   |
| ----------- | --------- | ----------- | --------------------------------------- |
| **CPU**     | 4 cores   | 8+ cores    | AI/ML features require more cores       |
| **RAM**     | 16GB      | 32GB+       | 32GB required for ML model training     |
| **Storage** | 100GB SSD | 500GB+ SSD  | Blockchain data and time-series storage |
| **Network** | 100Mbps   | 1Gbps+      | For blockchain synchronization          |
| **GPU**     | None      | NVIDIA A100 | Optional, for AI model training         |

### Software Prerequisites

| Software           | Version | Purpose                       | Installation                                   |
| ------------------ | ------- | ----------------------------- | ---------------------------------------------- |
| **Git**            | 2.0+    | Version control               | [git-scm.com](https://git-scm.com/)            |
| **Python**         | 3.10+   | Backend services              | [python.org](https://www.python.org/)          |
| **Node.js**        | 18+     | Frontend applications         | [nodejs.org](https://nodejs.org/)              |
| **Docker**         | 24.0+   | Containerization              | [docker.com](https://www.docker.com/)          |
| **Docker Compose** | 2.0+    | Multi-container orchestration | Included with Docker Desktop                   |
| **Foundry**        | Latest  | Smart contract development    | `curl -L https://foundry.paradigm.xyz \| bash` |

## Installation Methods

### Method 1: Quick Start (Recommended for Testing)

Use the automated setup script for a quick development environment:

```bash
# Clone the repository
git clone https://github.com/quantsingularity/Fluxion.git
cd Fluxion

# Run automated setup
./scripts/setup_fluxion_env.sh

# Start all services
./scripts/run_fluxion.sh
```

This method:

- Creates Python virtual environment
- Installs all dependencies
- Sets up configuration files
- Starts backend and frontend services

### Method 2: Docker Compose (Recommended for Production)

Use Docker for a consistent, isolated environment:

```bash
# Clone the repository
git clone https://github.com/quantsingularity/Fluxion.git
cd Fluxion

# Start all services with Docker Compose
cd infrastructure
docker-compose up -d

# View logs
docker-compose logs -f
```

Services will be available at:

- Backend API: `http://localhost:8000`
- Web Frontend: `http://localhost:3000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### Method 3: Manual Installation

For full control over the installation process:

```bash
# Clone repository
git clone https://github.com/quantsingularity/Fluxion.git
cd Fluxion

# Follow component-specific instructions below
```

## Platform-Specific Instructions

### Linux (Ubuntu/Debian)

| Step                   | Command                                                                                                | Notes                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------ |
| **1. Update system**   | `sudo apt update && sudo apt upgrade -y`                                                               | Refresh package lists          |
| **2. Install Python**  | `sudo apt install python3.10 python3.10-venv python3-pip -y`                                           | Includes pip and venv          |
| **3. Install Node.js** | `curl -fsSL https://deb.nodesource.com/setup_18.x \| sudo -E bash -` <br> `sudo apt install -y nodejs` | Official NodeSource repository |
| **4. Install Docker**  | `curl -fsSL https://get.docker.com -o get-docker.sh` <br> `sudo sh get-docker.sh`                      | Official Docker installation   |
| **5. Install Foundry** | `curl -L https://foundry.paradigm.xyz \| bash` <br> `foundryup`                                        | Smart contract toolchain       |

### macOS

| Step                    | Command                                                                                           | Notes                     |
| ----------------------- | ------------------------------------------------------------------------------------------------- | ------------------------- |
| **1. Install Homebrew** | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` | Package manager for macOS |
| **2. Install Python**   | `brew install python@3.10`                                                                        | Python 3.10+              |
| **3. Install Node.js**  | `brew install node@18`                                                                            | Node.js 18+               |
| **4. Install Docker**   | Download from [docker.com](https://www.docker.com/products/docker-desktop)                        | Docker Desktop for Mac    |
| **5. Install Foundry**  | `curl -L https://foundry.paradigm.xyz \| bash` <br> `foundryup`                                   | Smart contract toolchain  |

### Windows (WSL2 Required)

| Step                      | Instructions                                                                        | Notes                            |
| ------------------------- | ----------------------------------------------------------------------------------- | -------------------------------- |
| **1. Enable WSL2**        | Follow [Microsoft WSL2 Guide](https://docs.microsoft.com/en-us/windows/wsl/install) | Required for Linux compatibility |
| **2. Install Ubuntu**     | `wsl --install -d Ubuntu-22.04`                                                     | Ubuntu LTS in WSL2               |
| **3. Follow Linux steps** | Use Ubuntu terminal in WSL2                                                         | See Linux instructions above     |

## Component Installation

### Backend (Python/FastAPI)

```bash
cd code/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at `http://localhost:8000/docs` (API documentation).

### Web Frontend (React)

```bash
cd web-frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with API endpoint

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`.

### Blockchain (Foundry/Solidity)

```bash
cd code/blockchain

# Install Foundry dependencies
forge install

# Compile contracts
forge build

# Run tests
forge test

# Deploy to local network (requires running anvil)
anvil  # In separate terminal
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --private-key <PRIVATE_KEY> --broadcast
```

### Mobile Frontend (React Native/Expo)

```bash
cd mobile-frontend

# Install dependencies
npm install

# Start Expo development server
npm start

# Run on iOS simulator (macOS only)
npm run ios

# Run on Android emulator
npm run android
```

### Machine Learning Models

```bash
cd code/ml_models

# Create virtual environment
python3 -m venv ml_venv
source ml_venv/bin/activate

# Install ML dependencies
pip install torch scikit-learn pandas numpy prophet

# Train liquidity model
python train_liquidity_model.py

# Test forecasting models
python forecasting_models.py
```

## Verification

### Verify Installation

Run the following commands to verify your installation:

```bash
# Check Python version
python3 --version  # Should be 3.10 or higher

# Check Node.js version
node --version  # Should be v18 or higher
npm --version

# Check Docker
docker --version
docker-compose --version

# Check Foundry
forge --version
cast --version
anvil --version

# Run test suite
cd Fluxion
./scripts/test_fluxion.sh
```

### Health Check

After starting the services, verify they're running:

```bash
# Backend health check
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy","timestamp":1234567890,"version":"1.0.0","uptime":123.45}

# Frontend access
# Open http://localhost:3000 in browser
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application
APP_ENV=development
DEBUG=true

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fluxion
REDIS_URL=redis://localhost:6379

# Blockchain
ETHEREUM_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/YOUR-API-KEY
POLYGON_RPC_URL=https://polygon-rpc.com
PRIVATE_KEY=your-private-key-here

# API Keys
CHAINLINK_API_KEY=your-chainlink-key
ALCHEMY_API_KEY=your-alchemy-key

# Security
JWT_SECRET=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key
```

See [Configuration Guide](CONFIGURATION.md) for complete options.

## Troubleshooting

| Issue                        | Solution                                                                                |
| ---------------------------- | --------------------------------------------------------------------------------------- |
| **Port already in use**      | Kill existing processes: `lsof -ti:8000 \| xargs kill -9` (replace 8000 with your port) |
| **Python module not found**  | Ensure virtual environment is activated: `source venv/bin/activate`                     |
| **Docker permission denied** | Add user to docker group: `sudo usermod -aG docker $USER` (logout/login required)       |
| **Forge command not found**  | Run foundryup: `foundryup`                                                              |
| **npm install fails**        | Clear cache: `npm cache clean --force && rm -rf node_modules && npm install`            |

For more issues, see [Troubleshooting Guide](TROUBLESHOOTING.md).

## Next Steps

After installation:

1. **Read the [Usage Guide](USAGE.md)** to learn how to use Fluxion
2. **Review [Configuration Guide](CONFIGURATION.md)** to customize your setup
3. **Explore [Examples](examples/)** for practical use cases
4. **Check [API Reference](API.md)** for integration details

## Support

- **Issues**: [GitHub Issues](https://github.com/quantsingularity/Fluxion/issues)
- **Documentation**: This docs directory
- **Community**: Join discussions in GitHub Discussions
