from typing import Any, Dict, Tuple

LIQUIDITY_SEQ_LEN = 24
SUPPLY_CHAIN_SEQ_LEN = 30
SUPPLY_CHAIN_HORIZON = 5
RISK_SEQ_LEN = 30
RISK_WARMUP = 20
MAX_RECORDS = 5000
MAX_TRAIN_RECORDS = 500000
LIQUIDITY_HORIZON = 6

RISK_FACTORS: Tuple[str, ...] = (
    "market_risk",
    "credit_risk",
    "liquidity_risk",
    "operational_risk",
    "compliance_risk",
)
RISK_FACTOR_WEIGHTS: Tuple[float, ...] = (0.30, 0.20, 0.20, 0.15, 0.15)

RISK_FEATURES: Tuple[str, ...] = (
    "volatility",
    "price_change",
    "drawdown",
    "rsi",
    "macd",
    "bollinger_position",
    "volume_change",
    "volume_liquidity_ratio",
    "liquidity_change",
    "utilization",
    "collateral_ratio",
    "verified",
)

VIOLATION_TYPES: Tuple[str, ...] = (
    "aml_violation",
    "kyc_violation",
    "sanctions_violation",
    "transaction_limit_violation",
    "reporting_violation",
    "general_violation",
)

TRANSACTION_FEATURES: Tuple[str, ...] = (
    "log_amount",
    "log_amount_ratio",
    "log_tx_count_24h",
    "log_tx_count_30d",
    "log_account_age_days",
    "kyc_score",
    "country_risk",
    "log_counterparties_30d",
    "hour_sin",
    "hour_cos",
    "is_weekend",
    "cross_border",
)

TRANSACTION_DEFAULTS: Dict[str, float] = {
    "tx_count_24h": 2.0,
    "tx_count_30d": 20.0,
    "account_age_days": 365.0,
    "kyc_score": 0.8,
    "country_risk": 0.0,
    "counterparties_30d": 8.0,
    "cross_border": 0.0,
}

SUPPLY_CHAIN_FEATURES: Tuple[str, ...] = (
    "demand",
    "inventory_level",
    "lead_time_days",
    "supplier_reliability",
    "shipment_volume",
    "price_index",
    "freight_cost",
    "order_backlog",
    "utilization",
    "defect_rate",
    "season_sin",
    "season_cos",
)
SUPPLY_CHAIN_TARGET = "demand"

MODEL_TYPES: Tuple[str, ...] = (
    "liquidity",
    "supply_chain",
    "risk",
    "anomaly",
    "compliance",
)

PROFILES: Dict[str, Dict[str, Any]] = {
    "full": {
        "liquidity": {
            "hidden_size": 64,
            "num_layers": 2,
            "dropout": 0.2,
            "epochs": 40,
            "patience": 6,
            "lr": 1e-3,
            "rows": 6000,
        },
        "supply_chain": {
            "hidden_size": 64,
            "num_layers": 2,
            "dropout": 0.2,
            "epochs": 40,
            "patience": 6,
            "lr": 1e-3,
            "rows": 4000,
        },
        "risk": {
            "hidden_size": 64,
            "num_layers": 2,
            "dropout": 0.2,
            "epochs": 40,
            "patience": 6,
            "lr": 1e-3,
            "rows": 6000,
        },
        "anomaly": {
            "encoding_dim": 4,
            "dropout": 0.1,
            "epochs": 60,
            "patience": 8,
            "lr": 1e-3,
            "rows": 8000,
            "contamination": 0.03,
        },
        "compliance": {
            "hidden_size": 64,
            "dropout": 0.2,
            "epochs": 60,
            "patience": 8,
            "lr": 1e-3,
            "rows": 10000,
        },
        "batch_size": 64,
    },
    "quick": {
        "liquidity": {
            "hidden_size": 16,
            "num_layers": 1,
            "dropout": 0.0,
            "epochs": 3,
            "patience": 2,
            "lr": 2e-3,
            "rows": 600,
        },
        "supply_chain": {
            "hidden_size": 16,
            "num_layers": 1,
            "dropout": 0.0,
            "epochs": 3,
            "patience": 2,
            "lr": 2e-3,
            "rows": 400,
        },
        "risk": {
            "hidden_size": 16,
            "num_layers": 1,
            "dropout": 0.0,
            "epochs": 3,
            "patience": 2,
            "lr": 2e-3,
            "rows": 500,
        },
        "anomaly": {
            "encoding_dim": 3,
            "dropout": 0.0,
            "epochs": 8,
            "patience": 3,
            "lr": 2e-3,
            "rows": 1500,
            "contamination": 0.05,
        },
        "compliance": {
            "hidden_size": 16,
            "dropout": 0.0,
            "epochs": 8,
            "patience": 3,
            "lr": 2e-3,
            "rows": 2000,
        },
        "batch_size": 64,
    },
}


def risk_level(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.66:
        return "high"
    if score >= 0.33:
        return "medium"
    return "low"
