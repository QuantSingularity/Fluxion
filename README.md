# Fluxion

![CI/CD Status](https://img.shields.io/github/actions/workflow/status/quantsingularity/Fluxion/cicd.yml?branch=main&label=CI%2FCD&logo=github)

## Synthetic Asset Liquidity Engine

Fluxion is a synthetic asset platform: a FastAPI backend for portfolios, transactions, risk, and compliance, a React web dashboard, and a React Native (Expo) mobile app. Alongside the application is a set of Foundry-managed Solidity contracts for minting and liquidating synthetic assets and a real zero-knowledge circuit for private price commitments, plus a small PyTorch research library for forecasting and risk scoring.

<div align="center">
  <img src="docs/images/homepage.bmp" alt="Fluxion HomePage" width="100%">
</div>

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Feature Status](#feature-status)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Installation and Setup](#installation-and-setup)
- [Running the Stack](#running-the-stack)
- [API Surface](#api-surface)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

Fluxion demonstrates a synthetic asset workflow across a real, runnable codebase. The application tier (backend, smart contracts, and two clients) is wired and covered by tests. The Solidity contracts and the zero-knowledge circuit are genuinely implemented; a small PyTorch research library (forecasting, risk prediction) sits alongside the application but is not yet called by the live API, which currently returns a deterministic placeholder prediction instead.

## Project Structure

```text
Fluxion/
├── code/
│   ├── backend/              # FastAPI service: API, auth, services, DB
│   │   ├── api/routes/       # Health, auth, users, portfolio, transactions,
│   │   │                     # analytics, markets, compliance, risk, ml
│   │   ├── config/           # Settings and database config
│   │   ├── middleware/       # Rate limit and security middleware
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Auth, portfolio, risk, protocol, compliance, security
│   │   ├── migrations/       # Alembic migrations
│   │   └── tests/            # Backend test suite
│   ├── blockchain/           # Foundry project
│   │   ├── contracts/        # SyntheticAssetFactory, LiquidityPoolManager,
│   │   │                     # SyntheticLiquidationEngine, GovernanceToken, zk/
│   │   ├── circuits/         # Circom circuit for price commitments
│   │   ├── test/             # Foundry test suite
│   │   └── subgraph/         # The Graph schema (not yet indexed)
│   └── ml_models/            # Research ML library (forecasting, risk, anomaly detection)
├── web-frontend/             # React (Vite) dashboard
├── mobile-frontend/          # React Native + Expo app
├── infrastructure/           # Docker, Kubernetes, Terraform, Ansible, monitoring
├── scripts/                  # Deployment, cross-chain test, ML pipeline, and monitoring scripts
├── docs/                     # Documentation (this directory)
└── README.md
```

## Feature Status

### Application tier (wired and tested)

| Component                      | Details                                                                                                                                                                                                                                                                           |
| :----------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **API**                        | FastAPI backend exposing endpoints under `/api/v1` for health, auth, users, portfolio, transactions, analytics, markets, compliance, and risk.                                                                                                                                    |
| **Auth**                       | bcrypt password hashing, JWT access and refresh tokens, TOTP-based MFA (pyotp), and API key management. `SECRET_KEY` must be at least 32 characters; the shipped default already satisfies that check, so unlike some sibling projects it is not rejected outright in production. |
| **Portfolio and risk engines** | Real in-process Python logic for VaR, Expected Shortfall, Sharpe and Sortino ratios, max drawdown, beta, concentration and liquidity risk, stress testing, portfolio performance, and rebalancing recommendations.                                                                |
| **Collateral engine**          | Mint, burn, and liquidate logic with price-staleness checks and collateral-ratio calculations, run in-process by the backend.                                                                                                                                                     |
| **Smart contracts**            | Foundry-managed Solidity 0.8 contracts: a synthetic asset factory (implements a vault interface, pulls prices via Chainlink's `AggregatorV3Interface` and the Chainlink Any-API request/fulfill pattern), a liquidity pool manager, a liquidation engine, and a governance token. |
| **Zero-knowledge layer**       | A real Circom circuit (`price_commitment.circom`) with a matching `Groth16Verifier.sol` contract for private price commitments.                                                                                                                                                   |
| **Web dashboard**              | React app covering Home, Dashboard, Synthetics, Pools (including pool creation), Portfolio, Transactions, Analytics, Settings, and authentication screens.                                                                                                                        |
| **Mobile app**                 | React Native (Expo) app covering the same functional areas through React Navigation's bottom-tab and stack navigators.                                                                                                                                                            |
| **Guest login**                | Both clients recognize a local demo session and keep working, with placeholder data, if the backend is unreachable.                                                                                                                                                               |

### Research tier (library modules)

| Component                       | Details                                                                                                                                                            |
| :------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Forecasting models**          | LSTM and Transformer time-series models (PyTorch) for price and liquidity forecasting.                                                                             |
| **Financial risk predictor**    | PyTorch model for risk scoring.                                                                                                                                    |
| **Anomaly detection**           | A standalone anomaly-detection module, separate from the Isolation Forest model that the backend's own threat-detection service uses for live security monitoring. |
| **Liquidity training pipeline** | Scripts to train a liquidity-prediction model.                                                                                                                     |

These modules are unit-tested and importable, but the live `/api/v1/predict` endpoint returns a deterministic placeholder forecast rather than calling into this library, and the `ml-service` container defined in Docker Compose is a minimal health and metrics stub with the same inference not yet wired in.

## Technology Stack

| Area                 | Technology                                                                                   |
| :------------------- | :------------------------------------------------------------------------------------------- |
| Blockchain           | Solidity 0.8, Foundry, OpenZeppelin, Chainlink price oracles and Any-API                     |
| Zero-knowledge       | Circom, a Groth16 verifier contract                                                          |
| Backend API          | Python 3.11+, FastAPI, Uvicorn, Pydantic v2                                                  |
| Auth                 | bcrypt, PyJWT, pyotp (MFA)                                                                   |
| Data layer           | SQLAlchemy 2 (async), Alembic, PostgreSQL, Redis                                             |
| ML / Quant           | PyTorch (forecasting, risk prediction), scikit-learn (Isolation Forest for threat detection) |
| Web frontend         | React 18, Vite, Chakra UI, Ethers.js 6, Recharts                                             |
| Mobile frontend      | React Native, Expo, React Navigation                                                         |
| Infrastructure       | Docker, Docker Compose, Kubernetes, Terraform (an AWS KMS key), Ansible                      |
| Monitoring / secrets | Prometheus, Grafana, the Elastic stack (Elasticsearch, Kibana, Filebeat), HashiCorp Vault    |
| CI/CD                | GitHub Actions                                                                               |
| Testing              | pytest (backend), Foundry (contracts), React Testing Library (web), Jest (mobile)            |

PostgreSQL is a real dependency but is not provisioned by the included Docker Compose file; point `DATABASE_URL` at an instance you run yourself.

## Architecture

```text
Clients
  ├── web-frontend (React)               ── HTTP/JSON ──┐
  └── mobile-frontend (React Native)     ── HTTP/JSON ──┤
                                                        ▼
Backend (FastAPI)
  ├── Endpoints (/api/v1/*)  health, auth, users, portfolio, transactions,
  │                          analytics, markets, compliance, risk, predict
  ├── Middleware             security, CORS, trusted-host, rate limit
  ├── Services               portfolio, risk, collateral engine, KYC/AML,
  │                          security (threat detection)
  └── Data layer              PostgreSQL (async SQLAlchemy + Alembic), Redis
                                                        (no on-chain calls: web3.py is unused)

Blockchain (Foundry / Solidity 0.8, deployed independently per network)
  SyntheticAssetFactory (Chainlink oracle + Any-API) · LiquidityPoolManager
  SyntheticLiquidationEngine · FluxionGovernanceToken
  Zero-knowledge: price_commitment.circom + Groth16Verifier.sol

Research library (code/ml_models)
  forecasting · financial risk predictor · liquidity model · anomaly detection
  (PyTorch / scikit-learn, unit-tested, not called by the live API)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detail.

## Installation and Setup

Prerequisites: Foundry, Python 3.11+, and Node.js 20+. Docker is optional.

```bash
git clone https://github.com/quantsingularity/Fluxion.git
cd Fluxion

# Blockchain
cd code/blockchain
forge install

# Backend
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Web frontend
cd ../../web-frontend
npm install

# Mobile frontend
cd ../mobile-frontend
npm install
```

Full, environment-specific instructions are in [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Running the Stack

```bash
# 1) Supporting services (from infrastructure/, Docker required; provide your own PostgreSQL)
docker compose up -d redis vault

# 2) Local chain (from code/blockchain)
anvil                              # local chain at http://127.0.0.1:8545

# 3) Backend (from code/backend, venv active)
uvicorn app.main:app --reload      # serves http://0.0.0.0:8000, docs at /docs

# 4) Web dashboard (from web-frontend)
npm run dev                        # http://localhost:5173 (Vite default)

# 5) Mobile app (from mobile-frontend)
npm start                          # press w for web, a for Android, i for iOS
```

See [docs/USAGE.md](docs/USAGE.md) and [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## API Surface

Base URL `http://localhost:8000`. Interactive docs at `/docs` (Swagger) and `/redoc`.

| Group        | Prefix                              | Highlights                                                              |
| :----------- | :---------------------------------- | :---------------------------------------------------------------------- |
| Health       | `/api/v1/health`                    | Basic, detailed, readiness, and liveness checks                         |
| Auth         | `/api/v1/auth`                      | `register`, `login`, `refresh`, `logout`, `me`, `mfa/setup`, `api-keys` |
| Users        | `/api/v1/users`                     | `me`, `me/profile`, `me/preferences`, deactivate account                |
| Portfolio    | `/api/v1/portfolio`                 | list, `{id}`, `{id}/performance`, `{id}/assets`                         |
| Transactions | `/api/v1/transactions`              | list/create, `{id}`, `{id}/cancel`                                      |
| Analytics    | `/api/v1/analytics`                 | overview, risk, compliance                                              |
| Markets      | `/api/v1/markets`                   | pools, synthetic assets, tradable assets (public read access)           |
| Compliance   | `/api/v1/kyc`, `/api/v1/compliance` | `kyc/initiate`, `kyc/document`, `kyc/biometric`, `compliance/status`    |
| Risk         | `/api/v1/risk`                      | `assessment/{user_id}`, `monitor`, `alerts`, `report`                   |
| Predict      | `/api/v1/predict`                   | Deterministic placeholder forecast, not wired to the ml_models library  |

Full request and response shapes are in [docs/API.md](docs/API.md).

## Testing

```bash
# Smart contracts (from code/blockchain)
forge test

# Backend (from code/backend)
pytest

# Web (from web-frontend)
npm test

# Mobile (from mobile-frontend)
npm test
```

The backend suite includes unit tests for auth, collateralization, the data pipeline, and the user service, plus integration tests for the auth endpoints. The Foundry suite covers each Solidity contract individually, including the Groth16 verifier. Neither the web nor the mobile suite currently includes end-to-end tests.

## CI/CD Pipeline

GitHub Actions (`.github/workflows/cicd.yml`) runs five jobs on push, pull request, and manual dispatch:

| Job                            | Depends on          | What it does                                                                                        |
| :----------------------------- | :------------------ | :-------------------------------------------------------------------------------------------------- |
| Code Quality Checks            | -                   | Python formatter checks (autoflake, black) and a repository-wide Prettier check, including Solidity |
| Backend Tests                  | Code Quality Checks | Runs the pytest suite with coverage and uploads the coverage report as an artifact                  |
| Web-Frontend Test & Build      | Code Quality Checks | Runs the frontend test suite and produces the production build                                      |
| Mobile-Frontend Test & Build   | Code Quality Checks | Runs the Jest suite and produces the Expo web export                                                |
| Smart Contracts Compile & Test | Code Quality Checks | Installs Foundry dependencies, compiles the contracts, and runs `forge test` with a gas report      |

## Documentation

| Document                                           | Contents                               |
| :------------------------------------------------- | :------------------------------------- |
| [docs/README.md](docs/README.md)                   | Documentation index                    |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)       | System architecture                    |
| [docs/API.md](docs/API.md)                         | REST API reference                     |
| [docs/INSTALLATION.md](docs/INSTALLATION.md)       | Setup for all components               |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md)     | Environment variables and config       |
| [docs/USAGE.md](docs/USAGE.md)                     | Running and using the platform         |
| [docs/CLI.md](docs/CLI.md)                         | Helper scripts reference               |
| [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md)   | Feature status, implemented vs planned |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes                |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)       | Contribution guide                     |
| [docs/examples/](docs/examples/)                   | Worked examples                        |

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
