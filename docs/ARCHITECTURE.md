# Architecture

High-level system architecture, component interactions, and design patterns for Fluxion.

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Module Mapping](#module-mapping)
- [Design Patterns](#design-patterns)
- [Scalability](#scalability)

## System Overview

Fluxion is a microservices-based synthetic asset liquidity engine built on a three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Web Frontend │  │Mobile Frontend│  │  Admin Panel │      │
│  │   (React)    │  │ (React Native)│  │    (React)   │      │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────┘      │
└─────────┼─────────────────┼──────────────────┼──────────────┘
          │                 │                  │
          └─────────────────┼──────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────────┐
│                    APPLICATION LAYER                          │
│                            │                                  │
│     ┌──────────────────────┴───────────────────────┐         │
│     │          API Gateway (FastAPI)               │         │
│     │  ┌──────────┬──────────┬──────────────────┐ │         │
│     │  │   Auth   │   Rate   │    Security      │ │         │
│     │  │ Middleware│  Limit  │   Middleware     │ │         │
│     │  └──────────┴──────────┴──────────────────┘ │         │
│     └──────────────────┬────────────────────────────┘        │
│                        │                                      │
│  ┌─────────────────────┴───────────────────────────┐         │
│  │              Business Logic Services             │         │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌───────┐ │         │
│  │  │Trade │ │Pool  │ │Risk  │ │AI/ML │ │Cross- │ │         │
│  │  │Engine│ │Mgmt  │ │Engine│ │Models│ │Chain  │ │         │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └───────┘ │         │
│  └─────────────────────┬───────────────────────────┘         │
└────────────────────────┼─────────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────────┐
│                   DATA & BLOCKCHAIN LAYER                     │
│                        │                                      │
│  ┌─────────────┬───────┴────────┬────────────┐              │
│  │             │                │             │              │
│  │  ┌─────────▼──────┐  ┌──────▼────────┐   │              │
│  │  │   PostgreSQL   │  │  Redis Cache  │   │              │
│  │  │  TimescaleDB   │  │   (Session)   │   │              │
│  │  └────────────────┘  └───────────────┘   │              │
│  │                                           │              │
│  │  ┌────────────────────────────────────┐  │              │
│  │  │     Blockchain Layer (EVM)         │  │              │
│  │  │  ┌──────────┐  ┌──────────────┐   │  │              │
│  │  │  │ Ethereum │  │   Polygon    │   │  │              │
│  │  │  │          │  │              │   │  │              │
│  │  │  └──────────┘  └──────────────┘   │  │              │
│  │  │  ┌──────────┐  ┌──────────────┐   │  │              │
│  │  │  │ Arbitrum │  │   Optimism   │   │  │              │
│  │  │  │          │  │              │   │  │              │
│  │  │  └──────────┘  └──────────────┘   │  │              │
│  │  └────────────────────────────────────┘  │              │
│  │                                           │              │
│  │  ┌────────────────────────────────────┐  │              │
│  │  │   External Services                │  │              │
│  │  │  - Chainlink Oracles (Prices)      │  │              │
│  │  │  - Chainlink CCIP (Cross-chain)    │  │              │
│  │  │  - IPFS (Decentralized Storage)    │  │              │
│  │  └────────────────────────────────────┘  │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Frontend Layer

#### Web Frontend (`web-frontend/`)

```
web-frontend/
├── src/
│   ├── components/        # React components
│   │   ├── Trading/       # Trading interface
│   │   ├── Portfolio/     # Portfolio dashboard
│   │   ├── Pools/         # Liquidity pools
│   │   └── Analytics/     # Charts and analytics
│   ├── hooks/             # Custom React hooks
│   ├── services/          # API service layer
│   │   ├── api.js         # HTTP client
│   │   └── web3.js        # Blockchain interaction
│   ├── store/             # State management (Context API)
│   └── utils/             # Helper functions
└── package.json
```

**Key Technologies:**

- React 18 with hooks
- ethers.js 6 for Web3
- Recharts for visualization
- Chakra UI for components

#### Mobile Frontend (`mobile-frontend/`)

```
mobile-frontend/
├── src/
│   ├── screens/           # App screens
│   ├── components/        # Reusable components
│   ├── navigation/        # React Navigation
│   └── services/          # API and blockchain services
└── app.json
```

**Key Technologies:**

- React Native with Expo
- React Navigation
- Native wallet integration

### 2. Application Layer

#### API Gateway (`code/backend/app/main.py`)

Main FastAPI application with middleware stack:

```python
app = FastAPI(title="Fluxion API")

# Middleware order (outside to inside)
app.add_middleware(SecurityMiddleware)       # Security headers
app.add_middleware(RateLimitMiddleware)      # Rate limiting
app.add_middleware(CORSMiddleware)           # CORS handling
app.add_middleware(TrustedHostMiddleware)    # Host validation

# Routes
app.include_router(api_router, prefix="/api/v1")
```

**File:** `code/backend/app/main.py` (298 lines)

#### Business Logic Services

Located in `code/backend/`:

```
code/backend/
├── api/
│   ├── v1/
│   │   └── router.py           # API endpoint definitions
│   └── routes/
│       └── auth.py             # Authentication routes
├── services/                   # Business logic (planned)
│   ├── trading_service.py
│   ├── pool_service.py
│   └── risk_service.py
├── models/                     # Database models
│   ├── user.py
│   ├── transaction.py
│   ├── portfolio.py
│   └── risk.py
└── schemas/                    # Pydantic schemas
    └── base.py
```

### 3. Data & Blockchain Layer

#### Database Schema

**PostgreSQL/TimescaleDB:**

```sql
-- Users and authentication
TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE,
    password_hash VARCHAR,
    created_at TIMESTAMP,
    last_login TIMESTAMP
);

-- Trading orders
TABLE orders (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    asset_id VARCHAR,
    side VARCHAR,  -- BUY/SELL
    amount DECIMAL,
    price DECIMAL,
    order_type VARCHAR,  -- MARKET/LIMIT/TWAP/VWAP
    status VARCHAR,  -- PENDING/FILLED/CANCELLED
    created_at TIMESTAMP,
    filled_at TIMESTAMP
);

-- Liquidity pools
TABLE pools (
    id UUID PRIMARY KEY,
    name VARCHAR,
    assets JSONB,  -- Array of asset configurations
    tvl DECIMAL,
    apy DECIMAL,
    created_at TIMESTAMP
);

-- Time-series price data (TimescaleDB hypertable)
TABLE price_history (
    time TIMESTAMP NOT NULL,
    asset_id VARCHAR,
    price DECIMAL,
    volume DECIMAL,
    PRIMARY KEY (time, asset_id)
);
SELECT create_hypertable('price_history', 'time');
```

**Files:**

- `code/backend/models/*.py` - SQLAlchemy ORM models
- `code/backend/migrations/` - Alembic migrations

#### Smart Contracts

##### SyntheticAssetFactory.sol

Factory contract for creating synthetic assets.

```solidity
contract SyntheticAssetFactory {
  mapping(bytes32 => SyntheticAsset) public syntheticAssets;

  function createSynthetic(
    bytes32 _assetId,
    address _oracle,
    bytes32 _jobId,
    uint256 _fee
  ) external onlyOwner;

  function mintSynthetic(bytes32 _assetId, uint256 _amount) external;
  function burnSynthetic(bytes32 _assetId, uint256 _amount) external;
}
```

**File:** `code/blockchain/contracts/SyntheticAssetFactory.sol` (155 lines)

##### LiquidityPoolManager.sol

Manages liquidity pools with multi-asset support.

```solidity
contract FluxionLiquidityPoolManager {
    struct PoolConfig {
        address[] assets;
        uint256[] weights;
        uint256 fee;
        uint256 amplification;
        bool active;
        uint256 totalLiquidity;
    }

    function createPool(...) external onlyAdmin;
    function addLiquidity(...) external nonReentrant;
    function removeLiquidity(...) external nonReentrant;
    function swap(...) external nonReentrant;
}
```

**File:** `code/blockchain/contracts/LiquidityPoolManager.sol` (418 lines)

##### FluxionGovernanceToken.sol

ERC20 governance token with voting and staking.

```solidity
contract FluxionGovernanceToken is
  ERC20,
  ERC20Votes,
  ERC20Permit,
  AccessControl
{
  function stake(uint256 amount) external;
  function unstake(uint256 amount) external;
  function delegate(address delegatee) public override;
}
```

**File:** `code/blockchain/contracts/FluxionGovernanceToken.sol` (658 lines)

##### SupplyChainTracker.sol

Track assets through supply chain with Chainlink oracles.

```solidity
contract SupplyChainTracker {
    struct Asset {
        uint256 id;
        string metadata;
        address currentCustodian;
        AssetStatus status;
    }

    function trackAsset(...) external onlyTracker;
    function transferAsset(...) external;
}
```

**File:** `code/blockchain/contracts/SupplyChainTracker.sol` (351 lines)

#### AI/ML Models

##### Liquidity Prediction (LSTM)

```python
class LiquidityLSTM(nn.Module):
    def __init__(self, input_size=10, hidden_size=128,
                 num_layers=4, dropout=0.2):
        self.lstm = nn.LSTM(input_size, hidden_size,
                           num_layers, bidirectional=True)
        self.attention = nn.MultiheadAttention(...)
        self.fc = nn.Linear(...)
```

**File:** `code/ml_models/forecasting_models.py`

**Features:**

- Bidirectional LSTM with attention
- Multi-head attention mechanism
- Layer normalization
- GELU activation

##### Supply Chain Forecaster

```python
class SupplyChainForecaster(nn.Module):
    def __init__(self, input_size=12, hidden_size=128):
        self.conv1 = nn.Conv1d(input_size, 32, kernel_size=3)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3)
        self.lstm = nn.LSTM(64, hidden_size, ...)
```

**File:** `code/ml_models/forecasting_models.py`

**Features:**

- 1D convolution for feature extraction
- LSTM for temporal modeling
- Dropout for regularization

## Data Flow

### Trading Flow

```
┌─────────┐   1. Place Order    ┌─────────┐
│  User   ├──────────────────────>  API    │
│ (Web UI)│                       │Gateway │
└─────────┘                       └────┬────┘
                                       │
                                  2. Validate
                                       │
                                  ┌────▼────┐
                                  │ Trading │
                                  │ Service │
                                  └────┬────┘
                                       │
                             3. Execute on Blockchain
                                       │
                            ┌──────────▼──────────┐
                            │ Smart Contract      │
                            │ (SyntheticAsset)    │
                            └──────────┬──────────┘
                                       │
                                  4. Update DB
                                       │
                                  ┌────▼────┐
                                  │Database │
                                  │(Orders) │
                                  └─────────┘
```

### Cross-Chain Liquidity Flow

```
  Ethereum                    CCIP Router                  Polygon
┌──────────┐               ┌─────────────┐             ┌──────────┐
│  Pool A  │──1. Lock────> │  Chainlink  │──2. Msg───> │  Pool B  │
│  (ETH)   │               │    CCIP     │             │  (MATIC) │
└──────────┘               └─────────────┘             └──────────┘
     │                                                        │
     │                                                        │
     │          3. Update Unified Liquidity State            │
     └────────────────────────────┬────────────────────────┘
                                  │
                            ┌─────▼─────┐
                            │  Backend  │
                            │ Sync Svc  │
                            └───────────┘
```

### AI Prediction Flow

```
┌──────────────┐   1. Request      ┌──────────┐
│   User/API   ├────Prediction─────>   API    │
└──────────────┘                   │ Gateway  │
                                   └─────┬────┘
                                         │
                                    2. Check Cache
                                         │
                                   ┌─────▼────┐
                                   │  Redis   │──Cache Hit──> Return
                                   └─────┬────┘
                                         │
                                   Cache Miss
                                         │
                                   ┌─────▼────┐
                                   │ ML Model │
                                   │ Service  │
                                   └─────┬────┘
                                         │
                                   3. Load Model
                                         │
                                   ┌─────▼────┐
                                   │ PyTorch  │
                                   │  LSTM    │
                                   └─────┬────┘
                                         │
                                   4. Inference
                                         │
                                   5. Cache Result
                                         │
                                   ┌─────▼────┐
                                   │  Return  │
                                   │Prediction│
                                   └──────────┘
```

## Technology Stack

### Backend

| Component     | Technology        | Purpose                  | File Location                     |
| ------------- | ----------------- | ------------------------ | --------------------------------- |
| Web Framework | FastAPI 0.104.1   | HTTP API                 | `code/backend/app/main.py`        |
| ASGI Server   | Uvicorn 0.24.0    | Production server        | `code/backend/requirements.txt`   |
| Database ORM  | SQLAlchemy 2.0.23 | Database abstraction     | `code/backend/models/`            |
| Migrations    | Alembic 1.12.1    | Schema versioning        | `code/backend/migrations/`        |
| Cache         | Redis 5.0.1       | Caching, sessions        | N/A (external service)            |
| Task Queue    | Celery 5.3.4      | Background jobs          | `code/backend/` (planned)         |
| Validation    | Pydantic 2.5.0    | Request/response schemas | `code/backend/schemas/`           |
| Auth          | python-jose 3.3.0 | JWT tokens               | `code/backend/api/routes/auth.py` |

### Frontend

| Component     | Technology          | Purpose                | File Location                            |
| ------------- | ------------------- | ---------------------- | ---------------------------------------- |
| Framework     | React 18.2.0        | UI framework           | `web-frontend/src/`                      |
| Build Tool    | Vite 5.1.4          | Development & bundling | `web-frontend/vite.config.js`            |
| Web3 Library  | ethers.js 6.11.1    | Blockchain interaction | `web-frontend/src/services/web3.js`      |
| UI Components | Chakra UI 2.8.2     | Component library      | `web-frontend/src/components/`           |
| Charts        | Recharts 2.12.2     | Data visualization     | `web-frontend/src/components/Analytics/` |
| Routing       | React Router 6.22.2 | Navigation             | `web-frontend/src/App.jsx`               |

### Blockchain

| Component | Technology        | Purpose               | File Location                  |
| --------- | ----------------- | --------------------- | ------------------------------ |
| Language  | Solidity 0.8.19   | Smart contracts       | `code/blockchain/contracts/`   |
| Framework | Foundry           | Development & testing | `code/blockchain/foundry.toml` |
| Oracles   | Chainlink         | Price feeds, CCIP     | Smart contract imports         |
| Standards | ERC20, ERC20Votes | Token standards       | `FluxionGovernanceToken.sol`   |

### AI/ML

| Component     | Technology         | Purpose              | File Location                          |
| ------------- | ------------------ | -------------------- | -------------------------------------- |
| Framework     | PyTorch 2.1.2      | Deep learning        | `code/ml_models/*.py`                  |
| Time Series   | Prophet            | Forecasting          | `code/ml_models/forecasting_models.py` |
| Preprocessing | Scikit-learn 1.4.1 | Data preprocessing   | `code/ml_models/data_pipeline.py`      |
| Distributed   | Ray                | Distributed training | `code/ml_models/` (planned)            |

## Module Mapping

### Repository Structure

```
Fluxion/
├── code/
│   ├── backend/               # Backend API service
│   │   ├── api/               # API routes
│   │   ├── app/               # Application entry
│   │   ├── config/            # Configuration
│   │   ├── middleware/        # Middleware components
│   │   ├── models/            # Database models
│   │   └── schemas/           # Pydantic schemas
│   ├── blockchain/            # Smart contracts
│   │   ├── contracts/         # Solidity contracts
│   │   ├── script/            # Deployment scripts
│   │   └── test/              # Contract tests
│   └── ml_models/             # AI/ML models
│       ├── forecasting_models.py
│       ├── anomaly_detection.py
│       └── train_liquidity_model.py
├── web-frontend/              # React web application
│   └── src/
│       ├── components/
│       ├── services/
│       └── utils/
├── mobile-frontend/           # React Native app
├── infrastructure/            # DevOps & infrastructure
│   ├── ansible/
│   ├── kubernetes/
│   ├── terraform/
│   └── docker-compose.yml
├── scripts/                   # Automation scripts
└── docs/                      # Documentation
```

### Key File Locations

| Feature                | Primary File(s)                                        | Line Count | Notes                |
| ---------------------- | ------------------------------------------------------ | ---------- | -------------------- |
| API Gateway            | `code/backend/app/main.py`                             | 298        | FastAPI app          |
| Trading Logic          | `code/backend/api/v1/router.py`                        | TBD        | API endpoints        |
| Smart Contract Factory | `code/blockchain/contracts/SyntheticAssetFactory.sol`  | 155        | Asset creation       |
| Pool Manager           | `code/blockchain/contracts/LiquidityPoolManager.sol`   | 418        | Pool management      |
| Governance Token       | `code/blockchain/contracts/FluxionGovernanceToken.sol` | 658        | ERC20 + voting       |
| LSTM Model             | `code/ml_models/forecasting_models.py`                 | 659        | Liquidity prediction |
| Supply Chain           | `code/blockchain/contracts/SupplyChainTracker.sol`     | 351        | Asset tracking       |

## Design Patterns

### 1. Repository Pattern

Used in backend for data access abstraction (planned enhancement).

```python
# Example pattern
class OrderRepository:
    async def create(self, order: Order) -> Order:
        ...
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        ...
    async def list_by_user(self, user_id: str) -> List[Order]:
        ...
```

### 2. Factory Pattern

Used in smart contracts for asset creation.

```solidity
// SyntheticAssetFactory.sol
function createSynthetic(...) external onlyOwner {
    SyntheticToken token = new SyntheticToken(...);
    syntheticAssets[_assetId] = SyntheticAsset(...);
}
```

### 3. Middleware Pattern

Used in API gateway for cross-cutting concerns.

```python
# Security, rate limiting, CORS handled as middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CORSMiddleware)
```

### 4. Observer Pattern

Used for real-time updates via WebSocket.

```javascript
// Frontend subscribes to price updates
websocket.on("price_update", (data) => {
  updatePriceDisplay(data);
});
```

### 5. Strategy Pattern

Used for different order types (MARKET, LIMIT, TWAP, VWAP).

```python
class OrderExecutionStrategy:
    def execute(self, order: Order): ...

class MarketOrderStrategy(OrderExecutionStrategy): ...
class LimitOrderStrategy(OrderExecutionStrategy): ...
```

## Scalability

### Horizontal Scaling

- **API Gateway**: Stateless, can scale to N instances behind load balancer
- **Database**: Read replicas for query load distribution
- **Redis**: Redis Cluster for distributed caching
- **ML Inference**: Multiple model servers with load balancing

### Vertical Scaling

- **Database**: Increase CPU/RAM for complex queries
- **ML Training**: GPU instances for model training
- **Blockchain Nodes**: High-memory instances for full nodes

### Performance Optimizations

1. **Database**:
   - TimescaleDB for time-series data
   - Connection pooling (20 connections default)
   - Query optimization with indexes

2. **Caching**:
   - Redis for session data
   - API response caching (short TTL)
   - ML prediction caching (1-hour TTL)

3. **Blockchain**:
   - Batch transactions where possible
   - Gas optimization in contracts
   - Use of zkEVM for privacy and scaling

4. **API**:
   - Rate limiting prevents abuse
   - Async/await for I/O operations
   - Pagination for list endpoints

### Monitoring Points

- API response times (target: < 50ms)
- Database query times
- Blockchain RPC latency
- ML model inference time (target: < 1s)
- WebSocket message latency (target: < 100ms)

See [Monitoring Configuration](CONFIGURATION.md#monitoring-configuration) for setup details.

## Security Architecture

### Defense in Depth

1. **Network Layer**: Firewall rules, DDoS protection
2. **Application Layer**: Input validation, rate limiting
3. **Data Layer**: Encryption at rest, SSL/TLS in transit
4. **Smart Contract**: Audited code, emergency pause functionality

### Key Security Features

- JWT authentication with refresh tokens
- Password hashing with bcrypt
- SQL injection prevention (parameterized queries)
- XSS protection (React auto-escaping)
- CSRF protection
- Audit logging of critical actions

For details, see [Security Documentation](../docs/SECURITY.md).

## Next Steps

- **For developers**: Review [Contributing Guide](CONTRIBUTING.md)
- **For users**: See [Usage Guide](USAGE.md) and [API Reference](API.md)
- **For operators**: Check [Deployment Guide](../docs/DEPLOYMENT.md)
