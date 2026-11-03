# CLI Reference

Complete reference for Fluxion command-line tools and automation scripts.

## Table of Contents

- [Overview](#overview)
- [Installation Scripts](#installation-scripts)
- [Deployment Scripts](#deployment-scripts)
- [Testing Scripts](#testing-scripts)
- [AI/ML Pipeline](#aiml-pipeline)
- [Monitoring Scripts](#monitoring-scripts)
- [Utility Scripts](#utility-scripts)

## Overview

Fluxion provides a comprehensive set of CLI tools and automation scripts located in the `scripts/` directory:

| Script                     | Purpose                      | Complexity   |
| -------------------------- | ---------------------------- | ------------ |
| `setup_fluxion_env.sh`     | Environment setup            | Beginner     |
| `run_fluxion.sh`           | Start services               | Beginner     |
| `test_fluxion.sh`          | Run test suite               | Beginner     |
| `deploy_multi_env.sh`      | Multi-environment deployment | Advanced     |
| `cross_chain_test.sh`      | Cross-chain testing          | Advanced     |
| `ai_ml_pipeline.sh`        | AI/ML model pipeline         | Advanced     |
| `monitoring_setup.sh`      | Monitoring infrastructure    | Advanced     |
| `lint-all.sh`              | Code quality checks          | Intermediate |
| `build_web_frontend.sh`    | Build web frontend           | Intermediate |
| `build_mobile_frontend.sh` | Build mobile app             | Intermediate |

## Installation Scripts

### setup_fluxion_env.sh

Initialize development environment with all dependencies.

**Usage:**

```bash
./scripts/setup_fluxion_env.sh [OPTIONS]
```

**Options:**

| Flag                | Description                              | Default | Example             |
| ------------------- | ---------------------------------------- | ------- | ------------------- |
| `--skip-python`     | Skip Python environment setup            | false   | `--skip-python`     |
| `--skip-node`       | Skip Node.js environment setup           | false   | `--skip-node`       |
| `--skip-blockchain` | Skip blockchain tools setup              | false   | `--skip-blockchain` |
| `--clean`           | Clean existing environments before setup | false   | `--clean`           |

**Examples:**

```bash
# Full setup
./scripts/setup_fluxion_env.sh

# Setup only backend
./scripts/setup_fluxion_env.sh --skip-node --skip-blockchain

# Clean and rebuild all environments
./scripts/setup_fluxion_env.sh --clean
```

**What it does:**

1. Checks system prerequisites
2. Creates Python virtual environment
3. Installs Python dependencies
4. Installs Node.js dependencies (frontend and mobile)
5. Installs Foundry (if not present)
6. Sets up configuration files from templates
7. Initializes database (if configured)

### run_fluxion.sh

Start all Fluxion services.

**Usage:**

```bash
./scripts/run_fluxion.sh [COMPONENT]
```

**Arguments:**

| Component  | Description        | Port     |
| ---------- | ------------------ | -------- |
| (none)     | Start all services | Multiple |
| `backend`  | Backend API only   | 8000     |
| `frontend` | Web frontend only  | 5173     |
| `mobile`   | Mobile dev server  | 19000    |

**Examples:**

```bash
# Start all services
./scripts/run_fluxion.sh

# Start only backend
./scripts/run_fluxion.sh backend

# Start only frontend
./scripts/run_fluxion.sh frontend
```

**Services Started:**

- Backend API (FastAPI): `http://localhost:8000`
- Frontend (Vite): `http://localhost:5173`
- API Documentation: `http://localhost:8000/docs`

## Deployment Scripts

### deploy_multi_env.sh

Deploy Fluxion to multiple environments and blockchain networks.

**Usage:**

```bash
./scripts/deploy_multi_env.sh [OPTIONS]
```

**Options:**

| Flag               | Description                           | Values                                | Required          | Example                 |
| ------------------ | ------------------------------------- | ------------------------------------- | ----------------- | ----------------------- |
| `-e, --env`        | Target environment                    | development, staging, production      | Yes               | `-e staging`            |
| `-n, --networks`   | Blockchain networks (comma-separated) | ethereum, polygon, arbitrum, optimism | Yes               | `-n ethereum,polygon`   |
| `-c, --components` | Components to deploy                  | backend, frontend, blockchain, all    | No (default: all) | `-c backend,blockchain` |
| `--test`           | Run tests before deployment           | flag                                  | No                | `--test`                |
| `--skip-backup`    | Skip pre-deployment backup            | flag                                  | No                | `--skip-backup`         |
| `--dry-run`        | Simulate deployment without executing | flag                                  | No                | `--dry-run`             |
| `-h, --help`       | Show help message                     | flag                                  | No                | `-h`                    |

**Examples:**

```bash
# Deploy everything to staging on Ethereum and Polygon
./scripts/deploy_multi_env.sh -e staging -n ethereum,polygon

# Deploy only backend to production with tests
./scripts/deploy_multi_env.sh -e production -n ethereum -c backend --test

# Dry run deployment to see what would happen
./scripts/deploy_multi_env.sh -e production -n ethereum,polygon,arbitrum --dry-run

# Deploy frontend only
./scripts/deploy_multi_env.sh -e staging -n ethereum -c frontend
```

**Deployment Steps:**

1. Validates environment configuration
2. Runs pre-deployment tests (if `--test` specified)
3. Creates deployment backup (unless `--skip-backup`)
4. Builds components (smart contracts, backend, frontend)
5. Deploys to specified networks
6. Runs post-deployment verification
7. Creates deployment record
8. Sends notifications (if configured)

**Environment Configuration:**

Create config files in `infrastructure/deployment/configs/`:

```bash
# Example: infrastructure/deployment/configs/staging.env
ENVIRONMENT=staging
RPC_URL_ETHEREUM=https://eth-sepolia.alchemyapi.io/v2/YOUR-KEY
RPC_URL_POLYGON=https://polygon-mumbai.alchemyapi.io/v2/YOUR-KEY
DEPLOYER_PRIVATE_KEY=0x...
```

## Testing Scripts

### test_fluxion.sh

Run comprehensive test suite across all components.

**Usage:**

```bash
./scripts/test_fluxion.sh [OPTIONS]
```

**Options:**

| Flag            | Description                | Example         |
| --------------- | -------------------------- | --------------- |
| `--unit`        | Run only unit tests        | `--unit`        |
| `--integration` | Run only integration tests | `--integration` |
| `--e2e`         | Run only end-to-end tests  | `--e2e`         |
| `--coverage`    | Generate coverage report   | `--coverage`    |
| `--verbose`     | Verbose output             | `--verbose`     |

**Examples:**

```bash
# Run all tests
./scripts/test_fluxion.sh

# Run unit tests only
./scripts/test_fluxion.sh --unit

# Run tests with coverage report
./scripts/test_fluxion.sh --coverage

# Run integration and e2e tests
./scripts/test_fluxion.sh --integration --e2e
```

**Test Components:**

- Smart Contract Tests (Foundry): 90% coverage
- Backend API Tests (Pytest): 83% coverage
- Frontend Tests (Jest): 78% coverage
- Integration Tests: Cross-component workflows
- E2E Tests: Full user journeys

### cross_chain_test.sh

Specialized testing for cross-chain functionality.

**Usage:**

```bash
./scripts/cross_chain_test.sh [OPTIONS]
```

**Options:**

| Flag             | Description              | Values                                | Example               |
| ---------------- | ------------------------ | ------------------------------------- | --------------------- |
| `-n, --networks` | Networks to test         | ethereum, polygon, arbitrum, optimism | `-n ethereum,polygon` |
| `-t, --types`    | Test types               | unit, integration, e2e, messaging     | `-t unit,integration` |
| `-p, --parallel` | Run tests in parallel    | flag                                  | `-p`                  |
| `--local`        | Use local test networks  | flag                                  | `--local`             |
| `--report`       | Generate detailed report | flag                                  | `--report`            |

**Examples:**

```bash
# Test Ethereum and Polygon integration
./scripts/cross_chain_test.sh -n ethereum,polygon -t integration

# Run all test types in parallel
./scripts/cross_chain_test.sh -n ethereum,polygon,arbitrum -t unit,integration,e2e -p

# Test on local networks with report
./scripts/cross_chain_test.sh -n ethereum,polygon --local --report
```

**Test Scenarios:**

1. Cross-chain messaging (CCIP)
2. Asset bridging
3. Liquidity synchronization
4. Price oracle consistency
5. Transaction finality
6. Failure recovery

## AI/ML Pipeline

### ai_ml_pipeline.sh

Train, evaluate, and deploy AI/ML models.

**Usage:**

```bash
./scripts/ai_ml_pipeline.sh [OPTIONS]
```

**Options:**

| Flag            | Description                | Values                                                                                 | Example                      |
| --------------- | -------------------------- | -------------------------------------------------------------------------------------- | ---------------------------- |
| `-m, --models`  | Models to train            | liquidity_prediction, price_forecasting, volatility_modeling, arbitrage_detection, all | `-m liquidity_prediction`    |
| `--data`        | Data source path           | Path to training data                                                                  | `--data data/historical.csv` |
| `--gpu`         | Enable GPU acceleration    | flag                                                                                   | `--gpu`                      |
| `--distributed` | Distributed training       | flag                                                                                   | `--distributed`              |
| `--tune`        | Hyperparameter tuning      | flag                                                                                   | `--tune`                     |
| `--evaluate`    | Evaluate model performance | flag                                                                                   | `--evaluate`                 |
| `--deploy`      | Deploy after training      | flag                                                                                   | `--deploy`                   |
| `--epochs`      | Training epochs            | integer                                                                                | `--epochs 100`               |

**Available Models:**

| Model                | Purpose                   | Input Features               | Output               | Example Path                              |
| -------------------- | ------------------------- | ---------------------------- | -------------------- | ----------------------------------------- |
| liquidity_prediction | Predict pool liquidity    | Historical TVL, volume, fees | Future liquidity     | `code/ml_models/train_liquidity_model.py` |
| price_forecasting    | Asset price prediction    | OHLCV, volume, sentiment     | Price forecast       | `code/ml_models/forecasting_models.py`    |
| volatility_modeling  | Risk assessment           | Historical returns, volume   | Volatility estimates | `code/ml_models/models.py`                |
| arbitrage_detection  | Cross-chain opportunities | Multi-chain prices, fees     | Arbitrage signals    | `code/ml_models/anomaly_detection.py`     |

**Examples:**

```bash
# Train liquidity prediction model with GPU
./scripts/ai_ml_pipeline.sh -m liquidity_prediction --gpu --deploy

# Train all models with hyperparameter tuning
./scripts/ai_ml_pipeline.sh -m all --tune --gpu --epochs 200

# Evaluate price forecasting model
./scripts/ai_ml_pipeline.sh -m price_forecasting --evaluate

# Train with custom data and deploy
./scripts/ai_ml_pipeline.sh -m volatility_modeling --data custom_data.csv --deploy
```

**Training Pipeline:**

1. Data validation and preprocessing
2. Feature engineering
3. Model training (with optional GPU)
4. Hyperparameter tuning (if `--tune`)
5. Model evaluation on validation set
6. Performance metrics calculation
7. Model serialization
8. Deployment to backend (if `--deploy`)

**Output:**

- Trained model files: `code/ml_models/models/`
- Training logs: `code/ml_models/logs/`
- Evaluation metrics: `code/ml_models/reports/`

## Monitoring Scripts

### monitoring_setup.sh

Set up comprehensive monitoring infrastructure.

**Usage:**

```bash
./scripts/monitoring_setup.sh [OPTIONS]
```

**Options:**

| Flag               | Description                 | Values                                       | Example               |
| ------------------ | --------------------------- | -------------------------------------------- | --------------------- |
| `-e, --env`        | Environment                 | development, staging, production             | `-e production`       |
| `-c, --components` | Components to monitor       | backend, blockchain, database, frontend, all | `-c backend,database` |
| `-a, --alerts`     | Alert channels              | slack, email, pagerduty                      | `-a slack,email`      |
| `--dashboards`     | Generate Grafana dashboards | flag                                         | `--dashboards`        |
| `--install`        | Install monitoring tools    | flag                                         | `--install`           |

**Examples:**

```bash
# Set up production monitoring with all components
./scripts/monitoring_setup.sh -e production -c all -a slack,email --dashboards

# Monitor only backend and database in staging
./scripts/monitoring_setup.sh -e staging -c backend,database -a slack

# Install monitoring tools
./scripts/monitoring_setup.sh --install
```

**Monitoring Stack:**

- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Visualization dashboards (port 3001)
- **AlertManager**: Alert routing
- **Node Exporter**: System metrics
- **Custom Exporters**: Application-specific metrics

**Metrics Collected:**

| Component  | Metrics                                               | Dashboard         |
| ---------- | ----------------------------------------------------- | ----------------- |
| Backend    | Request rate, latency, error rate, active connections | API Performance   |
| Blockchain | Block height, gas prices, transaction success rate    | Blockchain Status |
| Database   | Query time, connection pool, cache hit rate           | Database Health   |
| Pools      | TVL, volume, utilization, APY                         | Liquidity Pools   |
| AI Models  | Prediction accuracy, inference time, model drift      | ML Performance    |

**Access Points:**

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (default login: admin/admin)
- AlertManager: `http://localhost:9093`

## Utility Scripts

### lint-all.sh

Run all code quality checks and linters.

**Usage:**

```bash
./scripts/lint-all.sh [OPTIONS]
```

**Options:**

| Flag               | Description                    | Example               |
| ------------------ | ------------------------------ | --------------------- |
| `--fix`            | Auto-fix issues where possible | `--fix`               |
| `--strict`         | Fail on warnings               | `--strict`            |
| `--component COMP` | Lint specific component        | `--component backend` |

**Examples:**

```bash
# Lint all code
./scripts/lint-all.sh

# Lint and auto-fix
./scripts/lint-all.sh --fix

# Lint only Python backend
./scripts/lint-all.sh --component backend
```

**Linters Used:**

| Language              | Tools                             | Purpose                          |
| --------------------- | --------------------------------- | -------------------------------- |
| Python                | black, flake8, mypy, isort        | Formatting, style, type checking |
| JavaScript/TypeScript | ESLint, Prettier                  | Style, best practices            |
| Solidity              | solhint, prettier-plugin-solidity | Smart contract quality           |
| YAML/JSON             | yamllint, jsonlint                | Configuration validation         |

### build_web_frontend.sh

Build web frontend for production.

**Usage:**

```bash
./scripts/build_web_frontend.sh [OPTIONS]
```

**Options:**

| Flag        | Description         | Example     |
| ----------- | ------------------- | ----------- |
| `--prod`    | Production build    | `--prod`    |
| `--analyze` | Analyze bundle size | `--analyze` |

**Examples:**

```bash
# Development build
./scripts/build_web_frontend.sh

# Production build with analysis
./scripts/build_web_frontend.sh --prod --analyze
```

**Output:** `web-frontend/dist/`

### build_mobile_frontend.sh

Build mobile application.

**Usage:**

```bash
./scripts/build_mobile_frontend.sh [PLATFORM]
```

**Arguments:**

| Platform  | Description            | Output      |
| --------- | ---------------------- | ----------- |
| `ios`     | iOS build (macOS only) | `.ipa` file |
| `android` | Android build          | `.apk` file |
| `both`    | Both platforms         | Both files  |

**Examples:**

```bash
# Build for Android
./scripts/build_mobile_frontend.sh android

# Build for both platforms
./scripts/build_mobile_frontend.sh both
```

## Script Configuration

### Environment Variables

Most scripts respect these environment variables:

```bash
# General
FLUXION_ENV=production          # Environment: development, staging, production
VERBOSE=true                     # Enable verbose output
DRY_RUN=false                   # Simulate without executing

# Deployment
DEPLOYER_PRIVATE_KEY=0x...      # Deployer wallet private key
RPC_URL_ETHEREUM=https://...    # Ethereum RPC endpoint
RPC_URL_POLYGON=https://...     # Polygon RPC endpoint

# Monitoring
SLACK_WEBHOOK_URL=https://...   # Slack alert webhook
SMTP_SERVER=smtp.gmail.com      # Email alert server
SMTP_USER=alerts@example.com    # Email sender

# AI/ML
CUDA_VISIBLE_DEVICES=0          # GPU devices for training
ML_DATA_PATH=/data/training     # Training data location
```

### Configuration Files

Scripts load configuration from:

```text
infrastructure/
├── deployment/configs/
│   ├── development.env
│   ├── staging.env
│   └── production.env
├── test/configs/
│   └── networks.json
├── monitoring/configs/
│   ├── prometheus.yml
│   └── alertmanager.yml
└── ai/configs/
    └── training.yaml
```

## Exit Codes

All scripts follow standard exit code conventions:

| Code | Meaning              |
| ---- | -------------------- |
| 0    | Success              |
| 1    | General error        |
| 2    | Invalid arguments    |
| 3    | Missing dependencies |
| 4    | Configuration error  |
| 5    | Network error        |
| 10   | Test failures        |

## Logging

Scripts log to:

- **Console**: Real-time output
- **Log files**: `logs/scripts/<script-name>-<timestamp>.log`
- **Syslog** (production): For centralized logging

## Best Practices

1. **Always run tests before deployment**: Use `--test` flag
2. **Use dry-run for production**: Verify deployment plan first
3. **Monitor script execution**: Check logs for issues
4. **Keep configurations in version control**: Except secrets
5. **Use environment-specific configs**: Don't hardcode values

## Troubleshooting

| Issue               | Solution                                                |
| ------------------- | ------------------------------------------------------- |
| Permission denied   | Make script executable: `chmod +x script.sh`            |
| Command not found   | Install prerequisites: `./scripts/setup_fluxion_env.sh` |
| Configuration error | Check `.env` files and paths                            |
| Network timeout     | Check RPC URLs and network connectivity                 |
| GPU not detected    | Install CUDA drivers, check `CUDA_VISIBLE_DEVICES`      |

For more help: `./scripts/<script-name>.sh --help`
