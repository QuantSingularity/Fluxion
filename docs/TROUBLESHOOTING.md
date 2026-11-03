# Troubleshooting Guide

Common issues and their solutions when working with Fluxion.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Blockchain Issues](#blockchain-issues)
- [Database Issues](#database-issues)
- [Network Issues](#network-issues)
- [Performance Issues](#performance-issues)
- [Security Issues](#security-issues)

## Installation Issues

### Python Version Mismatch

**Problem:** `python: command not found` or wrong version

**Solution:**

```bash
# Check Python version
python3 --version

# Install Python 3.10+
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv

# macOS
brew install python@3.10

# Create alias (add to ~/.bashrc or ~/.zshrc)
alias python=python3
```

### Node.js Not Found

**Problem:** `node: command not found`

**Solution:**

```bash
# Install Node.js 18+
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# macOS
brew install node@18

# Verify installation
node --version
npm --version
```

### Foundry Not Found

**Problem:** `forge: command not found`

**Solution:**

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash

# This installs foundryup
foundryup

# Verify installation
forge --version
cast --version
anvil --version

# If still not found, add to PATH
export PATH="$HOME/.foundry/bin:$PATH"
# Add to ~/.bashrc or ~/.zshrc to persist
```

### Permission Denied on Scripts

**Problem:** `Permission denied` when running scripts

**Solution:**

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Or specific script
chmod +x scripts/run_fluxion.sh
```

### Virtual Environment Issues

**Problem:** Cannot activate virtual environment

**Solution:**

```bash
# Remove existing venv
rm -rf venv

# Create new virtual environment
python3 -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
.\venv\Scripts\activate

# Verify activation
which python  # Should point to venv/bin/python
```

## Backend Issues

### Port Already in Use

**Problem:** `Address already in use: 0.0.0.0:8000`

**Solution:**

```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or use a different port
uvicorn app.main:app --port 8001
```

### Module Import Errors

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install requirements
cd code/backend
pip install -r requirements.txt

# If still failing, reinstall
pip install --force-reinstall -r requirements.txt
```

### Database Connection Failed

**Problem:** `Connection refused` or `database does not exist`

**Solution:**

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL if stopped
sudo systemctl start postgresql

# Create database
psql -U postgres
CREATE DATABASE fluxion_dev;
CREATE USER fluxion_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE fluxion_dev TO fluxion_user;
\q

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://fluxion_user:your_password@localhost:5432/fluxion_dev

# Run migrations
cd code/backend
alembic upgrade head
```

### Redis Connection Error

**Problem:** `Redis connection failed`

**Solution:**

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# If not running, start Redis
# Linux
sudo systemctl start redis

# macOS
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:7-alpine

# Update REDIS_URL in .env
REDIS_URL=redis://localhost:6379/0
```

### JWT Token Invalid

**Problem:** `Invalid token` or `Token expired`

**Solution:**

```bash
# Generate new JWT secret
openssl rand -hex 32

# Update .env file
JWT_SECRET=your-new-secret-here

# Restart backend server
# All existing tokens will be invalid - users must re-login
```

### Migration Errors

**Problem:** Alembic migration fails

**Solution:**

```bash
cd code/backend

# Check current revision
alembic current

# Downgrade to previous version
alembic downgrade -1

# Or start fresh (WARNING: drops all data)
alembic downgrade base
alembic upgrade head

# If migrations are corrupted
rm -rf migrations/versions/*.py
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Frontend Issues

### npm install Fails

**Problem:** `npm ERR!` during installation

**Solution:**

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install

# If still failing, use --legacy-peer-deps
npm install --legacy-peer-deps
```

### Build Errors

**Problem:** Build fails with errors

**Solution:**

```bash
# Check Node.js version
node --version  # Should be 18+

# Clear build cache
rm -rf dist/ .vite/

# Rebuild
npm run build

# If TypeScript errors
npm run build -- --skipLibCheck
```

### MetaMask Not Detected

**Problem:** `window.ethereum is undefined`

**Solution:**

1. Install MetaMask browser extension
2. Reload page after installation
3. Check browser compatibility (Chrome, Firefox, Brave)
4. Ensure MetaMask is not disabled

**Code check:**

```javascript
if (typeof window.ethereum === "undefined") {
  console.error("Please install MetaMask");
  // Show user-friendly message
}
```

### CORS Errors

**Problem:** `Access to fetch blocked by CORS policy`

**Solution:**

1. **Backend fix** - Update `code/backend/app/main.py`:

   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "http://localhost:3000",
           "http://localhost:5173",
           "https://app.fluxion.exchange"
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Environment variable** - Update `.env`:

   ```bash
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
   ```

3. Restart backend after changes

### WebSocket Connection Failed

**Problem:** WebSocket connection fails

**Solution:**

```bash
# Check backend WebSocket endpoint
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:8000/ws/v1

# Should return 101 Switching Protocols

# Check firewall allows WebSocket
sudo ufw allow 8000/tcp
```

```javascript
// In frontend, ensure correct WebSocket URL
const ws = new WebSocket("ws://localhost:8000/ws/v1");
// NOT 'wss://' for local development
```

## Blockchain Issues

### Foundry Compilation Errors

**Problem:** `forge build` fails

**Solution:**

```bash
cd code/blockchain

# Clean build artifacts
forge clean

# Update dependencies
forge install

# Check Solidity version in foundry.toml
# Ensure it matches pragma in contracts

# Rebuild
forge build

# If OpenZeppelin imports fail
forge install OpenZeppelin/openzeppelin-contracts
```

### Gas Estimation Failed

**Problem:** Transaction fails with gas estimation error

**Solution:**

```javascript
// Increase gas limit manually
const tx = await contract.methodName(args, {
  gasLimit: 500000, // Or higher
});

// Or estimate with buffer
const estimatedGas = await contract.estimateGas.methodName(args);
const tx = await contract.methodName(args, {
  gasLimit: (estimatedGas * 120n) / 100n, // 20% buffer
});
```

### RPC Endpoint Timeout

**Problem:** RPC requests timeout

**Solution:**

```bash
# Check RPC URL is correct
echo $ETHEREUM_RPC_URL

# Test RPC endpoint
curl -X POST $ETHEREUM_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Should return current block number

# If using Alchemy/Infura, check API key is valid
# If using local node, ensure it's running:
anvil  # For local testing
```

### Contract Deployment Fails

**Problem:** Contract deployment transaction reverts

**Solution:**

```bash
# Check deployer has sufficient balance
cast balance $DEPLOYER_ADDRESS --rpc-url $RPC_URL

# Check gas price
cast gas-price --rpc-url $RPC_URL

# Deploy with higher gas price
forge create src/Contract.sol:Contract \
  --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY \
  --gas-price 50000000000  # 50 gwei

# Check for constructor argument errors
forge create src/Contract.sol:Contract \
  --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY \
  --constructor-args "arg1" "arg2"
```

### Chain ID Mismatch

**Problem:** `Chain ID mismatch` error

**Solution:**

```bash
# Check actual chain ID
cast chain-id --rpc-url $RPC_URL

# Update frontend chain configuration
# In web-frontend/.env
VITE_CHAIN_ID=1  # Ethereum mainnet
# Or 137 for Polygon, 42161 for Arbitrum, etc.

# MetaMask: Switch to correct network
# Or add custom network with correct chain ID
```

## Database Issues

### Connection Pool Exhausted

**Problem:** `Too many connections` or pool timeout

**Solution:**

```bash
# Increase pool size in .env
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20

# Or increase PostgreSQL max_connections
# Edit postgresql.conf
max_connections = 200

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Slow Queries

**Problem:** Queries taking too long

**Solution:**

```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Add missing indexes
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Vacuum and analyze
VACUUM ANALYZE orders;
```

### Disk Space Full

**Problem:** Database writes failing due to disk space

**Solution:**

```bash
# Check disk space
df -h

# Find large tables
psql -U postgres -d fluxion_prod -c "
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;"
```

```sql
-- Clean old data if appropriate
DELETE FROM price_history WHERE time < NOW() - INTERVAL '90 days';
VACUUM FULL price_history;
```

## Network Issues

### Cannot Connect to API

**Problem:** API requests fail or timeout

**Solution:**

```bash
# Check backend is running
curl http://localhost:8000/health

# Check firewall
sudo ufw status
sudo ufw allow 8000/tcp

# Check if listening on correct interface
netstat -tlnp | grep 8000
# Should show 0.0.0.0:8000, not 127.0.0.1:8000

# Restart backend with correct host
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### SSL/TLS Certificate Errors

**Problem:** HTTPS certificate validation fails

**Solution:**

```bash
# For development, accept self-signed certs (Node.js)
export NODE_TLS_REJECT_UNAUTHORIZED=0
```

```python
# Or in Python requests:
requests.get(url, verify=False)
```

```bash
# For production, ensure valid SSL certificate
# Check certificate
openssl s_client -connect api.fluxion.exchange:443 -servername api.fluxion.exchange

# Renew Let's Encrypt certificate
sudo certbot renew
```

## Performance Issues

### API Response Slow

**Problem:** API requests take > 1 second

**Solution:**

1. **Enable caching:**

   ```python
   # Add Redis caching for expensive operations
   @cache(expire=300)  # 5 minute cache
   async def get_pool_stats(pool_id: str):
       ...
   ```

2. **Optimize database queries:**

   ```python
   # Use select_in_loading for relationships
   query = select(Order).options(
       selectinload(Order.user)
   )
   ```

3. **Add database indexes:**

   ```sql
   CREATE INDEX CONCURRENTLY idx_orders_asset_status
   ON orders(asset_id, status);
   ```

4. **Monitor with profiling:**

   ```bash
   # Install profiling middleware
   pip install pyinstrument

   # Profile slow endpoints
   python -m pyinstrument app/main.py
   ```

### Frontend Loading Slow

**Problem:** Frontend takes long to load

**Solution:**

```bash
# Analyze bundle size
npm run build
npm run analyze  # If configured
```

```javascript
// Code splitting - lazy load components
import { lazy, Suspense } from "react";
const Trading = lazy(() => import("./components/Trading"));
```

```bash
# Optimize images
# Use WebP format, compress, use CDN

# Enable caching
# Add cache headers in nginx/CDN configuration
```

### ML Model Inference Slow

**Problem:** AI predictions take too long

**Solution:**

```python
# 1. Enable model caching
model = load_model_cached('liquidity_lstm.pth')

# 2. Use GPU if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)

# 3. Batch predictions
predictions = model.predict_batch(inputs)

# 4. Cache predictions
@cache(expire=3600)  # 1 hour
def get_predictions(asset_id):
    return model.predict(asset_id)
```

## Security Issues

### Suspected Unauthorized Access

**Problem:** Unusual activity in logs

**Solution:**

```bash
# 1. Change all secrets immediately
openssl rand -hex 32  # New JWT secret
# Update .env and restart services

# 2. Review audit logs
grep "UNAUTHORIZED" logs/app.log

# 3. Revoke all tokens (force re-login)
redis-cli FLUSHDB  # If tokens stored in Redis

# 4. Enable additional security
# Update .env:
ENABLE_2FA=true
RATE_LIMIT_PER_MINUTE=50  # Reduce from 100

# 5. Check for SQL injection attempts
grep -i "union\|select\|drop" logs/access.log
```

### Wallet Compromised

**Problem:** Suspicion of private key leak

**Action Plan:**

1. **Immediate:**
   - Transfer all funds to new wallet
   - Revoke all approvals on compromised wallet
   - Notify team/users

2. **Investigation:**
   - Check commit history for exposed keys
   - Review server access logs
   - Scan for malware

3. **Prevention:**
   - Use hardware wallets for production
   - Never commit private keys
   - Use .env files (in .gitignore)
   - Rotate keys regularly

## Getting More Help

If issue persists:

1. **Check logs:**

   ```bash
   # Backend logs
   tail -f logs/app.log

   # Frontend console
   # Open browser DevTools (F12) -> Console

   # Smart contract events
   forge test -vvvv
   ```

2. **Search GitHub issues:**
   - [Fluxion Issues](https://github.com/quantsingularity/Fluxion/issues)

3. **Create new issue:**
   - Provide error messages
   - Include steps to reproduce
   - Share relevant logs
   - Specify environment (OS, versions)

4. **Community support:**
   - GitHub Discussions
   - Project Discord/Telegram (if available)

## Error Code Reference

| Error Code | Meaning               | Solution                                |
| ---------- | --------------------- | --------------------------------------- |
| HTTP 401   | Unauthorized          | Check auth token, re-login              |
| HTTP 403   | Forbidden             | Insufficient permissions                |
| HTTP 404   | Not Found             | Check endpoint URL, resource exists     |
| HTTP 422   | Validation Error      | Check request body format               |
| HTTP 429   | Rate Limit            | Wait and retry, reduce request rate     |
| HTTP 500   | Internal Server Error | Check server logs, report if persists   |
| HTTP 502   | Bad Gateway           | Backend not reachable, check if running |
| HTTP 503   | Service Unavailable   | Service restarting or overloaded        |
