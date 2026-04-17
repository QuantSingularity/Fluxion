# Fluxion

![CI/CD Status](https://img.shields.io/github/actions/workflow/status/quantsingularity/Fluxion/cicd.yml?branch=main&label=CI/CD&logo=github)
[![Test Coverage](https://img.shields.io/badge/coverage-83%25-brightgreen)](https://github.com/quantsingularity/Fluxion/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Synthetic Asset Liquidity Engine

Fluxion is a cutting-edge synthetic asset liquidity engine that leverages zero-knowledge proofs and cross-chain technology to provide efficient, secure, and scalable liquidity for synthetic assets across multiple blockchain networks.

<div align="center">
  <img src="docs/images/Fluxion_dashboard.bmp" alt="Fluxion Dashboard" width="80%">
</div>

---

## Table of Contents

| Section                                 | Description                                                             |
| :-------------------------------------- | :---------------------------------------------------------------------- |
| [Overview](#overview)                   | High-level summary of the platform's value proposition.                 |
| [Project Structure](#project-structure) | Overview of the repository layout and major directories.                |
| [Key Features](#key-features)           | Detailed breakdown of core functionalities.                             |
| [Tech Stack](#tech-stack)               | Technologies used across all layers of the application.                 |
| [Architecture](#architecture)           | Component-based view of the system's structure.                         |
| [Installation](#installation)           | Instructions for setting up the development environment.                |
| [Deployment](#deployment)               | Guide for local, testnet, and production deployment.                    |
| [Testing](#testing)                     | Overview of the comprehensive testing strategy.                         |
| [CI/CD Pipeline](#cicd-pipeline)        | Details on the automated continuous integration and deployment process. |
| [Documentation](#documentation)         | References to detailed guides, API docs, and architecture resources.    |
| [Contributing](#contributing)           | Guidelines for community contributions.                                 |
| [License](#license)                     | Licensing information.                                                  |

---

## Overview

Fluxion revolutionizes synthetic asset trading by providing deep, cross-chain liquidity through a combination of zero-knowledge proofs, AI-driven market making, and advanced risk management. The platform enables the creation, trading, and settlement of synthetic assets with minimal slippage, reduced fees, and enhanced security across multiple blockchain networks.

## Project Structure

The project is organized into several main components:

```
Fluxion/
├── code/                   # Core backend logic, services, and shared utilities
├── docs/                   # Project documentation
├── infrastructure/         # DevOps, deployment, and infra-related code
├── mobile-frontend/        # Mobile application
├── web-frontend/           # Web dashboard
├── scripts/                # Automation, setup, and utility scripts
├── LICENSE                 # License information
├── README.md               # Project overview and instructions
└── tools/                  # Formatter configs, linting tools, and dev utilities
```

## Key Features

### Synthetic Asset Creation

| Feature                              | Description                                                                  |
| :----------------------------------- | :--------------------------------------------------------------------------- |
| **Asset Tokenization**               | Create synthetic versions of real-world assets (stocks, commodities, forex). |
| **Custom Index Creation**            | Build and deploy custom synthetic indices.                                   |
| **Yield-Bearing Synthetics**         | Synthetic assets that generate yield.                                        |
| **Governance-Controlled Parameters** | Community governance of collateralization ratios and fees.                   |
| **Permissionless Listing**           | Open framework for adding new synthetic assets.                              |

### Zero-Knowledge Layer

| Feature                       | Description                                              |
| :---------------------------- | :------------------------------------------------------- |
| **zkEVM Integration**         | Scalable and private synthetic asset trading.            |
| **Batched Settlements**       | Efficient transaction processing with reduced gas costs. |
| **Privacy-Preserving Trades** | Confidential trading without revealing positions.        |
| **Proof Generation**          | Fast and efficient zero-knowledge proof generation.      |
| **Verifiable Transactions**   | Cryptographic verification of all trades.                |

### Cross-Chain Infrastructure

| Feature                       | Description                                                          |
| :---------------------------- | :------------------------------------------------------------------- |
| **Multi-Chain Deployment**    | Support for 10+ EVM-compatible chains.                               |
| **Unified Liquidity**         | Shared liquidity pools across multiple networks.                     |
| **Cross-Chain Messaging**     | Secure communication between blockchain networks via Chainlink CCIP. |
| **Chain-Agnostic Trading**    | Trade synthetic assets regardless of underlying blockchain.          |
| **Optimized Bridge Security** | Enhanced security for cross-chain asset transfers.                   |

### AI-Powered Market Making

| Feature                         | Description                                                         |
| :------------------------------ | :------------------------------------------------------------------ |
| **Dynamic Liquidity Provision** | Intelligent allocation of liquidity across pools.                   |
| **Predictive Price Modeling**   | ML models for synthetic asset price prediction.                     |
| **Volatility Forecasting**      | Advanced volatility models for risk management.                     |
| **Arbitrage Detection**         | Identification and exploitation of cross-chain price discrepancies. |
| **Adaptive Fee Structure**      | ML-optimized fees based on market conditions.                       |

## Tech Stack

| Component           | Technology                                                | Purpose                                                                                   |
| :------------------ | :-------------------------------------------------------- | :---------------------------------------------------------------------------------------- |
| **Blockchain**      | Solidity 0.8, Foundry, zkSync                             | Smart contract development, testing, and zero-knowledge proofs.                           |
| **Cross-Chain**     | Chainlink CCIP                                            | Secure, reliable cross-chain communication and data transfer.                             |
| **Backend**         | Python 3.10 (FastAPI), Celery, gRPC, WebSocket            | High-performance API, asynchronous task processing, and real-time data.                   |
| **AI/ML**           | PyTorch, Prophet, Scikit-learn, Ray                       | Deep learning, time series forecasting, statistical models, and distributed training.     |
| **Web Frontend**    | React 18 (TypeScript), Recharts, ethers.js 6, TailwindCSS | User interface, data visualization, blockchain interaction, and styling.                  |
| **Mobile Frontend** | React Native (Expo)                                       | Cross-platform mobile application development.                                            |
| **Database**        | TimescaleDB, Redis Stack, PostgreSQL, IPFS                | Time-series data, caching/real-time features, relational data, and decentralized storage. |
| **Infrastructure**  | Kubernetes, Prometheus, Grafana, ArgoCD, Terraform        | Container orchestration, monitoring, GitOps deployment, and infrastructure as code.       |

## Architecture

Fluxion follows a modular, microservices-based architecture, organized into distinct layers for scalability and maintainability.

| Component Layer        | Sub-Components                                                                    | Primary Function                                                                                    |
| :--------------------- | :-------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------- |
| **Frontend Layer**     | Trading Interface, Portfolio Dashboard, Analytics Tools, Admin Panel              | User interaction, data visualization, and administrative control.                                   |
| **API Gateway**        | Authentication, Rate Limiting, Request Routing, WebSocket Server                  | Single entry point for all external traffic, handling security and routing.                         |
| **Cross-Chain Router** | CCIP Integration, Message Passing, Asset Bridging, Chain Monitoring               | Manages secure, reliable communication and asset transfer between different blockchains.            |
| **zkEVM Sequencer**    | Proof Generation, Batch Processing, State Management, Verification System         | Handles the zero-knowledge proof generation and batch settlement process for scalability.           |
| **Liquidity Pools**    | AMM Pools, Order Books, Yield Strategies, Rebalancing Engine                      | Core mechanism for providing liquidity and facilitating synthetic asset trades.                     |
| **Settlement Layer**   | Transaction Finalization, Fee Collection, Dispute Resolution, Oracle Integration  | Finalizes trades, manages fees, and integrates with external data sources.                          |
| **Risk Engine**        | Position Monitoring, Liquidation Manager, Insurance Fund, Circuit Breakers        | Monitors protocol health, manages liquidations, and protects the system from extreme market events. |
| **AI Models**          | Liquidity Prediction, Price Forecasting, Volatility Modeling, Arbitrage Detection | Provides intelligent insights and automation for market making and risk management.                 |
| **Data Layer**         | Market Data, User Positions, Historical Trades, Protocol Metrics                  | Persistent storage and retrieval of all critical protocol data.                                     |

## Installation

The project uses a monorepo structure with separate directories for the blockchain, backend, and frontend components.

### Prerequisites

| Prerequisite       | Version/Requirement           |
| :----------------- | :---------------------------- |
| **Blockchain**     | Foundry (for smart contracts) |
| **Backend**        | Python 3.10+, pip             |
| **Web Frontend**   | Node.js (v18+), npm           |
| **Infrastructure** | Git, Docker, Docker Compose   |

### Setup Steps

| Step                             | Command                                                                   | Description                                                           |
| :------------------------------- | :------------------------------------------------------------------------ | :-------------------------------------------------------------------- |
| **1. Clone Repository**          | `git clone https://github.com/quantsingularity/Fluxion.git && cd Fluxion` | Download the source code.                                             |
| **2. Install Blockchain Deps**   | `cd code/blockchain && forge install`                                     | Install dependencies for smart contracts.                             |
| **3. Install Backend Deps**      | `cd ../backend && pip install -r requirements.txt`                        | Install Python dependencies.                                          |
| **4. Install Web Frontend Deps** | `cd ../web-frontend && npm install`                                       | Install Node.js dependencies for the web application.                 |
| **5. Configure Environment**     | `cp .env.example .env`                                                    | Create the environment file and add blockchain RPC URLs and API keys. |

## Deployment

### Local Development

| Component                 | Directory               | Command                     | Access Point                      |
| :------------------------ | :---------------------- | :-------------------------- | :-------------------------------- |
| **All Services (Docker)** | `infrastructure/docker` | `docker-compose up -d`      | N/A                               |
| **Blockchain Node**       | `code/blockchain`       | `forge node`                | RPC Endpoint                      |
| **Backend API**           | `code/backend`          | `uvicorn main:app --reload` | `http://localhost:8000`           |
| **Web Frontend**          | `web-frontend`          | `npm start`                 | `http://localhost:3000` (default) |

### Testnet & Production Deployment

| Environment               | Tool                    | Command/Process                                                                              | Description                                                   |
| :------------------------ | :---------------------- | :------------------------------------------------------------------------------------------- | :------------------------------------------------------------ |
| **Testnet Deployment**    | Foundry, Docker Compose | `forge script script/Deploy.s.sol --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast` | Deploys smart contracts to a specified testnet.               |
| **Testnet Services**      | Docker Compose          | `docker-compose -f docker-compose.testnet.yml up -d`                                         | Starts backend services configured for testnet interaction.   |
| **Production Deployment** | Kubernetes              | `kubectl apply -f infrastructure/k8s/`                                                       | Deploys the entire application stack to a Kubernetes cluster. |
| **GitOps Deployment**     | ArgoCD                  | Managed via ArgoCD configuration files in `infrastructure/kubernetes/`                       | Continuous deployment using GitOps principles.                |

## Testing

The project maintains comprehensive test coverage across all components to ensure reliability and security.

### Test Coverage Summary

| Component           | Coverage | Status |
| :------------------ | :------- | :----- |
| Smart Contracts     | 90%      | ✅     |
| zkEVM Integration   | 85%      | ✅     |
| Cross-Chain Router  | 82%      | ✅     |
| Liquidity Pools     | 88%      | ✅     |
| Settlement Layer    | 84%      | ✅     |
| Risk Engine         | 80%      | ✅     |
| AI Models           | 75%      | ✅     |
| Frontend Components | 78%      | ✅     |
| **Overall**         | **83%**  | ✅     |

### Testing Strategy

| Component           | Test Types                                                                      | Key Tools                          |
| :------------------ | :------------------------------------------------------------------------------ | :--------------------------------- |
| **Smart Contracts** | Unit, Integration, Fuzz, Security, Gas Optimization                             | Foundry, Slither, Mythril          |
| **Backend**         | API Endpoint, Service Layer Unit, Database Integration, WebSocket Communication | Pytest, Mocking Libraries          |
| **Web Frontend**    | Component, Integration, End-to-End (E2E), Web3 Integration                      | React Testing Library, Cypress     |
| **Mobile Frontend** | Unit, Integration, E2E                                                          | Jest, React Native Testing Library |

### Running Tests

| Component           | Directory         | Command             |
| :------------------ | :---------------- | :------------------ |
| **Smart Contracts** | `code/blockchain` | `forge test`        |
| **Backend**         | `code/backend`    | `pytest`            |
| **Web Frontend**    | `web-frontend`    | `npm test`          |
| **Mobile Frontend** | `mobile-frontend` | `npm test`          |
| **All Tests**       | Root              | `./test_fluxion.sh` |

## CI/CD Pipeline

Fluxion uses GitHub Actions for continuous integration and deployment, ensuring a robust and automated software delivery lifecycle.

| Stage                | Control Area                    | Institutional-Grade Detail                                                              |
| :------------------- | :------------------------------ | :-------------------------------------------------------------------------------------- |
| **Formatting Check** | Change Triggers                 | Enforced on all `push` and `pull_request` events to `main` and `develop`                |
|                      | Manual Oversight                | On-demand execution via controlled `workflow_dispatch`                                  |
|                      | Source Integrity                | Full repository checkout with complete Git history for auditability                     |
|                      | Python Runtime Standardization  | Python 3.10 with deterministic dependency caching                                       |
|                      | Backend Code Hygiene            | `autoflake` to detect unused imports/variables using non-mutating diff-based validation |
|                      | Backend Style Compliance        | `black --check` to enforce institutional formatting standards                           |
|                      | Non-Intrusive Validation        | Temporary workspace comparison to prevent unauthorized source modification              |
|                      | Node.js Runtime Control         | Node.js 18 with locked dependency installation via `npm ci`                             |
|                      | Web Frontend Formatting Control | Prettier checks for web-facing assets                                                   |
|                      | Mobile Frontend Formatting      | Prettier enforcement for mobile application codebases                                   |
|                      | Documentation Governance        | Repository-wide Markdown formatting enforcement                                         |
|                      | Infrastructure Configuration    | Prettier validation for YAML/YML infrastructure definitions                             |
|                      | Compliance Gate                 | Any formatting deviation fails the pipeline and blocks merge                            |

## Documentation

| Document                    | Path                 | Description                                                    |
| :-------------------------- | :------------------- | :------------------------------------------------------------- |
| **README**                  | `README.md`          | High-level overview, project scope, and repository entry point |
| **Installation Guide**      | `INSTALLATION.md`    | Step-by-step installation and environment setup                |
| **API Reference**           | `API.md`             | Detailed documentation for all API endpoints                   |
| **CLI Reference**           | `CLI.md`             | Command-line interface usage, commands, and examples           |
| **User Guide**              | `USAGE.md`           | Comprehensive end-user guide, workflows, and examples          |
| **Architecture Overview**   | `ARCHITECTURE.md`    | System architecture, components, and design rationale          |
| **Configuration Guide**     | `CONFIGURATION.md`   | Configuration options, environment variables, and tuning       |
| **Feature Matrix**          | `FEATURE_MATRIX.md`  | Feature coverage, capabilities, and roadmap alignment          |
| **Contributing Guidelines** | `CONTRIBUTING.md`    | Contribution workflow, coding standards, and PR requirements   |
| **Troubleshooting**         | `TROUBLESHOOTING.md` | Common issues, diagnostics, and remediation steps              |

## Contributing

Contributions are welcome! Please follow these guidelines to submit a Pull Request.

| Step                | Description                                                               | Command/Action                                  |
| :------------------ | :------------------------------------------------------------------------ | :---------------------------------------------- |
| **1. Fork**         | Fork the repository to your personal GitHub account.                      | N/A                                             |
| **2. Branch**       | Create a new feature branch.                                              | `git checkout -b feature/your-feature-name`     |
| **3. Commit**       | Commit your changes with a descriptive message.                           | `git commit -m 'feat: add descriptive feature'` |
| **4. Push**         | Push your changes to your forked repository.                              | `git push origin feature/your-feature-name`     |
| **5. Pull Request** | Open a Pull Request against the `main` branch of the original repository. | GitHub UI                                       |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
