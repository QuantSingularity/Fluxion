import zlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

POOLS: List[Dict[str, Any]] = [
    {
        "id": "pool-synbtc-synusd",
        "name": "synBTC/synUSD",
        "pair": "synBTC/synUSD",
        "assets": ["synBTC", "synUSD"],
        "weights": [50, 50],
        "fee": 0.003,
        "tvl": 10500000,
        "apr": 12.5,
        "volume_24h": 2100000,
        "fees_24h": 6300,
        "utilization": 0.72,
        "verified": True,
    },
    {
        "id": "pool-syneth-synusd",
        "name": "synETH/synUSD",
        "pair": "synETH/synUSD",
        "assets": ["synETH", "synUSD"],
        "weights": [50, 50],
        "fee": 0.003,
        "tvl": 8200000,
        "apr": 10.8,
        "volume_24h": 1640000,
        "fees_24h": 4920,
        "utilization": 0.65,
        "verified": True,
    },
    {
        "id": "pool-syneth-synbtc",
        "name": "synETH/synBTC",
        "pair": "synETH/synBTC",
        "assets": ["synETH", "synBTC"],
        "weights": [60, 40],
        "fee": 0.0025,
        "tvl": 4300000,
        "apr": 8.1,
        "volume_24h": 720000,
        "fees_24h": 1800,
        "utilization": 0.48,
        "verified": False,
    },
]

SYNTHETICS: List[Dict[str, Any]] = [
    {
        "id": "syn-eth",
        "name": "Synthetic Ethereum",
        "symbol": "synETH",
        "underlying_asset": "ETH",
        "price": 3450.25,
        "price_change_24h": 2.4,
        "collateral_ratio": 1.5,
        "total_supply": 125000,
        "circulating_supply": 118500,
        "tvl": 78500000,
        "volume_24h": 12400000,
        "verified": True,
    },
    {
        "id": "syn-btc",
        "name": "Synthetic Bitcoin",
        "symbol": "synBTC",
        "underlying_asset": "BTC",
        "price": 64800.0,
        "price_change_24h": -1.1,
        "collateral_ratio": 1.5,
        "total_supply": 2100,
        "circulating_supply": 1985,
        "tvl": 79000000,
        "volume_24h": 9800000,
        "verified": True,
    },
]

STABLE_SYMBOLS = {"synUSD": 1.0}


def find_pool(pool_id: str) -> Optional[Dict[str, Any]]:
    for pool in POOLS:
        if pool["id"] == pool_id:
            return pool
    return None


def find_synthetic(asset_id: str) -> Optional[Dict[str, Any]]:
    for item in SYNTHETICS:
        if item["id"] == asset_id or item["symbol"].lower() == asset_id.lower():
            return item
    return None


def _symbol_price(symbol: str) -> float:
    if symbol in STABLE_SYMBOLS:
        return STABLE_SYMBOLS[symbol]
    for item in SYNTHETICS:
        if item["symbol"] == symbol:
            return float(item["price"])
    return 1.0


def _symbol_collateral(symbol: str) -> Optional[float]:
    for item in SYNTHETICS:
        if item["symbol"] == symbol:
            return float(item["collateral_ratio"])
    return None


def _build_history(
    key: str,
    points: int,
    end_price: float,
    end_liquidity: float,
    hourly_volume: float,
    utilization: Optional[float],
    collateral_ratio: float,
    verified: bool,
    sigma: float,
) -> List[Dict[str, Any]]:
    rng = np.random.default_rng(zlib.crc32(key.encode("utf-8")))
    returns = rng.normal(0.0, sigma, points)
    log_price = np.cumsum(returns)
    log_price -= log_price[-1]
    price = end_price * np.exp(log_price)

    log_liq = np.zeros(points)
    for i in range(1, points):
        log_liq[i] = (
            0.9 * log_liq[i - 1] + rng.normal(0.0, 0.004) - 0.5 * abs(returns[i])
        )
    log_liq -= log_liq[-1]
    liquidity = end_liquidity * np.exp(log_liq)

    volume = (
        hourly_volume * rng.lognormal(0.0, 0.3, points) * (1.0 + 20.0 * np.abs(returns))
    )
    collateral = np.clip(
        collateral_ratio + np.cumsum(rng.normal(0.0, 0.01, points)) * 0.2, 0.8, 3.0
    )
    collateral = collateral - collateral[-1] + collateral_ratio

    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    records = []
    for i in range(points):
        ts = end - timedelta(hours=points - 1 - i)
        row: Dict[str, Any] = {
            "timestamp": ts.isoformat(),
            "price": float(price[i]),
            "volume": float(volume[i]),
            "liquidity": float(liquidity[i]),
            "collateral_ratio": float(np.clip(collateral[i], 0.8, 3.0)),
            "verified": 1.0 if verified else 0.0,
        }
        if utilization is not None:
            row["utilization"] = float(
                np.clip(utilization + rng.normal(0.0, 0.02), 0.0, 1.0)
            )
        records.append(row)
    return records


def pool_history(pool: Dict[str, Any], points: int) -> List[Dict[str, Any]]:
    base, quote = pool["assets"][0], pool["assets"][1]
    price = _symbol_price(base) / max(_symbol_price(quote), 1e-9)
    collaterals = [c for c in (_symbol_collateral(s) for s in pool["assets"]) if c]
    return _build_history(
        key=pool["id"],
        points=points,
        end_price=price,
        end_liquidity=float(pool["tvl"]),
        hourly_volume=float(pool["volume_24h"]) / 24.0,
        utilization=float(pool["utilization"]),
        collateral_ratio=float(np.mean(collaterals)) if collaterals else 1.5,
        verified=bool(pool.get("verified", False)),
        sigma=0.006,
    )


def synthetic_history(asset: Dict[str, Any], points: int) -> List[Dict[str, Any]]:
    return _build_history(
        key=asset["id"],
        points=points,
        end_price=float(asset["price"]),
        end_liquidity=float(asset["tvl"]),
        hourly_volume=float(asset["volume_24h"]) / 24.0,
        utilization=None,
        collateral_ratio=float(asset["collateral_ratio"]),
        verified=bool(asset.get("verified", False)),
        sigma=0.008,
    )
