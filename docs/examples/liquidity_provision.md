# Liquidity Provision Example

Complete guide to providing liquidity to Fluxion pools, earning fees, and managing LP positions.

## Overview

Liquidity providers (LPs) earn fees by depositing assets into liquidity pools. This example shows how to:

1. Check available pools
2. Add liquidity to pools
3. Monitor earnings
4. Remove liquidity

## Prerequisites

- Fluxion running locally or deployed
- Assets to provide as liquidity
- Web3 wallet (MetaMask) with funds

## Smart Contract Interaction

### Using ethers.js

```javascript
const { ethers } = require("ethers");

// Contract ABIs
const LiquidityPoolManagerABI = require("./abis/LiquidityPoolManager.json");

// Configuration
const POOL_MANAGER_ADDRESS = "0x..."; // Deployed contract address
const RPC_URL = "http://localhost:8545"; // Or testnet/mainnet

async function main() {
  // Connect to provider
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const signer = await provider.getSigner();

  // Connect to contract
  const poolManager = new ethers.Contract(
    POOL_MANAGER_ADDRESS,
    LiquidityPoolManagerABI,
    signer,
  );

  console.log("Connected to LiquidityPoolManager at", POOL_MANAGER_ADDRESS);

  // Add liquidity
  const poolId = ethers.id("ETH-USDC-POOL");
  const ethAmount = ethers.parseEther("1.0"); // 1 ETH
  const usdcAmount = ethers.parseUnits("3000", 6); // 3000 USDC (6 decimals)

  const tx = await poolManager.addLiquidity(
    poolId,
    [ethAmount, usdcAmount],
    { value: ethAmount }, // Send ETH with transaction
  );

  console.log("Transaction hash:", tx.hash);
  const receipt = await tx.wait();
  console.log("Liquidity added! Block:", receipt.blockNumber);
}

main().catch(console.error);
```

## API-Based Liquidity Management

### Add Liquidity via API

```python
#!/usr/bin/env python3
"""
Liquidity provision example using Fluxion API
"""

import asyncio
import httpx
from decimal import Decimal

API_URL = "http://localhost:8000"
API_TOKEN = "your-jwt-token"

async def add_liquidity_example():
    """Add liquidity to a pool via API"""

    async with httpx.AsyncClient() as client:
        # 1. Get available pools
        response = await client.get(
            f"{API_URL}/api/v1/pools",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        pools = response.json()

        print("Available Pools:")
        for pool in pools['pools']:
            print(f"  {pool['pool_id']}: {pool['name']}")
            print(f"    TVL: ${Decimal(pool['tvl']):,.2f}")
            print(f"    APY: {Decimal(pool['apy']):.2f}%")
            print()

        # 2. Select a pool
        pool_id = "pool_eth_usdc"

        # 3. Get pool details
        response = await client.get(
            f"{API_URL}/api/v1/pool/{pool_id}/stats",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        pool_stats = response.json()

        print(f"Selected Pool: {pool_stats['name']}")
        print(f"Current TVL: ${Decimal(pool_stats['tvl']):,.2f}")
        print(f"24h Volume: ${Decimal(pool_stats['volume_24h']):,.2f}")
        print()

        # 4. Add liquidity
        response = await client.post(
            f"{API_URL}/api/v1/pool/{pool_id}/deposit",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            json={
                "assets": [
                    {"asset": "ETH", "amount": "1.0"},
                    {"asset": "USDC", "amount": "3000"}
                ],
                "min_lp_tokens": "2980"  # Allow 2% slippage
            }
        )
        response.raise_for_status()
        result = response.json()

        print("✓ Liquidity Added Successfully!")
        print(f"  Transaction ID: {result['transaction_id']}")
        print(f"  LP Tokens Received: {result['lp_tokens_received']}")
        print(f"  Pool Share: {Decimal(result['share_percentage']):.4f}%")
        print(f"  Transaction Hash: {result['transaction_hash']}")

        return result

async def remove_liquidity_example(pool_id: str, lp_tokens: str):
    """Remove liquidity from a pool"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/v1/pool/{pool_id}/withdraw",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            json={
                "lp_tokens": lp_tokens,
                "min_assets": [
                    {"asset": "ETH", "amount": "0.95"},  # Allow some slippage
                    {"asset": "USDC", "amount": "2850"}
                ]
            }
        )
        response.raise_for_status()
        result = response.json()

        print("✓ Liquidity Removed Successfully!")
        print(f"  Assets Returned:")
        for asset in result['assets_returned']:
            print(f"    {asset['asset']}: {asset['amount']}")
        print(f"  Transaction Hash: {result['transaction_hash']}")

        return result

async def monitor_earnings(pool_id: str):
    """Monitor LP position and earnings"""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/api/v1/pool/{pool_id}/position",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        response.raise_for_status()
        position = response.json()

        print("Your LP Position:")
        print(f"  LP Tokens: {position['lp_tokens']}")
        print(f"  Pool Share: {Decimal(position['share_percentage']):.4f}%")
        print(f"  Position Value: ${Decimal(position['value_usd']):,.2f}")
        print(f"  Fees Earned (24h): ${Decimal(position['fees_earned_24h']):,.2f}")
        print(f"  Fees Earned (All Time): ${Decimal(position['fees_earned_total']):,.2f}")
        print(f"  Impermanent Loss: {Decimal(position['impermanent_loss_percent']):.2f}%")

        return position

async def calculate_expected_returns(
    pool_id: str,
    amount_usd: str,
    days: int = 365
):
    """Calculate expected returns from liquidity provision"""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/api/v1/pool/{pool_id}/stats",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        stats = response.json()

        apy = Decimal(stats['apy']) / 100  # Convert percentage to decimal
        amount = Decimal(amount_usd)

        # Simple APY calculation (not accounting for compounding)
        daily_rate = apy / 365
        expected_return = amount * daily_rate * days

        print(f"Expected Returns Calculation:")
        print(f"  Pool APY: {Decimal(stats['apy']):.2f}%")
        print(f"  Initial Deposit: ${amount:,.2f}")
        print(f"  Time Period: {days} days")
        print(f"  Expected Fees: ${expected_return:,.2f}")
        print(f"  Expected Total: ${amount + expected_return:,.2f}")

        return {
            'apy': stats['apy'],
            'initial_amount': str(amount),
            'expected_fees': str(expected_return),
            'expected_total': str(amount + expected_return)
        }

async def main():
    """Main liquidity provision workflow"""

    print("=" * 60)
    print("Fluxion Liquidity Provision Example")
    print("=" * 60)
    print()

    # 1. Calculate expected returns
    print("Step 1: Calculate Expected Returns")
    print("-" * 60)
    await calculate_expected_returns(
        pool_id="pool_eth_usdc",
        amount_usd="6000",
        days=365
    )
    print()

    # 2. Add liquidity
    print("Step 2: Add Liquidity")
    print("-" * 60)
    result = await add_liquidity_example()
    print()

    # 3. Monitor position
    print("Step 3: Monitor Position")
    print("-" * 60)
    await asyncio.sleep(5)  # Wait for transaction confirmation
    await monitor_earnings("pool_eth_usdc")
    print()

    # 4. Optional: Remove liquidity
    # print("Step 4: Remove Liquidity")
    # print("-" * 60)
    # await remove_liquidity_example("pool_eth_usdc", result['lp_tokens_received'])
    # print()

    print("=" * 60)
    print("Liquidity provision workflow completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Concepts

### Impermanent Loss

When providing liquidity, you may experience impermanent loss if asset prices diverge:

```python
def calculate_impermanent_loss(price_ratio: float) -> float:
    """
    Calculate impermanent loss percentage

    Args:
        price_ratio: Final price / Initial price

    Returns:
        Impermanent loss as percentage (negative value)
    """
    import math

    # Formula: 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
    loss = (2 * math.sqrt(price_ratio) / (1 + price_ratio)) - 1
    return loss * 100  # Convert to percentage

# Example
initial_eth_price = 3000
final_eth_price = 4500
price_ratio = final_eth_price / initial_eth_price

il = calculate_impermanent_loss(price_ratio)
print(f"Impermanent Loss: {il:.2f}%")  # -2.02%
```

### Fee Earnings

Liquidity providers earn a portion of trading fees:

```python
# If pool charges 0.3% fee and your share is 1%
trading_volume_24h = 1_000_000  # $1M in 24h
pool_fee_rate = 0.003  # 0.3%
your_share = 0.01  # 1%

daily_fees = trading_volume_24h * pool_fee_rate * your_share
annual_fees = daily_fees * 365

print(f"Daily fees: ${daily_fees:,.2f}")
print(f"Annual fees: ${annual_fees:,.2f}")
```

## Best Practices

1. **Start Small**: Test with small amounts first
2. **Diversify**: Don't put all assets in one pool
3. **Monitor**: Regularly check impermanent loss
4. **Compound**: Reinvest fees to maximize returns
5. **Understand Risks**: Study impermanent loss before providing liquidity

## Risk Management

```python
async def check_pool_risk(pool_id: str) -> dict:
    """Check risk metrics for a pool"""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/api/v1/pool/{pool_id}/risk",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        risk = response.json()

        # Risk indicators
        warnings = []

        if Decimal(risk['volatility']) > Decimal('50'):
            warnings.append("High volatility - increased IL risk")

        if Decimal(risk['utilization']) > Decimal('0.9'):
            warnings.append("High utilization - may impact withdrawals")

        if Decimal(risk['concentration']) > Decimal('0.3'):
            warnings.append("High concentration - single LP dominance")

        if warnings:
            print("⚠️  Risk Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("✓ Pool risk profile is acceptable")

        return risk
```

## Monitoring Dashboard

Create a simple monitoring script:

```python
#!/usr/bin/env python3
"""
LP position monitoring dashboard
Run this script periodically to track your positions
"""

import asyncio
from datetime import datetime

async def dashboard():
    """Display LP dashboard"""

    print(f"\nFluxion LP Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Get all LP positions
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/api/v1/portfolio/lp-positions",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        positions = response.json()

        total_value = Decimal('0')
        total_fees = Decimal('0')

        for pos in positions['positions']:
            print(f"\nPool: {pos['pool_name']}")
            print(f"  Value: ${Decimal(pos['value_usd']):,.2f}")
            print(f"  Share: {Decimal(pos['share_percentage']):.4f}%")
            print(f"  APY: {Decimal(pos['current_apy']):.2f}%")
            print(f"  Fees (24h): ${Decimal(pos['fees_24h']):,.2f}")
            print(f"  IL: {Decimal(pos['impermanent_loss']):.2f}%")

            total_value += Decimal(pos['value_usd'])
            total_fees += Decimal(pos['fees_total'])

        print("\n" + "=" * 80)
        print(f"Total LP Value: ${total_value:,.2f}")
        print(f"Total Fees Earned: ${total_fees:,.2f}")

# Run dashboard every 5 minutes
async def run_monitoring():
    while True:
        await dashboard()
        await asyncio.sleep(300)  # 5 minutes

if __name__ == "__main__":
    asyncio.run(run_monitoring())
```

## Next Steps

- Review [API Reference](../API.md#liquidity-operations) for complete pool API
- Study [Risk Management](../API.md#risk-management) for portfolio protection
- Check [Configuration](../CONFIGURATION.md) for pool parameters
- See the [Usage Guide](../USAGE.md) for complementary trading workflows

## Disclaimer

Liquidity provision involves risks including impermanent loss. Always:

- Understand the risks before providing liquidity
- Start with amounts you can afford to lose
- Monitor your positions regularly
- Consider the pool's risk profile
