from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd
from ml_models.config import (
    MAX_RECORDS,
    RISK_FACTOR_WEIGHTS,
    RISK_FACTORS,
    RISK_FEATURES,
    RISK_SEQ_LEN,
    RISK_WARMUP,
    TRANSACTION_DEFAULTS,
    TRANSACTION_FEATURES,
)


class InputError(ValueError):
    pass


def as_frame(
    records: Any, required: Sequence[str], limit: int = MAX_RECORDS
) -> pd.DataFrame:
    if isinstance(records, pd.DataFrame):
        df = records.copy()
    elif isinstance(records, (list, tuple)):
        df = pd.DataFrame(list(records))
    else:
        raise InputError(f"Unsupported input type: {type(records).__name__}")
    if len(df) == 0:
        raise InputError("No records supplied")
    if len(df) > limit:
        raise InputError(f"At most {limit} records are accepted")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise InputError(f"Missing required fields: {', '.join(missing)}")
    return df


def market_frame(records: Any, limit: int = MAX_RECORDS) -> pd.DataFrame:
    df = as_frame(records, ("timestamp", "price", "volume", "liquidity"), limit)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df[df["timestamp"].notna()].set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    for col in ("price", "volume", "liquidity"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("utilization", "collateral_ratio", "verified"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan
    df["price"] = df["price"].ffill(limit=5)
    df["liquidity"] = df["liquidity"].ffill(limit=5)
    df = df[df["price"].notna() & (df["price"] > 0)]
    df["volume"] = df["volume"].fillna(0).clip(lower=0)
    df["liquidity"] = df["liquidity"].fillna(0).clip(lower=0)
    return df


def min_risk_records() -> int:
    return RISK_SEQ_LEN + RISK_WARMUP


def build_risk_features(records: Any, limit: int = MAX_RECORDS) -> pd.DataFrame:
    df = market_frame(records, limit)
    if len(df) < min_risk_records():
        raise InputError(
            f"Need at least {min_risk_records()} valid records, got {len(df)}"
        )

    p = df["price"].astype(float)
    v = df["volume"].astype(float)
    liq = df["liquidity"].astype(float)
    safe_liq = liq.clip(lower=1e-9)
    safe_vol = v.clip(lower=1e-9)

    out = pd.DataFrame(index=df.index)
    log_ret = np.log(p / p.shift(1))
    out["volatility"] = log_ret.rolling(10).std().clip(0, 1)
    out["price_change"] = log_ret.clip(-0.5, 0.5)
    out["drawdown"] = (1 - p / p.rolling(RISK_SEQ_LEN, min_periods=1).max()).clip(0, 1)

    delta = p.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).clip(0, 100) / 100
    rsi = rsi.where(~((loss == 0) & (gain > 0)), 1.0)
    rsi = rsi.where(~((loss == 0) & (gain == 0)), 0.5)
    out["rsi"] = rsi

    macd = p.ewm(span=12, adjust=False).mean() - p.ewm(span=26, adjust=False).mean()
    out["macd"] = (macd / p).clip(-0.5, 0.5)

    ma = p.rolling(20).mean()
    sd = p.rolling(20).std().replace(0, np.nan)
    out["bollinger_position"] = ((p - ma) / (2 * sd)).clip(-1, 1).fillna(0)

    out["volume_change"] = np.log(safe_vol / safe_vol.shift(1)).clip(-3, 3)
    out["volume_liquidity_ratio"] = (v / safe_liq).clip(0, 5)
    out["liquidity_change"] = np.log(safe_liq / safe_liq.shift(1)).clip(-3, 3)

    util_proxy = (v / safe_liq).clip(0, 1)
    out["utilization"] = df["utilization"].clip(0, 1).fillna(util_proxy)
    out["collateral_ratio"] = df["collateral_ratio"].clip(0, 10).fillna(1.5)
    out["verified"] = df["verified"].clip(0, 1).fillna(1.0)

    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    if len(out) < RISK_SEQ_LEN:
        raise InputError(
            f"Only {len(out)} usable rows after feature warm-up; "
            f"need at least {RISK_SEQ_LEN}"
        )
    return out[list(RISK_FEATURES)]


def risk_targets(features: pd.DataFrame) -> pd.DataFrame:
    f = features
    market = (
        0.45 * np.clip(f["volatility"] / 0.05, 0, 1)
        + 0.30 * np.clip(f["drawdown"] / 0.30, 0, 1)
        + 0.15 * f["bollinger_position"].abs()
        + 0.10 * (f["rsi"] - 0.5).abs() * 2
    )
    credit = (
        0.6 * np.clip((1.5 - f["collateral_ratio"]) / 0.75, 0, 1)
        + 0.4 * f["utilization"]
    )
    liquidity = (
        0.5 * np.clip(f["volume_liquidity_ratio"] / 1.0, 0, 1)
        + 0.3 * np.clip(-f["liquidity_change"] / 0.1, 0, 1)
        + 0.2 * f["utilization"]
    )
    operational = 0.5 * np.clip(f["price_change"].abs() / 0.08, 0, 1) + 0.5 * np.clip(
        f["volume_change"].abs() / 1.5, 0, 1
    )
    compliance = 0.7 * (1 - f["verified"]) + 0.3 * np.clip(
        f["volume_liquidity_ratio"] / 2.0, 0, 1
    )
    out = pd.DataFrame(
        {
            "market_risk": market,
            "credit_risk": credit,
            "liquidity_risk": liquidity,
            "operational_risk": operational,
            "compliance_risk": compliance,
        },
        index=f.index,
    )
    return out.clip(0, 1)[list(RISK_FACTORS)]


def overall_risk(factors: np.ndarray) -> np.ndarray:
    weights = np.asarray(RISK_FACTOR_WEIGHTS, dtype=np.float64)
    return np.clip(np.asarray(factors, dtype=np.float64) @ weights, 0, 1)


def _parse_timestamp(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        raise InputError(f"Invalid timestamp: {value!r}")
    return ts.to_pydatetime()


def _number(record: Dict[str, Any], key: str, default: float) -> float:
    raw = record.get(key)
    if raw is None:
        return float(default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise InputError(f"Field '{key}' must be numeric")
    if not np.isfinite(value):
        raise InputError(f"Field '{key}' must be finite")
    return value


def transaction_frame(
    records: Iterable[Dict[str, Any]], limit: int = MAX_RECORDS
) -> pd.DataFrame:
    items: List[Dict[str, Any]] = list(records)
    if not items:
        raise InputError("No transactions supplied")
    if len(items) > limit:
        raise InputError(f"At most {limit} transactions are accepted")
    rows = []
    for i, rec in enumerate(items):
        if not isinstance(rec, dict):
            raise InputError(f"Transaction {i} must be an object")
        if "amount" not in rec:
            raise InputError(f"Transaction {i} is missing 'amount'")
        amount = _number(rec, "amount", 0.0)
        if amount < 0:
            raise InputError(f"Transaction {i} has a negative amount")
        ts = _parse_timestamp(rec.get("timestamp"))
        avg = _number(rec, "avg_amount_30d", amount if amount > 0 else 1.0)
        rows.append(
            {
                "amount": min(amount, 1e12),
                "avg_amount_30d": max(min(avg, 1e12), 1e-9),
                "tx_count_24h": max(
                    _number(rec, "tx_count_24h", TRANSACTION_DEFAULTS["tx_count_24h"]),
                    0.0,
                ),
                "tx_count_30d": max(
                    _number(rec, "tx_count_30d", TRANSACTION_DEFAULTS["tx_count_30d"]),
                    0.0,
                ),
                "account_age_days": max(
                    _number(
                        rec,
                        "account_age_days",
                        TRANSACTION_DEFAULTS["account_age_days"],
                    ),
                    0.0,
                ),
                "kyc_score": float(
                    np.clip(
                        _number(rec, "kyc_score", TRANSACTION_DEFAULTS["kyc_score"]),
                        0,
                        1,
                    )
                ),
                "country_risk": float(
                    np.clip(
                        _number(
                            rec, "country_risk", TRANSACTION_DEFAULTS["country_risk"]
                        ),
                        0,
                        1,
                    )
                ),
                "counterparties_30d": max(
                    _number(
                        rec,
                        "counterparties_30d",
                        TRANSACTION_DEFAULTS["counterparties_30d"],
                    ),
                    0.0,
                ),
                "cross_border": float(
                    np.clip(
                        _number(
                            rec, "cross_border", TRANSACTION_DEFAULTS["cross_border"]
                        ),
                        0,
                        1,
                    )
                ),
                "hour": float(ts.hour),
                "is_weekend": float(ts.weekday() >= 5),
            }
        )
    return pd.DataFrame(rows)


def transaction_features(frame: pd.DataFrame) -> np.ndarray:
    ratio = (frame["amount"] / frame["avg_amount_30d"]).clip(0, 1000)
    hours = frame["hour"].astype(float)
    cols = {
        "log_amount": np.log1p(frame["amount"]),
        "log_amount_ratio": np.log1p(ratio),
        "log_tx_count_24h": np.log1p(frame["tx_count_24h"]),
        "log_tx_count_30d": np.log1p(frame["tx_count_30d"]),
        "log_account_age_days": np.log1p(frame["account_age_days"]),
        "kyc_score": frame["kyc_score"],
        "country_risk": frame["country_risk"],
        "log_counterparties_30d": np.log1p(frame["counterparties_30d"]),
        "hour_sin": np.sin(2 * np.pi * hours / 24),
        "hour_cos": np.cos(2 * np.pi * hours / 24),
        "is_weekend": frame["is_weekend"],
        "cross_border": frame["cross_border"],
    }
    matrix = np.column_stack(
        [np.asarray(cols[name], dtype=np.float64) for name in TRANSACTION_FEATURES]
    )
    return matrix.astype(np.float32)
