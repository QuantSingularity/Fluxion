# API Reference

Complete reference for Fluxion's RESTful API with parameters, examples, and response formats.

## Table of Contents

- [Base URL and Authentication](#base-url-and-authentication)
- [Authentication Endpoints](#authentication-endpoints)
- [Trading Operations](#trading-operations)
- [Liquidity Operations](#liquidity-operations)
- [Pool Management](#pool-management)
- [Risk Management](#risk-management)
- [AI/ML Endpoints](#aiml-endpoints)
- [Cross-Chain Operations](#cross-chain-operations)
- [Admin Endpoints](#admin-endpoints)
- [WebSocket API](#websocket-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Base URL and Authentication

### Base URL

```text
Production: https://api.fluxion.exchange/v1
Staging: https://api-staging.fluxion.exchange/v1
Local: http://localhost:8000/api/v1
```

### Authentication

All API endpoints (except health checks) require JWT authentication. Include the token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

### Rate Limits

| Endpoint Type         | Rate Limit    | Notes              |
| --------------------- | ------------- | ------------------ |
| Regular endpoints     | 100 req/min   | Per user           |
| Market data           | 1000 req/min  | Per user           |
| AI predictions        | 10 req/min    | Resource intensive |
| WebSocket connections | 10 concurrent | Per user           |

## Authentication Endpoints

### POST /auth/login

Authenticate user and receive JWT token.

| Parameter   | Type    | Required | Default | Description            | Example            |
| ----------- | ------- | -------- | ------- | ---------------------- | ------------------ |
| username    | string  | Yes      | -       | User username or email | `user@example.com` |
| password    | string  | Yes      | -       | User password          | "SecurePass123!"   |
| remember_me | boolean | No       | false   | Extended token expiry  | true               |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "trader@example.com",
    "password": "SecurePass123!",
    "remember_me": true
  }'
```

**Example Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-123",
    "username": "trader@example.com",
    "roles": ["trader"]
  }
}
```

### POST /auth/refresh

Refresh an expired JWT token.

| Parameter     | Type   | Required | Default | Description              | Example       |
| ------------- | ------ | -------- | ------- | ------------------------ | ------------- |
| refresh_token | string | Yes      | -       | Refresh token from login | "eyJhbGci..." |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### POST /auth/logout

Invalidate current JWT token.

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Trading Operations

### POST /order

Create a new synthetic asset order.

| Parameter          | Type      | Required | Default | Description                             | Example    |
| ------------------ | --------- | -------- | ------- | --------------------------------------- | ---------- |
| asset_id           | string    | Yes      | -       | Synthetic asset identifier              | "BTC-USD"  |
| side               | enum      | Yes      | -       | Order side: BUY or SELL                 | "BUY"      |
| amount             | string    | Yes      | -       | Order quantity (decimal string)         | "1.5"      |
| price              | string    | No       | -       | Limit price (required for LIMIT orders) | "50000.00" |
| order_type         | enum      | Yes      | -       | MARKET, LIMIT, TWAP, or VWAP            | "MARKET"   |
| slippage_tolerance | string    | No       | "0.01"  | Max acceptable slippage (0.01 = 1%)     | "0.005"    |
| time_in_force      | enum      | No       | "GTC"   | GTC, IOC, FOK, GTD                      | "GTC"      |
| expires_at         | timestamp | No       | -       | Expiry for GTD orders                   | 1640995200 |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/order \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "BTC-USD",
    "side": "BUY",
    "amount": "0.5",
    "order_type": "MARKET",
    "slippage_tolerance": "0.01"
  }'
```

**Example Response:**

```json
{
  "order_id": "ord_1234567890",
  "status": "PENDING",
  "asset_id": "BTC-USD",
  "side": "BUY",
  "amount": "0.5",
  "filled_amount": "0",
  "order_type": "MARKET",
  "timestamp": "2024-01-15T10:30:00Z",
  "estimated_price": "50125.50",
  "estimated_slippage": "0.0025"
}
```

### GET /order/{order_id}

Get order status and details.

| Parameter | Type   | Required | Default | Description                       | Example          |
| --------- | ------ | -------- | ------- | --------------------------------- | ---------------- |
| order_id  | string | Yes      | -       | Order identifier from POST /order | "ord_1234567890" |

**Example Request:**

```bash
curl -X GET http://localhost:8000/api/v1/order/ord_1234567890 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**

```json
{
  "order_id": "ord_1234567890",
  "status": "FILLED",
  "asset_id": "BTC-USD",
  "side": "BUY",
  "amount": "0.5",
  "filled_amount": "0.5",
  "average_price": "50150.25",
  "order_type": "MARKET",
  "created_at": "2024-01-15T10:30:00Z",
  "filled_at": "2024-01-15T10:30:05Z",
  "fees": "25.08",
  "transaction_hashes": ["0x1234abcd..."]
}
```

### GET /orders

Get user's order history.

| Parameter | Type      | Required | Default | Description                        | Example    |
| --------- | --------- | -------- | ------- | ---------------------------------- | ---------- |
| asset_id  | string    | No       | -       | Filter by asset                    | "BTC-USD"  |
| status    | enum      | No       | -       | PENDING, FILLED, CANCELLED, FAILED | "FILLED"   |
| limit     | integer   | No       | 50      | Number of orders to return         | 100        |
| offset    | integer   | No       | 0       | Pagination offset                  | 0          |
| from_date | timestamp | No       | -       | Start date filter                  | 1640000000 |
| to_date   | timestamp | No       | -       | End date filter                    | 1640995200 |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/orders?asset_id=BTC-USD&status=FILLED&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### DELETE /order/{order_id}

Cancel a pending order.

**Example Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/order/ord_1234567890 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Liquidity Operations

### POST /pool/{pool_id}/deposit

Add liquidity to a pool.

| Parameter     | Type   | Required | Default | Description                   | Example                            |
| ------------- | ------ | -------- | ------- | ----------------------------- | ---------------------------------- |
| pool_id       | string | Yes      | -       | Pool identifier               | "pool_eth_usdc"                    |
| assets        | array  | Yes      | -       | Assets and amounts to deposit | [{"asset": "ETH", "amount": "10"}] |
| min_lp_tokens | string | No       | -       | Minimum LP tokens to receive  | "1000"                             |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/pool/pool_eth_usdc/deposit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {"asset": "ETH", "amount": "10"},
      {"asset": "USDC", "amount": "30000"}
    ],
    "min_lp_tokens": "9950"
  }'
```

**Example Response:**

```json
{
  "transaction_id": "tx_deposit_123",
  "pool_id": "pool_eth_usdc",
  "lp_tokens_received": "10000",
  "share_percentage": "0.5",
  "transaction_hash": "0xabcd1234...",
  "status": "CONFIRMED"
}
```

### POST /pool/{pool_id}/withdraw

Remove liquidity from a pool.

| Parameter  | Type   | Required | Default | Description               | Example                             |
| ---------- | ------ | -------- | ------- | ------------------------- | ----------------------------------- |
| pool_id    | string | Yes      | -       | Pool identifier           | "pool_eth_usdc"                     |
| lp_tokens  | string | Yes      | -       | LP tokens to burn         | "5000"                              |
| min_assets | array  | No       | -       | Minimum assets to receive | [{"asset": "ETH", "amount": "4.9"}] |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/pool/pool_eth_usdc/withdraw \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "lp_tokens": "5000",
    "min_assets": [
      {"asset": "ETH", "amount": "4.9"},
      {"asset": "USDC", "amount": "14700"}
    ]
  }'
```

### GET /pool/{pool_id}/stats

Get pool statistics and metrics.

**Example Request:**

```bash
curl -X GET http://localhost:8000/api/v1/pool/pool_eth_usdc/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**

```json
{
  "pool_id": "pool_eth_usdc",
  "name": "ETH-USDC Liquidity Pool",
  "tvl": "125000000.50",
  "volume_24h": "5250000.00",
  "volume_7d": "38500000.00",
  "fees_24h": "15750.00",
  "apy": "12.5",
  "utilization": "0.68",
  "assets": [
    {
      "asset": "ETH",
      "balance": "25000",
      "weight": "0.5",
      "price_usd": "3000.50"
    },
    {
      "asset": "USDC",
      "balance": "50000000",
      "weight": "0.5",
      "price_usd": "1.0"
    }
  ],
  "total_lp_tokens": "2000000",
  "lp_token_price": "62.50"
}
```

## Pool Management

### GET /pools

List all available liquidity pools.

| Parameter | Type    | Required | Default | Description               | Example    |
| --------- | ------- | -------- | ------- | ------------------------- | ---------- |
| chain     | string  | No       | -       | Filter by blockchain      | "ethereum" |
| min_tvl   | string  | No       | -       | Minimum TVL filter        | "1000000"  |
| sort_by   | enum    | No       | "tvl"   | Sort by: tvl, apy, volume | "apy"      |
| limit     | integer | No       | 50      | Number of pools to return | 20         |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/pools?chain=ethereum&min_tvl=1000000&sort_by=apy" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Risk Management

### GET /risk/metrics

Get risk metrics for user's portfolio.

**Example Request:**

```bash
curl -X GET http://localhost:8000/api/v1/risk/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**

```json
{
  "var_95": "15250.50",
  "var_99": "22500.75",
  "expected_shortfall": "18000.25",
  "sharpe_ratio": "1.85",
  "beta": "1.12",
  "volatility": "0.25",
  "max_drawdown": "0.18",
  "correlation_matrix": {
    "BTC-USD": { "ETH-USD": 0.85, "SOL-USD": 0.72 },
    "ETH-USD": { "BTC-USD": 0.85, "SOL-USD": 0.78 }
  },
  "liquidation_risk": "LOW",
  "health_factor": "2.5"
}
```

### GET /risk/position/{position_id}

Get risk metrics for specific position.

| Parameter   | Type   | Required | Default | Description         | Example      |
| ----------- | ------ | -------- | ------- | ------------------- | ------------ |
| position_id | string | Yes      | -       | Position identifier | "pos_123456" |

**Example Request:**

```bash
curl -X GET http://localhost:8000/api/v1/risk/position/pos_123456 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## AI/ML Endpoints

### GET /ai/predictions/{asset_id}

Get AI-powered price predictions.

| Parameter | Type    | Required | Default | Description                          | Example   |
| --------- | ------- | -------- | ------- | ------------------------------------ | --------- |
| asset_id  | string  | Yes      | -       | Asset identifier                     | "BTC-USD" |
| horizon   | integer | No       | 24      | Prediction horizon in hours          | 48        |
| interval  | integer | No       | 1       | Interval between predictions (hours) | 4         |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/ai/predictions/BTC-USD?horizon=48&interval=4" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**

```json
{
  "asset_id": "BTC-USD",
  "current_price": "50000.00",
  "model_version": "v2.3.1",
  "generated_at": "2024-01-15T10:30:00Z",
  "predictions": [
    {
      "timestamp": "2024-01-15T14:30:00Z",
      "price": "50250.00",
      "confidence": 0.85,
      "lower_bound": "49800.00",
      "upper_bound": "50700.00"
    },
    {
      "timestamp": "2024-01-15T18:30:00Z",
      "price": "50500.00",
      "confidence": 0.78,
      "lower_bound": "49900.00",
      "upper_bound": "51100.00"
    }
  ]
}
```

### GET /ai/liquidity/forecast

Get liquidity forecast for pools.

| Parameter | Type    | Required | Default | Description                       | Example         |
| --------- | ------- | -------- | ------- | --------------------------------- | --------------- |
| pool_id   | string  | No       | -       | Specific pool (or all if omitted) | "pool_eth_usdc" |
| horizon   | integer | No       | 168     | Forecast horizon in hours         | 336             |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/ai/liquidity/forecast?pool_id=pool_eth_usdc&horizon=168" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### GET /ai/arbitrage/opportunities

Get detected arbitrage opportunities across chains.

**Example Request:**

```bash
curl -X GET http://localhost:8000/api/v1/ai/arbitrage/opportunities \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Example Response:**

```json
{
  "opportunities": [
    {
      "id": "arb_123",
      "asset": "USDC",
      "buy_chain": "ethereum",
      "sell_chain": "polygon",
      "buy_price": "1.0",
      "sell_price": "1.003",
      "profit_bps": 30,
      "estimated_profit_usd": "300.00",
      "required_capital": "100000.00",
      "expiry": "2024-01-15T10:35:00Z",
      "risk_score": 0.15
    }
  ]
}
```

## Cross-Chain Operations

### POST /crosschain/bridge

Initiate cross-chain asset bridge.

| Parameter  | Type   | Required | Default | Description                            | Example    |
| ---------- | ------ | -------- | ------- | -------------------------------------- | ---------- |
| asset      | string | Yes      | -       | Asset to bridge                        | "USDC"     |
| amount     | string | Yes      | -       | Amount to bridge                       | "10000"    |
| from_chain | string | Yes      | -       | Source chain                           | "ethereum" |
| to_chain   | string | Yes      | -       | Destination chain                      | "polygon"  |
| recipient  | string | No       | -       | Recipient address (defaults to sender) | "0x..."    |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/crosschain/bridge \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": "USDC",
    "amount": "10000",
    "from_chain": "ethereum",
    "to_chain": "polygon"
  }'
```

**Example Response:**

```json
{
  "bridge_id": "bridge_789",
  "status": "INITIATED",
  "from_tx_hash": "0x1234...",
  "estimated_completion": "2024-01-15T10:45:00Z",
  "fees": {
    "bridge_fee": "10.00",
    "gas_fee": "15.50"
  }
}
```

### GET /crosschain/bridge/{bridge_id}

Get bridge transaction status.

**Example Request:**

```bash
curl -X GET http://localhost:8000/api/v1/crosschain/bridge/bridge_789 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Admin Endpoints

### GET /admin/system/status

Get system health and status (requires admin role).

**Example Response:**

```json
{
  "status": "healthy",
  "uptime": 86400,
  "services": {
    "database": { "status": "healthy", "latency_ms": 5 },
    "redis": { "status": "healthy", "latency_ms": 2 },
    "blockchain_rpc": { "status": "healthy", "latency_ms": 150 }
  },
  "metrics": {
    "active_users": 1250,
    "orders_24h": 8500,
    "tvl": "125000000.50"
  }
}
```

## WebSocket API

### Connection

```text
wss://api.fluxion.exchange/ws/v1
```

### Subscribe to Market Data

```json
{
  "type": "subscribe",
  "channels": ["trades", "orderbook", "liquidations"],
  "symbols": ["BTC-USD", "ETH-USD"]
}
```

### Unsubscribe

```json
{
  "type": "unsubscribe",
  "channels": ["trades"],
  "symbols": ["BTC-USD"]
}
```

### Example Messages

**Trade Update:**

```json
{
  "type": "trade",
  "symbol": "BTC-USD",
  "price": "50125.50",
  "amount": "0.5",
  "side": "BUY",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

**Order Book Update:**

```json
{
  "type": "orderbook",
  "symbol": "ETH-USD",
  "bids": [
    ["3000.50", "10.5"],
    ["3000.25", "8.2"]
  ],
  "asks": [
    ["3001.00", "12.3"],
    ["3001.25", "15.7"]
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Handling

### Error Response Format

```json
{
  "error": "Detailed error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "amount",
    "issue": "Must be greater than 0"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456"
}
```

### Error Codes

| Code                  | HTTP Status | Description                             |
| --------------------- | ----------- | --------------------------------------- |
| UNAUTHORIZED          | 401         | Invalid or missing authentication token |
| FORBIDDEN             | 403         | Insufficient permissions                |
| NOT_FOUND             | 404         | Resource not found                      |
| VALIDATION_ERROR      | 422         | Invalid request parameters              |
| RATE_LIMIT_EXCEEDED   | 429         | Too many requests                       |
| INSUFFICIENT_BALANCE  | 400         | Insufficient funds for operation        |
| ORDER_FAILED          | 400         | Order execution failed                  |
| POOL_INACTIVE         | 400         | Liquidity pool is inactive              |
| INTERNAL_SERVER_ERROR | 500         | Internal server error                   |

## Rate Limiting

Rate limit headers are included in all responses:

```text
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

When rate limit is exceeded:

```json
{
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## SDK Examples

There are no standalone SDK example files yet. The request and response samples above, the [Usage Guide](USAGE.md) and the [liquidity provision example](examples/liquidity_provision.md) show working calls.
