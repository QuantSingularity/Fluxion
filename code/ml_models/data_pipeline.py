"""
Fluxion ML Data Pipeline
════════════════════════
Production-grade feature-engineering and preprocessing pipeline for
DeFi time-series data feeding into the Fluxion ML models.

Key responsibilities
────────────────────
  1. Raw ingestion — accepts either a list-of-dicts or a DataFrame.
  2. Cleaning       — removes zero-price / zero-volume rows, forward-fills
                      missing oracle prices, clips extreme outliers.
  3. Feature engineering
       • Price features  : velocity (1-period return), log-return,
                           rolling volatility (7 / 30-period std),
                           ATH / ATL distance, momentum (RSI proxy).
       • Liquidity feats : depth imbalance, utilisation ratio,
                           Z-score relative to a rolling 30-period window.
       • Volume features : VWAP, volume momentum, buy/sell pressure proxy.
       • Cross-asset     : correlation with a synthetic "market index"
                           built from the input pool, rolling beta estimate.
       • Temporal        : hour-of-day, day-of-week, is_weekend one-hots
                           (DeFi activity is strongly time-dependent).
  4. Normalisation    — RobustScaler (median / IQR) for continuous features;
                        MinMaxScaler for bounded ratios; passthrough for
                        one-hot flags.
  5. Train / val split — chronological (no leakage) with a configurable
                         validation fraction and an optional holdout window.
  6. Sequence builder  — converts the flat feature matrix into overlapping
                         (seq_len, n_features) windows for LSTM / Transformer
                         models, yielding (X, y) tensors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Configuration dataclass
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class PipelineConfig:
    """Hyper-parameters that govern the data pipeline behaviour."""

    # Sequence modelling
    seq_len: int = 64  # Look-back window length fed to LSTM / Transformer
    forecast_horizon: int = 1  # Steps ahead to predict (1 = next period)

    # Rolling window lengths
    short_window: int = 7
    long_window: int = 30

    # Train / validation split (chronological)
    val_fraction: float = 0.15
    holdout_fraction: float = 0.05  # Final holdout kept completely unseen

    # Outlier clipping (±N × IQR)
    outlier_iqr_multiplier: float = 5.0

    # Minimum rows required after cleaning before raising
    min_rows_after_clean: int = seq_len + forecast_horizon

    # Columns that must be present in the raw input
    required_raw_cols: List[str] = field(
        default_factory=lambda: [
            "timestamp",
            "price",
            "volume",
            "liquidity",
        ]
    )

    # Optional columns that are used if present
    optional_raw_cols: List[str] = field(
        default_factory=lambda: [
            "volatility",
            "arbitrage_opportunities",
            "buy_volume",
            "sell_volume",
            "pool_utilisation",
        ]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Feature groups (used for selective scaler assignment)
# ──────────────────────────────────────────────────────────────────────────────

# Continuous features normalised with RobustScaler
_ROBUST_FEATURES = [
    "log_return",
    "price_velocity",
    "vol_7",
    "vol_30",
    "vwap",
    "volume_momentum",
    "liquidity_zscore_30",
    "buy_sell_imbalance",
    "pool_utilisation",
    "beta_30",
    "correlation_30",
]

# Bounded ratio features normalised with MinMaxScaler [0, 1]
_MINMAX_FEATURES = [
    "rsi_14",
    "ath_distance",
    "atl_distance",
    "depth_imbalance",
    "vol_regime",  # 0 = low vol, 1 = high vol (normalised σ)
]

# Binary / one-hot flags — passed through unchanged
_PASSTHROUGH_FEATURES = [
    "is_weekend",
]

# Temporal cyclical encodings — passed through unchanged
_CYCLICAL_FEATURES = [
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
]

ALL_FEATURES = (
    _ROBUST_FEATURES + _MINMAX_FEATURES + _PASSTHROUGH_FEATURES + _CYCLICAL_FEATURES
)


# ──────────────────────────────────────────────────────────────────────────────
# DataPipeline
# ──────────────────────────────────────────────────────────────────────────────


class DataPipeline:
    """
    End-to-end data pipeline for Fluxion ML models.

    Usage
    ─────
    >>> pipeline = DataPipeline(config)
    >>> features_df = pipeline.transform(raw_data)          # fit + transform
    >>> X_train, y_train, X_val, y_val = pipeline.build_sequences(features_df)

    For inference on new batches (scalers already fitted):
    >>> features_df = pipeline.transform(raw_data, fit=False)
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self._robust_scaler = RobustScaler()
        self._minmax_scaler = MinMaxScaler(feature_range=(0, 1))
        self._fitted = False

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def transform(
        self,
        raw_data: Any,
        fit: bool = True,
    ) -> pd.DataFrame:
        """
        Ingest, clean, engineer features, and normalise.

        Parameters
        ──────────
        raw_data : list[dict] | pd.DataFrame
            Raw OHLCV / liquidity records.
        fit : bool
            Whether to fit the scalers on this data (True for training,
            False for validation / inference).

        Returns
        ───────
        pd.DataFrame  with ALL_FEATURES columns, indexed by timestamp.
        """
        df = self._ingest(raw_data)
        df = self._clean(df)
        df = self._engineer_features(df)
        df = self._normalise(df, fit=fit)
        logger.info(
            "DataPipeline.transform: %d rows, %d features",
            len(df),
            df.shape[1],
        )
        return df

    def build_sequences(
        self,
        features_df: pd.DataFrame,
        target_col: str = "log_return",
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Build overlapping (seq_len × n_features) windows and split
        chronologically into train and validation sets.

        Returns  (X_train, y_train, X_val, y_val)
        """
        cfg = self.config
        X, y = self._make_windows(features_df, target_col)
        if len(X) == 0:
            raise ValueError(
                "No sequences could be built — check seq_len vs data length"
            )

        n = len(X)
        n_hld = max(1, int(n * cfg.holdout_fraction))
        n_val = max(1, int((n - n_hld) * cfg.val_fraction))
        n_train = n - n_hld - n_val

        X_train, y_train = X[:n_train], y[:n_train]
        X_val, y_val = X[n_train : n_train + n_val], y[n_train : n_train + n_val]

        logger.info(
            "Sequences — train: %d, val: %d, holdout: %d",
            n_train,
            n_val,
            n_hld,
        )
        return X_train, y_train, X_val, y_val

    def get_feature_names(self) -> List[str]:
        return ALL_FEATURES

    def is_fitted(self) -> bool:
        return self._fitted

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _ingest(self, raw_data: Any) -> pd.DataFrame:
        """Convert raw input to a cleaned, time-indexed DataFrame."""
        if isinstance(raw_data, pd.DataFrame):
            df = raw_data.copy()
        elif isinstance(raw_data, (list, tuple)):
            df = pd.DataFrame(raw_data)
        else:
            raise TypeError(f"Unsupported input type: {type(raw_data)}")

        # Validate required columns
        missing = set(self.config.required_raw_cols) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Parse timestamp
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

        df = df.set_index("timestamp").sort_index()

        # Add optional cols if absent
        for col in self.config.optional_raw_cols:
            if col not in df.columns:
                df[col] = np.nan

        return df

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop bad rows, forward-fill gaps, and clip extreme outliers."""
        # Remove clearly invalid rows
        df = df[(df["price"] > 0) & (df["volume"] >= 0)].copy()

        # Forward-fill missing oracle prices (short gaps only)
        df["price"] = df["price"].ffill(limit=5)
        df["liquidity"] = df["liquidity"].ffill(limit=5).fillna(0)

        # Clip price and volume outliers using IQR
        for col in ("price", "volume"):
            q25, q75 = df[col].quantile([0.25, 0.75])
            iqr = q75 - q25
            lo = q25 - self.config.outlier_iqr_multiplier * iqr
            hi = q75 + self.config.outlier_iqr_multiplier * iqr
            df[col] = df[col].clip(lo, hi)

        df = df.dropna(subset=["price"])

        min_rows = self.config.min_rows_after_clean
        if len(df) < min_rows:
            raise ValueError(
                f"Only {len(df)} rows after cleaning; " f"at least {min_rows} required."
            )
        return df

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:  # noqa: C901
        """Compute the full feature set from raw OHLCV / liquidity columns."""
        cfg = self.config
        out = pd.DataFrame(index=df.index)

        p = df["price"].astype(float)
        v = df["volume"].astype(float)
        l = df["liquidity"].astype(float)

        # ── Price features ────────────────────────────────────────────────────
        out["log_return"] = np.log(p / p.shift(1))
        out["price_velocity"] = p.pct_change()
        out["vol_7"] = out["log_return"].rolling(cfg.short_window).std()
        out["vol_30"] = out["log_return"].rolling(cfg.long_window).std()

        # ATH / ATL distance (rolling 90-period)
        ath = p.rolling(90).max()
        atl = p.rolling(90).min()
        out["ath_distance"] = ((ath - p) / ath).clip(0, 1)
        out["atl_distance"] = ((p - atl) / ath).clip(0, 1)

        # RSI-14 proxy (simple momentum oscillator)
        delta = p.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        out["rsi_14"] = (100 - 100 / (1 + rs)).clip(0, 100) / 100  # normalised

        # Volatility regime: compare current daily vol to its own 60-day median
        daily_vol = out["vol_7"].rolling(60).median().replace(0, np.nan)
        out["vol_regime"] = (out["vol_7"] / daily_vol).clip(0, 3) / 3  # [0, 1]

        # ── Volume features ───────────────────────────────────────────────────
        vwap_num = (p * v).rolling(cfg.short_window).sum()
        vwap_den = v.rolling(cfg.short_window).sum().replace(0, np.nan)
        out["vwap"] = vwap_num / vwap_den
        out["volume_momentum"] = v.pct_change(periods=cfg.short_window)

        if "buy_volume" in df.columns and "sell_volume" in df.columns:
            bv = df["buy_volume"].astype(float).fillna(0)
            sv = df["sell_volume"].astype(float).fillna(0)
            total = (bv + sv).replace(0, np.nan)
            out["buy_sell_imbalance"] = ((bv - sv) / total).fillna(0)
        else:
            out["buy_sell_imbalance"] = 0.0

        # ── Liquidity features ───────────────────────────────────────────────
        liq_roll_mean = l.rolling(cfg.long_window).mean()
        liq_roll_std = l.rolling(cfg.long_window).std().replace(0, np.nan)
        out["liquidity_zscore_30"] = (l - liq_roll_mean) / liq_roll_std

        if "pool_utilisation" in df.columns:
            out["pool_utilisation"] = df["pool_utilisation"].astype(float).clip(0, 1)
        else:
            # Proxy: volume / liquidity (capped at 1)
            out["pool_utilisation"] = (v / l.replace(0, np.nan)).clip(0, 1).fillna(0)

        # Depth imbalance proxy (ask / bid normalised via VWAP deviation)
        out["depth_imbalance"] = (
            (p - out["vwap"]) / out["vwap"].replace(0, np.nan)
        ).clip(-1, 1) / 2 + 0.5

        # ── Cross-asset features (synthetic market index) ─────────────────────
        # Build a simple equal-weight price index from the available series
        market_ret = out["log_return"].rolling(cfg.long_window).mean()  # proxy
        cov = out["log_return"].rolling(cfg.long_window).cov(market_ret)
        var_mkt = market_ret.rolling(cfg.long_window).var().replace(0, np.nan)
        out["beta_30"] = (cov / var_mkt).clip(-3, 3)
        out["correlation_30"] = (
            out["log_return"].rolling(cfg.long_window).corr(market_ret)
        )

        # ── Temporal features ─────────────────────────────────────────────────
        if hasattr(df.index, "hour"):
            h = df.index.hour.astype(float)
            d = df.index.dayofweek.astype(float)
        else:
            h = pd.to_datetime(df.index).hour.astype(float)
            d = pd.to_datetime(df.index).dayofweek.astype(float)

        out["hour_sin"] = np.sin(2 * np.pi * h / 24)
        out["hour_cos"] = np.cos(2 * np.pi * h / 24)
        out["dow_sin"] = np.sin(2 * np.pi * d / 7)
        out["dow_cos"] = np.cos(2 * np.pi * d / 7)
        out["is_weekend"] = (d >= 5).astype(float)

        # ── Final clean-up ────────────────────────────────────────────────────
        out = out.replace([np.inf, -np.inf], np.nan)
        out = out.ffill(limit=3).bfill(limit=3)
        out = out.dropna(subset=_ROBUST_FEATURES + _MINMAX_FEATURES)

        return out[ALL_FEATURES]

    def _normalise(self, df: pd.DataFrame, fit: bool) -> pd.DataFrame:
        """Apply RobustScaler to continuous cols and MinMaxScaler to ratio cols."""
        if df.empty:
            return df

        out = df.copy()

        # Continuous features → RobustScaler
        robust_present = [c for c in _ROBUST_FEATURES if c in out.columns]
        if robust_present:
            if fit:
                out[robust_present] = self._robust_scaler.fit_transform(
                    out[robust_present]
                )
            else:
                out[robust_present] = self._robust_scaler.transform(out[robust_present])

        # Bounded ratio features → MinMaxScaler
        minmax_present = [c for c in _MINMAX_FEATURES if c in out.columns]
        if minmax_present:
            if fit:
                out[minmax_present] = self._minmax_scaler.fit_transform(
                    out[minmax_present]
                )
            else:
                out[minmax_present] = self._minmax_scaler.transform(out[minmax_present])

        if fit:
            self._fitted = True

        return out

    def _make_windows(
        self,
        df: pd.DataFrame,
        target_col: str,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Slide a window of length `seq_len` over the feature matrix and collect
        the next `forecast_horizon` steps of `target_col` as labels.
        """
        cfg = self.config
        arr = df[ALL_FEATURES].values.astype(np.float32)
        tgt = (
            df[target_col].values.astype(np.float32)
            if target_col in df.columns
            else np.zeros(len(df), dtype=np.float32)
        )
        n = len(arr)
        limit = n - cfg.seq_len - cfg.forecast_horizon + 1

        if limit <= 0:
            return np.empty((0, cfg.seq_len, len(ALL_FEATURES))), np.empty(0)

        X = np.stack([arr[i : i + cfg.seq_len] for i in range(limit)])
        y = np.array(
            [tgt[i + cfg.seq_len + cfg.forecast_horizon - 1] for i in range(limit)]
        )
        return X, y
