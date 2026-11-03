# Usage Guide

This guide covers typical usage patterns for Fluxion, including CLI usage, library usage, and common workflows.

## Table of Contents

- [Getting Started](#getting-started)
- [CLI Usage](#cli-usage)
- [Library Usage](#library-usage)
- [Common Workflows](#common-workflows)
- [Web Interface](#web-interface)
- [API Integration](#api-integration)

## Getting Started

After installing Fluxion (see [Installation Guide](INSTALLATION.md)), you can interact with the platform in several ways:

1. **Web Interface**: Visual dashboard for trading and monitoring
2. **CLI Tools**: Command-line scripts for automation
3. **API**: RESTful API for programmatic access
4. **SDK**: Python/JavaScript libraries for integration

## CLI Usage

### Starting Services

```bash
# Start all services (backend + frontend)
./scripts/run_fluxion.sh

# Or start individual components

# Backend only
cd code/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend only
cd web-frontend
npm run dev

# Blockchain node
cd code/blockchain
anvil  # Local test network
```

### Environment Setup

```bash
# Initialize development environment
./scripts/setup_fluxion_env.sh

# This script:
# - Creates Python virtual environment
# - Installs backend dependencies
# - Installs frontend dependencies
# - Sets up configuration files
# - Initializes database (if needed)
```

### Deployment

```bash
# Deploy to multiple environments
./scripts/deploy_multi_env.sh -e staging -n ethereum,polygon,arbitrum

# Options:
#   -e, --env: Environment (development, staging, production)
#   -n, --networks: Blockchain networks (comma-separated)
#   -c, --components: Components to deploy (backend,frontend,blockchain)
#   --test: Run tests before deployment

# Example: Deploy only backend to production on Ethereum
./scripts/deploy_multi_env.sh -e production -n ethereum -c backend --test
```

### Testing

```bash
# Run all tests
./scripts/test_fluxion.sh

# Run specific test suites
cd code/blockchain && forge test          # Smart contract tests
cd code/backend && pytest                 # Backend tests
cd web-frontend && npm test               # Frontend tests

# Cross-chain testing
./scripts/cross_chain_test.sh -n ethereum,polygon -t unit,integration -p

# Options:
#   -n, --networks: Networks to test
#   -t, --types: Test types (unit,integration,e2e,messaging)
#   -p, --parallel: Run tests in parallel
```

### AI/ML Pipeline

```bash
# Train and deploy ML models
./scripts/ai_ml_pipeline.sh -m liquidity_prediction,price_forecasting --gpu --deploy

# Options:
#   -m, --models: Models to train (comma-separated)
#     - liquidity_prediction: LSTM model for liquidity forecasting
#     - price_forecasting: Time series price prediction
#     - volatility_modeling: Volatility and risk metrics
#     - arbitrage_detection: Cross-chain arbitrage opportunities
#   --gpu: Enable GPU acceleration
#   --deploy: Deploy models after training
#   --tune: Enable hyperparameter tuning

# Example: Train all models with GPU and tuning
./scripts/ai_ml_pipeline.sh -m all --gpu --tune --deploy
```

### Monitoring Setup

```bash
# Set up monitoring stack
./scripts/monitoring_setup.sh -e production -c backend,blockchain,database -a slack,email

# Options:
#   -e, --env: Environment to monitor
#   -c, --components: Components to monitor (comma-separated)
#   -a, --alerts: Alert channels (slack,email,pagerduty)
#   --dashboards: Generate Grafana dashboards

# View monitoring endpoints
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001
```

### Linting and Code Quality

```bash
# Run all linters
./scripts/lint-all.sh

# This checks:
# - Python code with black, flake8, mypy
# - JavaScript/TypeScript with ESLint, Prettier
# - Solidity with solhint, prettier-plugin-solidity
# - Infrastructure as Code (Terraform, Kubernetes YAML)
```

## Library Usage

### Python SDK

```python
from fluxion_sdk import FluxionClient
from fluxion_sdk.models import Order, OrderSide, OrderType

# Initialize client
client = FluxionClient(
    api_url="http://localhost:8000",
    api_key="your-api-key-here"
)

# Create market order
order = client.create_order(
    asset_id="BTC-USD",
    side=OrderSide.BUY,
    amount="1.0",
    order_type=OrderType.MARKET
)
print(f"Order created: {order.order_id}")

# Check order status
status = client.get_order_status(order.order_id)
print(f"Order status: {status.status}")

# Get pool statistics
pool_stats = client.get_pool_stats("pool-id-123")
print(f"TVL: ${pool_stats.tvl}")
print(f"24h Volume: ${pool_stats.volume_24h}")
print(f"APY: {pool_stats.apy}%")

# Add liquidity
receipt = client.add_liquidity(
    pool_id="pool-id-123",
    amount="10000",
    asset="USDC"
)
print(f"Liquidity added: {receipt.transaction_hash}")

# Get AI predictions
predictions = client.get_price_predictions("BTC-USD")
for pred in predictions.predictions:
    print(f"Time: {pred.timestamp}, Price: ${pred.price}, Confidence: {pred.confidence}")
```

### JavaScript SDK (ethers.js)

```javascript
const { ethers } = require("ethers");
const FluxionABI = require("./abis/SyntheticAssetFactory.json");

// Connect to provider
const provider = new ethers.JsonRpcProvider("http://localhost:8545");
const signer = await provider.getSigner();

// Connect to contract
const factoryAddress = "0x...";
const factory = new ethers.Contract(factoryAddress, FluxionABI, signer);

// Create synthetic asset
const tx = await factory.createSynthetic(
  ethers.id("BTC-USD"), // Asset ID
  "0x....", // Oracle address
  ethers.id("job-id"), // Chainlink job ID
  ethers.parseEther("0.1"), // Fee
);
await tx.wait();
console.log("Synthetic asset created:", tx.hash);

// Mint synthetic tokens
const mintTx = await factory.mintSynthetic(
  ethers.id("BTC-USD"),
  ethers.parseEther("10"),
);
await mintTx.wait();
console.log("Minted 10 sBTC tokens");

// Get asset details
const asset = await factory.syntheticAssets(ethers.id("BTC-USD"));
console.log("Token address:", asset.token);
console.log("Oracle:", asset.oracle);
console.log("Active:", asset.active);
```

## Common Workflows

### Workflow 1: Create and Trade Synthetic Assets

```bash
# Step 1: Deploy smart contracts
cd code/blockchain
forge script script/Deploy.s.sol --rpc-url $RPC_URL --private-key $PRIVATE_KEY --broadcast

# Step 2: Create synthetic asset (via CLI or web interface)
# Using Python SDK:
python3 << EOF
from fluxion_sdk import FluxionClient
client = FluxionClient(api_url="http://localhost:8000")
client.create_synthetic_asset(
    name="Synthetic Bitcoin",
    symbol="sBTC",
    underlying="BTC",
    collateral_ratio=1.5
)
EOF

# Step 3: Add liquidity to pool
# Via web interface: Connect wallet -> Pools -> Add Liquidity
# Or via API (see API examples above)

# Step 4: Place trade
# Via web interface: Trading -> Select Asset -> Place Order
# Or via SDK (see Python SDK example above)
```

### Workflow 2: Set Up Cross-Chain Liquidity

```python
from fluxion_sdk import FluxionClient

client = FluxionClient(api_url="http://localhost:8000")

# Create unified liquidity pool across chains
pool = client.create_cross_chain_pool(
    name="Multi-Chain USDC Pool",
    assets=["USDC"],
    chains=["ethereum", "polygon", "arbitrum"],
    initial_liquidity={
        "ethereum": "100000",
        "polygon": "100000",
        "arbitrum": "100000"
    }
)

# Monitor cross-chain liquidity
status = client.get_pool_status(pool.pool_id)
for chain, liquidity in status.chain_liquidity.items():
    print(f"{chain}: ${liquidity}")
```

### Workflow 3: AI-Powered Market Making

```bash
# Step 1: Train liquidity prediction model
cd code/ml_models
python train_liquidity_model.py --data historical_data.csv --epochs 100 --save models/liquidity_lstm.pth

# Step 2: Deploy model to backend
./scripts/ai_ml_pipeline.sh -m liquidity_prediction --deploy

# Step 3: Configure automated market making
python3 << EOF
from fluxion_sdk import FluxionClient
client = FluxionClient(api_url="http://localhost:8000")

client.configure_market_maker(
    pool_id="pool-123",
    strategy="ai_optimized",
    parameters={
        "use_ml_predictions": True,
        "rebalance_frequency": "hourly",
        "risk_tolerance": 0.05
    }
)
EOF

# Step 4: Monitor performance
# Access dashboard at http://localhost:3000/market-making
```

### Workflow 4: Privacy-Preserving Trade (zkEVM)

```javascript
const { ethers } = require("ethers");

// Connect to zkSync network
const zkProvider = new ethers.JsonRpcProvider(
  "https://zksync2-testnet.zksync.dev",
);
const zkSigner = new ethers.Wallet(PRIVATE_KEY, zkProvider);

// Execute private trade
const syntheticAsset = new ethers.Contract(ASSET_ADDRESS, ABI, zkSigner);

// Trade is batched and settled privately
const tx = await syntheticAsset.trade(
  ethers.parseEther("1.0"), // Amount
  ethers.parseEther("50000"), // Price limit
  { gasLimit: 1000000 },
);

await tx.wait();
console.log("Private trade executed:", tx.hash);
// Trade details remain confidential on zkEVM
```

## Web Interface

### Dashboard Overview

Access the web dashboard at `http://localhost:3000`:

1. **Home**: Overview of system metrics, TVL, volume
2. **Trading**: Place orders, view order book, execute trades
3. **Pools**: View liquidity pools, add/remove liquidity
4. **Portfolio**: Track positions, P&L, transaction history
5. **Analytics**: Charts, predictions, risk metrics
6. **Admin** (if authorized): System configuration, monitoring

### Connecting Wallet

```javascript
// MetaMask connection
async function connectWallet() {
  if (window.ethereum) {
    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts",
    });
    console.log("Connected:", accounts[0]);
  }
}
```

### Trading Interface

1. Select synthetic asset from dropdown
2. Choose order type (Market, Limit, TWAP, VWAP)
3. Enter amount and price (for limit orders)
4. Review slippage tolerance
5. Click "Place Order"
6. Confirm transaction in wallet
7. Monitor order status in "Orders" tab

## API Integration

### Authentication

```bash
# Get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'

# Use token in subsequent requests
curl -X GET http://localhost:8000/api/v1/pool/stats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Example API Calls

```bash
# Get health status
curl http://localhost:8000/health

# Get pool statistics
curl http://localhost:8000/api/v1/pool/pool-123/stats \
  -H "Authorization: Bearer TOKEN"

# Create order
curl -X POST http://localhost:8000/api/v1/order \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "BTC-USD",
    "side": "BUY",
    "amount": "1.0",
    "order_type": "MARKET"
  }'

# Get AI predictions
curl http://localhost:8000/api/v1/ai/predictions/BTC-USD \
  -H "Authorization: Bearer TOKEN"
```

For complete API documentation, see [API Reference](API.md).

## Best Practices

### Security

- Always use environment variables for sensitive data (private keys, API keys)
- Never commit `.env` files to version control
- Use hardware wallets for production deployments
- Enable 2FA for admin accounts

### Performance

- Use read replicas for high-traffic applications
- Enable Redis caching for frequently accessed data
- Batch transactions when possible
- Monitor gas prices and adjust accordingly

### Monitoring

- Set up alerts for critical events (liquidations, system health)
- Monitor pool utilization and rebalance as needed
- Track AI model performance and retrain when accuracy degrades
- Review logs regularly for anomalies

## Next Steps

- **Explore [API Reference](API.md)** for detailed endpoint documentation
- **Read [Configuration Guide](CONFIGURATION.md)** to customize your setup
- **Check [Examples](examples/)** for more use cases
- **Review [Troubleshooting](TROUBLESHOOTING.md)** for common issues
