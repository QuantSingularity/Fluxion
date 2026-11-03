# Configuration Guide

Complete configuration reference for Fluxion, including environment variables, configuration files, and deployment settings.

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Database Setup](#database-setup)
- [Blockchain Tooling Configuration](#blockchain-tooling-configuration)
- [Security Configuration](#security-configuration)
- [AI/ML Model Configuration](#aiml-model-configuration)
- [Monitoring Configuration](#monitoring-configuration)
- [Environment-Specific Settings](#environment-specific-settings)

## Configuration Overview

Fluxion uses a layered configuration approach:

1. **Default values** (hardcoded in application)
2. **Configuration files** (YAML, JSON, .env)
3. **Environment variables** (highest priority)

Configuration precedence: **Environment Variables > Config Files > Defaults**

## Environment Variables

### Application Settings

| Option            | Type    | Default     | Description                                          | Where to set |
| ----------------- | ------- | ----------- | ---------------------------------------------------- | ------------ |
| `APP_ENV`         | string  | development | Environment: development, staging, production        | `.env` file  |
| `APP_NAME`        | string  | Fluxion     | Application name                                     | `.env` file  |
| `APP_VERSION`     | string  | 1.0.0       | Application version                                  | `.env` file  |
| `DEBUG`           | boolean | false       | Enable debug mode (disable in production)            | `.env` file  |
| `LOG_LEVEL`       | string  | INFO        | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL | `.env` file  |
| `ALLOWED_ORIGINS` | list    | \*          | CORS allowed origins (comma-separated)               | `.env` file  |
| `ALLOWED_HOSTS`   | list    | \*          | Trusted hosts (comma-separated)                      | `.env` file  |
| `SECRET_KEY`      | string  | -           | Application secret key (required)                    | `.env` file  |

**Example:**

```bash
APP_ENV=production
APP_NAME=Fluxion
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://app.fluxion.exchange,https://www.fluxion.exchange
ALLOWED_HOSTS=api.fluxion.exchange,api-staging.fluxion.exchange
SECRET_KEY=your-super-secret-key-change-this-in-production
```

### Database Configuration

| Option                  | Type    | Default                | Description                       | Where to set         |
| ----------------------- | ------- | ---------------------- | --------------------------------- | -------------------- |
| `DATABASE_URL`          | string  | -                      | Primary database URL (PostgreSQL) | `.env` file, env var |
| `DATABASE_READ_URL`     | string  | -                      | Read replica URL (optional)       | `.env` file, env var |
| `DATABASE_POOL_SIZE`    | integer | 20                     | Connection pool size              | `.env` file          |
| `DATABASE_MAX_OVERFLOW` | integer | 10                     | Max overflow connections          | `.env` file          |
| `DATABASE_POOL_TIMEOUT` | integer | 30                     | Connection timeout (seconds)      | `.env` file          |
| `DATABASE_ECHO`         | boolean | false                  | Log SQL queries (debug only)      | `.env` file          |
| `REDIS_URL`             | string  | redis://localhost:6379 | Redis connection URL              | `.env` file, env var |
| `REDIS_MAX_CONNECTIONS` | integer | 50                     | Redis connection pool size        | `.env` file          |
| `REDIS_DB`              | integer | 0                      | Redis database number             | `.env` file          |

**Example:**

```bash
# PostgreSQL
DATABASE_URL=postgresql://fluxion_user:secure_password@localhost:5432/fluxion_prod
DATABASE_READ_URL=postgresql://fluxion_reader:reader_pass@replica.example.com:5432/fluxion_prod
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=60

# Redis
REDIS_URL=redis://:redis_password@localhost:6379/0
REDIS_MAX_CONNECTIONS=100
REDIS_DB=0
```

### Blockchain Configuration

| Option                  | Type    | Default | Description                                  | Where to set         |
| ----------------------- | ------- | ------- | -------------------------------------------- | -------------------- |
| `ETHEREUM_RPC_URL`      | string  | -       | Ethereum RPC endpoint                        | `.env` file, env var |
| `POLYGON_RPC_URL`       | string  | -       | Polygon RPC endpoint                         | `.env` file, env var |
| `ARBITRUM_RPC_URL`      | string  | -       | Arbitrum RPC endpoint                        | `.env` file, env var |
| `OPTIMISM_RPC_URL`      | string  | -       | Optimism RPC endpoint                        | `.env` file, env var |
| `ZKSYNC_RPC_URL`        | string  | -       | zkSync RPC endpoint                          | `.env` file, env var |
| `DEPLOYER_PRIVATE_KEY`  | string  | -       | Contract deployer private key (NEVER commit) | env var only         |
| `OPERATOR_PRIVATE_KEY`  | string  | -       | Operator private key                         | env var only         |
| `GAS_PRICE_MULTIPLIER`  | float   | 1.1     | Gas price multiplier for faster transactions | `.env` file          |
| `CONFIRMATION_BLOCKS`   | integer | 6       | Required confirmations for finality          | `.env` file          |
| `CHAINLINK_CCIP_ROUTER` | string  | -       | Chainlink CCIP router address                | `.env` file          |

**Example:**

```bash
# RPC Endpoints
ETHEREUM_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/YOUR-API-KEY
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR-API-KEY
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR-API-KEY
OPTIMISM_RPC_URL=https://opt-mainnet.g.alchemy.com/v2/YOUR-API-KEY
ZKSYNC_RPC_URL=https://mainnet.era.zksync.io

# Wallet Keys (NEVER commit these to git!)
DEPLOYER_PRIVATE_KEY=0x...
OPERATOR_PRIVATE_KEY=0x...

# Transaction Settings
GAS_PRICE_MULTIPLIER=1.2
CONFIRMATION_BLOCKS=12

# Chainlink CCIP
CHAINLINK_CCIP_ROUTER=0x0BF3dE8c5D3e8A2B34D2BEeB17ABfCeBaf363A59
```

### Authentication & Security

| Option                          | Type    | Default | Description                            | Where to set         |
| ------------------------------- | ------- | ------- | -------------------------------------- | -------------------- |
| `JWT_SECRET`                    | string  | -       | JWT signing secret (required)          | `.env` file, env var |
| `JWT_ALGORITHM`                 | string  | HS256   | JWT algorithm                          | `.env` file          |
| `JWT_EXPIRATION_MINUTES`        | integer | 60      | JWT token expiration                   | `.env` file          |
| `REFRESH_TOKEN_EXPIRATION_DAYS` | integer | 30      | Refresh token expiration               | `.env` file          |
| `PASSWORD_MIN_LENGTH`           | integer | 12      | Minimum password length                | `.env` file          |
| `PASSWORD_REQUIRE_SPECIAL`      | boolean | true    | Require special characters in password | `.env` file          |
| `ENABLE_2FA`                    | boolean | true    | Enable two-factor authentication       | `.env` file          |
| `RATE_LIMIT_PER_MINUTE`         | integer | 100     | API rate limit per minute              | `.env` file          |
| `ENCRYPTION_KEY`                | string  | -       | Data encryption key (required)         | env var only         |
| `CORS_MAX_AGE`                  | integer | 3600    | CORS preflight cache time (seconds)    | `.env` file          |

**Example:**

```bash
# JWT Configuration
JWT_SECRET=your-jwt-secret-256-bits-minimum
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=30

# Password Policy
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_SPECIAL=true

# Security Features
ENABLE_2FA=true
RATE_LIMIT_PER_MINUTE=100

# Encryption
ENCRYPTION_KEY=your-encryption-key-keep-this-very-secret

# CORS
CORS_MAX_AGE=3600
```

### External Services

| Option                | Type   | Default | Description                | Where to set         |
| --------------------- | ------ | ------- | -------------------------- | -------------------- |
| `CHAINLINK_API_KEY`   | string | -       | Chainlink API key          | `.env` file, env var |
| `ALCHEMY_API_KEY`     | string | -       | Alchemy API key            | `.env` file, env var |
| `INFURA_API_KEY`      | string | -       | Infura API key             | `.env` file, env var |
| `ETHERSCAN_API_KEY`   | string | -       | Etherscan API key          | `.env` file, env var |
| `POLYGONSCAN_API_KEY` | string | -       | Polygonscan API key        | `.env` file, env var |
| `SENTRY_DSN`          | string | -       | Sentry error tracking DSN  | `.env` file, env var |
| `SLACK_WEBHOOK_URL`   | string | -       | Slack notification webhook | `.env` file, env var |
| `SENDGRID_API_KEY`    | string | -       | SendGrid email API key     | `.env` file, env var |

**Example:**

```bash
# Blockchain Infrastructure
CHAINLINK_API_KEY=your-chainlink-api-key
ALCHEMY_API_KEY=your-alchemy-api-key
INFURA_API_KEY=your-infura-api-key
ETHERSCAN_API_KEY=your-etherscan-api-key
POLYGONSCAN_API_KEY=your-polygonscan-api-key

# Monitoring & Alerts
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email
SENDGRID_API_KEY=your-sendgrid-api-key
```

### AI/ML Configuration

| Option                      | Type    | Default               | Description                   | Where to set |
| --------------------------- | ------- | --------------------- | ----------------------------- | ------------ |
| `ML_MODELS_PATH`            | string  | code/ml_models/models | Path to trained models        | `.env` file  |
| `ML_DATA_PATH`              | string  | data/ml               | Path to training data         | `.env` file  |
| `ML_ENABLE_GPU`             | boolean | false                 | Enable GPU acceleration       | `.env` file  |
| `ML_BATCH_SIZE`             | integer | 32                    | Training/inference batch size | `.env` file  |
| `ML_CACHE_SIZE`             | integer | 1000                  | Prediction cache size         | `.env` file  |
| `ML_RETRAIN_INTERVAL_HOURS` | integer | 168                   | Auto-retrain interval (hours) | `.env` file  |
| `CUDA_VISIBLE_DEVICES`      | string  | 0                     | GPU devices to use            | env var      |
| `TORCH_HOME`                | string  | ~/.cache/torch        | PyTorch cache directory       | env var      |

**Example:**

```bash
# Model Paths
ML_MODELS_PATH=/opt/fluxion/models
ML_DATA_PATH=/data/training

# Performance
ML_ENABLE_GPU=true
ML_BATCH_SIZE=64
ML_CACHE_SIZE=5000

# Training
ML_RETRAIN_INTERVAL_HOURS=168

# GPU Configuration
CUDA_VISIBLE_DEVICES=0,1
TORCH_HOME=/opt/torch_cache
```

## Configuration Files

### Backend Configuration (code/backend/config/settings.py)

Python-based configuration with Pydantic settings:

```python
from pydantic_settings import BaseSettings
from typing import List, Optional

class AppSettings(BaseSettings):
    APP_NAME: str = "Fluxion"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True

class DatabaseSettings(BaseSettings):
    DATABASE_URL: str
    DATABASE_READ_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    class Config:
        env_file = ".env"

class Settings:
    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()

settings = Settings()
```

### Smart Contract Configuration (code/blockchain/.env)

```bash
# Network Configuration
NETWORK=mainnet  # mainnet, testnet, localhost

# Deployment
DEPLOYER_ADDRESS=0x...
FACTORY_ADDRESS=0x...
POOL_MANAGER_ADDRESS=0x...

# Contract Parameters
COLLATERAL_RATIO=150  # 150%
LIQUIDATION_THRESHOLD=130  # 130%
FEE_BASIS_POINTS=30  # 0.3%
```

### Frontend Configuration (web-frontend/.env)

```bash
# API
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# Blockchain
VITE_CHAIN_ID=1
VITE_NETWORK_NAME=Ethereum Mainnet

# Features
VITE_ENABLE_ANALYTICS=true
VITE_SENTRY_DSN=https://...

# UI
VITE_THEME=dark
VITE_CURRENCY=USD
```

### Docker Compose Configuration (infrastructure/docker-compose.yml)

```yaml
version: "3.8"

services:
  backend:
    build: ./code/backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  frontend:
    build: ./web-frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=${API_URL}
    depends_on:
      - backend
    restart: unless-stopped

  postgres:
    image: timescale/timescaledb:latest-pg15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Database Setup

### PostgreSQL Setup

```sql
-- Create database
CREATE DATABASE fluxion_prod;

-- Create user
CREATE USER fluxion_user WITH PASSWORD 'secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE fluxion_prod TO fluxion_user;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create read-only user for replicas
CREATE USER fluxion_reader WITH PASSWORD 'reader_password';
GRANT CONNECT ON DATABASE fluxion_prod TO fluxion_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fluxion_reader;
```

### Redis Configuration (redis.conf)

```conf
# Network
bind 0.0.0.0
port 6379
protected-mode yes
requirepass your-redis-password

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Performance
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

## Blockchain Tooling Configuration

### Foundry Configuration (foundry.toml)

```toml
[profile.default]
src = "contracts"
out = "out"
libs = ["lib"]
solc = "0.8.19"
optimizer = true
optimizer_runs = 200
via_ir = false

[profile.production]
optimizer = true
optimizer_runs = 10000
via_ir = true

[rpc_endpoints]
mainnet = "${ETHEREUM_RPC_URL}"
polygon = "${POLYGON_RPC_URL}"
arbitrum = "${ARBITRUM_RPC_URL}"

[etherscan]
mainnet = { key = "${ETHERSCAN_API_KEY}" }
polygon = { key = "${POLYGONSCAN_API_KEY}" }
```

### Network-Specific Settings

```javascript
// For each network
{
  ethereum: {
    chainId: 1,
    rpcUrl: process.env.ETHEREUM_RPC_URL,
    explorerUrl: "https://etherscan.io",
    confirmations: 12,
    gasMultiplier: 1.1
  },
  polygon: {
    chainId: 137,
    rpcUrl: process.env.POLYGON_RPC_URL,
    explorerUrl: "https://polygonscan.com",
    confirmations: 256,
    gasMultiplier: 1.2
  }
}
```

## Security Configuration

### SSL/TLS Configuration

```nginx
# Nginx SSL configuration
server {
    listen 443 ssl http2;
    server_name api.fluxion.exchange;

    ssl_certificate /etc/ssl/certs/fluxion.crt;
    ssl_certificate_key /etc/ssl/private/fluxion.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### Firewall Rules

```bash
# UFW firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8545/tcp  # Blockchain RPC (internal only)
sudo ufw enable
```

## AI/ML Model Configuration

### Model Configuration (code/ml_models/config.yaml)

```yaml
models:
  liquidity_prediction:
    type: LSTM
    input_size: 10
    hidden_size: 128
    num_layers: 4
    dropout: 0.2
    learning_rate: 0.001
    batch_size: 32
    epochs: 100

  price_forecasting:
    type: Transformer
    d_model: 256
    nhead: 8
    num_layers: 6
    dropout: 0.1
    learning_rate: 0.0001
    batch_size: 64
    epochs: 150

training:
  device: cuda # cuda or cpu
  validation_split: 0.2
  early_stopping_patience: 10
  checkpoint_interval: 5
```

## Monitoring Configuration

### Prometheus Configuration (prometheus.yml)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "fluxion-backend"
    static_configs:
      - targets: ["backend:8000"]

  - job_name: "fluxion-postgres"
    static_configs:
      - targets: ["postgres-exporter:9187"]

  - job_name: "fluxion-redis"
    static_configs:
      - targets: ["redis-exporter:9121"]

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
```

### Grafana Configuration

```yaml
# datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

## Environment-Specific Settings

### Development

```bash
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://dev:dev@localhost:5432/fluxion_dev
ETHEREUM_RPC_URL=http://localhost:8545  # Local Anvil
```

### Staging

```bash
APP_ENV=staging
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://staging:***@db-staging.internal:5432/fluxion_staging
ETHEREUM_RPC_URL=https://sepolia.infura.io/v3/***
```

### Production

```bash
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://prod:***@db-prod.internal:5432/fluxion_prod
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/***
```

## Best Practices

1. **Never commit secrets**: Use `.env` files (add to `.gitignore`)
2. **Use environment variables**: For deployment-specific values
3. **Separate by environment**: Different configs for dev/staging/prod
4. **Validate on startup**: Check required config values exist
5. **Use strong secrets**: Generate with `openssl rand -hex 32`
6. **Rotate credentials**: Regularly update API keys and passwords
7. **Least privilege**: Give minimal required permissions
8. **Monitor configuration**: Alert on config changes in production

## Troubleshooting

| Issue                        | Solution                                          |
| ---------------------------- | ------------------------------------------------- |
| Missing environment variable | Check `.env` file exists and variable is set      |
| Database connection failed   | Verify `DATABASE_URL` format and credentials      |
| RPC endpoint timeout         | Check `*_RPC_URL` values and network connectivity |
| Invalid JWT token            | Verify `JWT_SECRET` is set and consistent         |
| CORS errors                  | Add frontend URL to `ALLOWED_ORIGINS`             |

For more help, see [Troubleshooting Guide](TROUBLESHOOTING.md).
