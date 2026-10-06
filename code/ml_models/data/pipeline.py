from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    seq_len: int = 64
    forecast_horizon: int = 1
    short_window: int = 7
    long_window: int = 30
    extrema_window: int = 90
    regime_window: int = 60
    val_fraction: float = 0.15
    holdout_fraction: float = 0.05
    outlier_iqr_multiplier: float = 5.0
    max_gap_fill: int = 5
    min_rows_after_clean: Optional[int] = None
    required_raw_cols: List[str] = field(
        default_factory=lambda: ["timestamp", "price", "volume", "liquidity"]
    )
    optional_raw_cols: List[str] = field(
        default_factory=lambda: [
            "volatility",
            "arbitrage_opportunities",
            "buy_volume",
            "sell_volume",
            "pool_utilisation",
        ]
    )

    def __post_init__(self) -> None:
        if self.min_rows_after_clean is None:
            self.min_rows_after_clean = (
                self.seq_len + self.forecast_horizon + self.warmup_rows
            )

    @property
    def warmup_rows(self) -> int:
        return max(
            self.extrema_window,
            self.regime_window + self.short_window,
            2 * self.long_window,
        )

    @property
    def train_fraction(self) -> float:
        return max(0.1, 1.0 - self.val_fraction - self.holdout_fraction)


_ROBUST_FEATURES = [
    "log_return",
    "price_velocity",
    "vol_7",
    "vol_30",
    "vwap",
    "volume_momentum",
    "liquidity_zscore_30",
    "liquidity_log_change",
    "buy_sell_imbalance",
    "beta_30",
    "correlation_30",
]

_MINMAX_FEATURES = [
    "rsi_14",
    "ath_distance",
    "atl_distance",
    "depth_imbalance",
    "vol_regime",
    "pool_utilisation",
]

_PASSTHROUGH_FEATURES = ["is_weekend"]

_CYCLICAL_FEATURES = ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]

ALL_FEATURES = (
    _ROBUST_FEATURES + _MINMAX_FEATURES + _PASSTHROUGH_FEATURES + _CYCLICAL_FEATURES
)


class DataPipeline:
    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self._robust_scaler = RobustScaler()
        self._minmax_scaler = MinMaxScaler(feature_range=(0, 1), clip=True)
        self._fitted = False

    def transform(self, raw_data: Any, fit: bool = True) -> pd.DataFrame:
        df = self._ingest(raw_data)
        df = self._clean(df)
        df = self._engineer_features(df)
        df = self._normalise(df, fit=fit)
        logger.info(
            "DataPipeline.transform: %d rows, %d features", len(df), df.shape[1]
        )
        return df

    def build_sequences(
        self,
        features_df: pd.DataFrame,
        target_col: str = "log_return",
        include_holdout: bool = False,
    ) -> Tuple[np.ndarray, ...]:
        cfg = self.config
        X, y = self._make_windows(features_df, target_col)
        if len(X) == 0:
            raise ValueError(
                "No sequences could be built - check seq_len vs data length"
            )

        n = len(X)
        n_hld = max(1, int(n * cfg.holdout_fraction))
        n_val = max(1, int((n - n_hld) * cfg.val_fraction))
        n_train = n - n_hld - n_val
        if n_train < 1:
            raise ValueError("Not enough sequences for a train/validation split")

        X_train, y_train = X[:n_train], y[:n_train]
        X_val, y_val = X[n_train : n_train + n_val], y[n_train : n_train + n_val]

        logger.info(
            "Sequences - train: %d, val: %d, holdout: %d", n_train, n_val, n_hld
        )
        if include_holdout:
            X_hld, y_hld = X[n_train + n_val :], y[n_train + n_val :]
            return X_train, y_train, X_val, y_val, X_hld, y_hld
        return X_train, y_train, X_val, y_val

    def last_window(self, features_df: pd.DataFrame) -> np.ndarray:
        seq_len = self.config.seq_len
        if len(features_df) < seq_len:
            raise ValueError(
                f"Need at least {seq_len} usable rows after feature warm-up, "
                f"got {len(features_df)}"
            )
        window = features_df[ALL_FEATURES].values[-seq_len:].astype(np.float32)
        return window[np.newaxis, :, :]

    def inverse_target(self, values: Any, column: str) -> np.ndarray:
        arr = np.asarray(values, dtype=np.float64)
        if column not in _ROBUST_FEATURES:
            return arr
        idx = _ROBUST_FEATURES.index(column)
        return arr * self._robust_scaler.scale_[idx] + self._robust_scaler.center_[idx]

    def scale_of(self, column: str) -> float:
        if column not in _ROBUST_FEATURES:
            return 1.0
        return float(self._robust_scaler.scale_[_ROBUST_FEATURES.index(column)])

    def get_feature_names(self) -> List[str]:
        return ALL_FEATURES

    def is_fitted(self) -> bool:
        return self._fitted

    def save(self, path: Any) -> None:
        joblib.dump(self, Path(path))

    @staticmethod
    def load(path: Any) -> "DataPipeline":
        obj = joblib.load(Path(path))
        if not isinstance(obj, DataPipeline):
            raise TypeError("Artifact is not a DataPipeline")
        return obj

    def _ingest(self, raw_data: Any) -> pd.DataFrame:
        if isinstance(raw_data, pd.DataFrame):
            df = raw_data.copy()
        elif isinstance(raw_data, (list, tuple)):
            df = pd.DataFrame(list(raw_data))
        else:
            raise TypeError(f"Unsupported input type: {type(raw_data)}")

        missing = set(self.config.required_raw_cols) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

        df = df[df["timestamp"].notna()]
        df = df.set_index("timestamp").sort_index()
        df = df[~df.index.duplicated(keep="last")]

        for col in ("price", "volume", "liquidity"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

        for col in self.config.optional_raw_cols:
            if col not in df.columns:
                df[col] = np.nan
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        df = df.copy()
        df["price"] = df["price"].ffill(limit=cfg.max_gap_fill)
        df["liquidity"] = df["liquidity"].ffill(limit=cfg.max_gap_fill).fillna(0)
        df["volume"] = df["volume"].fillna(0)

        df = df[
            df["price"].notna()
            & (df["price"] > 0)
            & (df["volume"] >= 0)
            & (df["liquidity"] >= 0)
        ].copy()

        if len(df) > 0:
            for col in ("price", "volume"):
                q25, q75 = df[col].quantile([0.25, 0.75])
                iqr = q75 - q25
                lo = q25 - cfg.outlier_iqr_multiplier * iqr
                hi = q75 + cfg.outlier_iqr_multiplier * iqr
                df[col] = df[col].clip(lo, hi)

        min_rows = int(cfg.min_rows_after_clean or 0)
        if len(df) < min_rows:
            raise ValueError(
                f"Only {len(df)} rows after cleaning; at least {min_rows} required."
            )
        return df

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        out = pd.DataFrame(index=df.index)

        p = df["price"].astype(float)
        v = df["volume"].astype(float)
        liq = df["liquidity"].astype(float)

        out["log_return"] = np.log(p / p.shift(1))
        out["price_velocity"] = p.pct_change()
        out["vol_7"] = out["log_return"].rolling(cfg.short_window).std()
        out["vol_30"] = out["log_return"].rolling(cfg.long_window).std()

        ath = p.rolling(cfg.extrema_window).max()
        atl = p.rolling(cfg.extrema_window).min()
        out["ath_distance"] = ((ath - p) / ath).clip(0, 1)
        out["atl_distance"] = ((p - atl) / ath).clip(0, 1)

        delta = p.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        out["rsi_14"] = (100 - 100 / (1 + rs)).clip(0, 100) / 100

        regime_base = (
            out["vol_7"].rolling(cfg.regime_window).median().replace(0, np.nan)
        )
        out["vol_regime"] = (out["vol_7"] / regime_base).clip(0, 3) / 3

        vwap_num = (p * v).rolling(cfg.short_window).sum()
        vwap_den = v.rolling(cfg.short_window).sum().replace(0, np.nan)
        out["vwap"] = vwap_num / vwap_den
        out["volume_momentum"] = v.pct_change(periods=cfg.short_window)

        bv = df["buy_volume"].astype(float).fillna(0)
        sv = df["sell_volume"].astype(float).fillna(0)
        total = (bv + sv).replace(0, np.nan)
        out["buy_sell_imbalance"] = ((bv - sv) / total).fillna(0)

        liq_mean = liq.rolling(cfg.long_window).mean()
        liq_std = liq.rolling(cfg.long_window).std().replace(0, np.nan)
        out["liquidity_zscore_30"] = (liq - liq_mean) / liq_std
        safe_liq = liq.clip(lower=1e-9)
        out["liquidity_log_change"] = np.log(safe_liq / safe_liq.shift(1))

        util_proxy = (v / liq.replace(0, np.nan)).clip(0, 1)
        util_raw = df["pool_utilisation"].astype(float).clip(0, 1)
        out["pool_utilisation"] = util_raw.fillna(util_proxy).fillna(0)

        out["depth_imbalance"] = (
            (p - out["vwap"]) / out["vwap"].replace(0, np.nan)
        ).clip(-1, 1) / 2 + 0.5

        market_ret = out["log_return"].rolling(cfg.long_window).mean()
        cov = out["log_return"].rolling(cfg.long_window).cov(market_ret)
        var_mkt = market_ret.rolling(cfg.long_window).var().replace(0, np.nan)
        out["beta_30"] = (cov / var_mkt).clip(-3, 3)
        out["correlation_30"] = (
            out["log_return"].rolling(cfg.long_window).corr(market_ret)
        )

        idx = pd.DatetimeIndex(df.index)
        hours = idx.hour.astype(float)
        dows = idx.dayofweek.astype(float)
        out["hour_sin"] = np.sin(2 * np.pi * hours / 24)
        out["hour_cos"] = np.cos(2 * np.pi * hours / 24)
        out["dow_sin"] = np.sin(2 * np.pi * dows / 7)
        out["dow_cos"] = np.cos(2 * np.pi * dows / 7)
        out["is_weekend"] = (dows >= 5).astype(float)

        out = out.replace([np.inf, -np.inf], np.nan)
        out = out.ffill(limit=3)
        out = out.dropna(subset=_ROBUST_FEATURES + _MINMAX_FEATURES)

        if out.empty:
            raise ValueError(
                f"No rows remain after feature warm-up; provide more than "
                f"{cfg.warmup_rows} records"
            )
        return out[ALL_FEATURES]

    def _normalise(self, df: pd.DataFrame, fit: bool) -> pd.DataFrame:
        if df.empty:
            return df
        if not fit and not self._fitted:
            raise RuntimeError("DataPipeline must be fitted before fit=False use")

        out = df.copy()
        fit_rows = max(2, int(len(out) * self.config.train_fraction))

        if fit:
            self._robust_scaler.fit(out[_ROBUST_FEATURES].iloc[:fit_rows])
            self._minmax_scaler.fit(out[_MINMAX_FEATURES].iloc[:fit_rows])
            self._fitted = True

        out[_ROBUST_FEATURES] = self._robust_scaler.transform(out[_ROBUST_FEATURES])
        out[_MINMAX_FEATURES] = self._minmax_scaler.transform(out[_MINMAX_FEATURES])
        return out

    def _make_windows(
        self, df: pd.DataFrame, target_col: str
    ) -> Tuple[np.ndarray, np.ndarray]:
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
            return (
                np.empty((0, cfg.seq_len, len(ALL_FEATURES)), dtype=np.float32),
                np.empty(0, dtype=np.float32),
            )

        X = np.stack([arr[i : i + cfg.seq_len] for i in range(limit)])
        y = np.array(
            [tgt[i + cfg.seq_len + cfg.forecast_horizon - 1] for i in range(limit)],
            dtype=np.float32,
        )
        return X, y
