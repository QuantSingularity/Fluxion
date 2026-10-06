from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from ml_models.config import SUPPLY_CHAIN_FEATURES


def market_records(
    n: int = 2000,
    seed: int = 0,
    start: Optional[datetime] = None,
    verified: float = 1.0,
    collateral_mean: float = 1.6,
    vol_scale: float = 1.0,
    base_price: float = 100.0,
    base_liquidity: float = 1_000_000.0,
    base_volume: float = 50_000.0,
) -> List[Dict[str, Any]]:
    rng = np.random.default_rng(seed)
    start = start or datetime(2024, 1, 1, tzinfo=timezone.utc)

    regime = np.zeros(n, dtype=int)
    for i in range(1, n):
        flip = rng.random() < 0.03
        regime[i] = (1 - regime[i - 1]) if flip else regime[i - 1]
    sigma = np.where(regime == 0, 0.004, 0.014) * vol_scale
    returns = rng.normal(0.0, sigma)
    price = base_price * np.exp(np.cumsum(returns))

    hours = np.array([(start + timedelta(hours=i)).hour for i in range(n)])
    hour_factor = 1.0 + 0.3 * np.sin(2 * np.pi * hours / 24)
    volume = (
        base_volume
        * rng.lognormal(0.0, 0.35, n)
        * (1.0 + 30.0 * np.abs(returns))
        * hour_factor
    )

    mu = np.log(base_liquidity)
    log_liq = np.empty(n)
    log_liq[0] = mu
    for i in range(1, n):
        drift = 0.05 * (mu - log_liq[i - 1])
        flow = 0.01 * (volume[i] / base_volume - 1.0)
        shock = -1.5 * abs(returns[i]) * (1 if regime[i] else 0.3)
        log_liq[i] = log_liq[i - 1] + drift + flow + shock + rng.normal(0, 0.003)
    liquidity = np.exp(log_liq)

    buy_share = np.clip(0.5 + 4.0 * returns + rng.normal(0, 0.05, n), 0.1, 0.9)
    utilization = np.clip(10.0 * volume / liquidity + rng.normal(0, 0.02, n), 0, 1)

    collateral = np.empty(n)
    collateral[0] = collateral_mean
    for i in range(1, n):
        collateral[i] = np.clip(
            collateral[i - 1]
            + 0.05 * (collateral_mean - collateral[i - 1])
            + rng.normal(0, 0.02),
            0.8,
            3.0,
        )

    records: List[Dict[str, Any]] = []
    for i in range(n):
        records.append(
            {
                "timestamp": (start + timedelta(hours=i)).isoformat(),
                "price": float(price[i]),
                "volume": float(volume[i]),
                "liquidity": float(liquidity[i]),
                "buy_volume": float(volume[i] * buy_share[i]),
                "sell_volume": float(volume[i] * (1 - buy_share[i])),
                "pool_utilisation": float(utilization[i]),
                "utilization": float(utilization[i]),
                "collateral_ratio": float(collateral[i]),
                "verified": float(verified),
            }
        )
    return records


def transaction_records(
    n: int = 2000, seed: int = 0, anomaly_fraction: float = 0.03
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    rng = np.random.default_rng(seed)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    records: List[Dict[str, Any]] = []
    labels = np.zeros(n, dtype=int)
    is_anomaly = rng.random(n) < anomaly_fraction

    for i in range(n):
        day = int(rng.integers(0, 90))
        hour = int(np.clip(rng.normal(13, 4), 0, 23))
        ts = base + timedelta(days=day, hours=hour, minutes=int(rng.integers(0, 60)))
        amount = float(np.clip(rng.lognormal(6.0, 1.1), 1, 40_000))
        avg_amount = float(amount * rng.lognormal(0.0, 0.3))
        rec = {
            "amount": amount,
            "avg_amount_30d": avg_amount,
            "timestamp": ts.isoformat(),
            "tx_count_24h": float(rng.poisson(2)),
            "tx_count_30d": float(rng.poisson(20)),
            "account_age_days": float(rng.exponential(400) + 30),
            "kyc_score": float(rng.beta(8, 2)),
            "country_risk": float(rng.choice([0, 0.2, 0.5], p=[0.8, 0.15, 0.05])),
            "counterparties_30d": float(rng.poisson(8)),
            "cross_border": float(rng.random() < 0.15),
        }
        if is_anomaly[i]:
            labels[i] = 1
            kind = int(rng.integers(0, 4))
            if kind == 0:
                rec["amount"] = float(amount * rng.lognormal(3.0, 0.5))
                rec["tx_count_24h"] = float(rng.poisson(18))
            elif kind == 1:
                rec["account_age_days"] = float(rng.uniform(0, 5))
                rec["amount"] = float(rng.uniform(8_000, 90_000))
                rec["kyc_score"] = float(rng.uniform(0, 0.3))
            elif kind == 2:
                rec["country_risk"] = float(rng.uniform(0.8, 1.0))
                rec["cross_border"] = 1.0
                rec["amount"] = float(rng.uniform(5_000, 120_000))
            else:
                night = ts.replace(hour=int(rng.integers(1, 5)))
                rec["timestamp"] = night.isoformat()
                rec["amount"] = float(rng.uniform(9_200, 9_900))
                rec["tx_count_24h"] = float(rng.poisson(14))
                rec["counterparties_30d"] = float(rng.poisson(40))
        records.append(rec)
    return records, labels


def compliance_labels(frame: pd.DataFrame) -> np.ndarray:
    amount = frame["amount"].to_numpy()
    count_24h = frame["tx_count_24h"].to_numpy()
    country = frame["country_risk"].to_numpy()
    kyc = frame["kyc_score"].to_numpy()
    age = frame["account_age_days"].to_numpy()
    cross = frame["cross_border"].to_numpy()
    ratio = amount / frame["avg_amount_30d"].to_numpy()

    aml = ((amount >= 9_000) & (count_24h >= 8)) | ((ratio >= 10) & (country >= 0.5))
    kyc_v = (kyc < 0.3) | ((age < 7) & (amount >= 5_000))
    sanctions = (country >= 0.8) & (amount >= 1_000)
    limit = amount >= 50_000
    reporting = (amount >= 10_000) & (cross >= 0.5)
    general = (aml | kyc_v | sanctions) & (ratio >= 5)
    return np.column_stack([aml, kyc_v, sanctions, limit, reporting, general]).astype(
        np.float32
    )


def supply_chain_frame(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(n)

    noise = np.zeros(n)
    for i in range(1, n):
        noise[i] = 0.7 * noise[i - 1] + rng.normal(0, 4)
    demand = (
        100 + 20 * np.sin(2 * np.pi * t / 30) + 8 * np.cos(2 * np.pi * t / 7) + noise
    )

    lead_time = np.clip(7 + 0.03 * (demand - 100) + rng.normal(0, 1.2, n), 1, None)
    reliability = np.clip(
        0.93 - 0.004 * (lead_time - 7) + rng.normal(0, 0.02, n), 0.5, 1
    )
    shipments = np.roll(demand, 3) * reliability + rng.normal(0, 2, n)
    inventory = np.clip(500 - 2.0 * (demand - 100) + rng.normal(0, 15, n), 0, None)
    price_index = 100 + np.cumsum(rng.normal(0, 0.3, n)) * 0.2 + 0.1 * (demand - 100)
    freight = 50 + 0.15 * price_index + rng.normal(0, 2, n)
    backlog = (
        pd.Series(np.clip(demand - shipments, 0, None)).ewm(span=10).mean().to_numpy()
    )
    utilization = np.clip(demand / 150, 0, 1)
    defects = np.clip(0.02 + 0.01 * rng.normal(0, 1, n), 0, 0.2)

    frame = pd.DataFrame(
        {
            "demand": demand,
            "inventory_level": inventory,
            "lead_time_days": lead_time,
            "supplier_reliability": reliability,
            "shipment_volume": shipments,
            "price_index": price_index,
            "freight_cost": freight,
            "order_backlog": backlog,
            "utilization": utilization,
            "defect_rate": defects,
            "season_sin": np.sin(2 * np.pi * t / 30),
            "season_cos": np.cos(2 * np.pi * t / 30),
        }
    )
    return frame[list(SUPPLY_CHAIN_FEATURES)]
