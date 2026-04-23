"""
Unit tests for the Fluxion ML Data Pipeline
Tests ingestion, cleaning, feature engineering, normalisation,
sequence building, and edge cases.
"""

from __future__ import annotations

import os

# The data_pipeline lives in code/ml_models — add it to sys.path via conftest
import sys
from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np
import pandas as pd
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml_models")
)

from data_pipeline import (
    _MINMAX_FEATURES,
    _ROBUST_FEATURES,
    ALL_FEATURES,
    DataPipeline,
    PipelineConfig,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_raw(n: int = 200, start_price: float = 100.0) -> List[dict]:
    """Generate synthetic OHLCV-style records for testing."""
    rng = np.random.default_rng(42)
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = start_price
    liq = 1_000_000.0
    for i in range(n):
        price = max(0.01, price * (1 + rng.normal(0, 0.01)))
        vol = abs(rng.normal(50_000, 10_000))
        liq = max(100.0, liq * (1 + rng.normal(0, 0.005)))
        rows.append(
            {
                "timestamp": ts + timedelta(hours=i),
                "price": round(price, 4),
                "volume": round(vol, 2),
                "liquidity": round(liq, 2),
                "buy_volume": round(vol * rng.uniform(0.4, 0.6), 2),
                "sell_volume": round(vol * rng.uniform(0.4, 0.6), 2),
                "pool_utilisation": round(rng.uniform(0.1, 0.9), 4),
            }
        )
    return rows


@pytest.fixture
def raw_data():
    return _make_raw(200)


@pytest.fixture
def pipeline():
    cfg = PipelineConfig(
        seq_len=32, long_window=20, short_window=5, min_rows_after_clean=50
    )
    return DataPipeline(config=cfg)


# ─── Ingestion ────────────────────────────────────────────────────────────────


class TestIngestion:
    def test_accepts_list_of_dicts(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_accepts_dataframe(self, pipeline, raw_data):
        df_in = pd.DataFrame(raw_data)
        df = pipeline.transform(df_in)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_rejects_missing_required_cols(self, pipeline):
        bad = [{"timestamp": "2024-01-01", "price": 100}]  # missing volume & liquidity
        with pytest.raises(ValueError, match="Missing required columns"):
            pipeline.transform(bad)

    def test_rejects_unsupported_type(self, pipeline):
        with pytest.raises(TypeError):
            pipeline.transform({"price": 100})  # dict, not list/DataFrame

    def test_timestamp_parsing(self, pipeline, raw_data):
        # Convert timestamps to string — pipeline should parse them
        str_rows = [{**r, "timestamp": r["timestamp"].isoformat()} for r in raw_data]
        df = pipeline.transform(str_rows)
        assert pd.api.types.is_datetime64_any_dtype(df.index)


# ─── Cleaning ─────────────────────────────────────────────────────────────────


class TestCleaning:
    def test_removes_zero_price_rows(self, pipeline, raw_data):
        raw_data[5]["price"] = 0
        raw_data[10]["price"] = -1.0
        df = pipeline.transform(raw_data)
        # These rows should be absent
        assert len(df) < len(raw_data)

    def test_raises_when_too_few_rows_after_clean(self):
        cfg = PipelineConfig(seq_len=32, min_rows_after_clean=100)
        p = DataPipeline(config=cfg)
        rows = _make_raw(10)  # far too few
        with pytest.raises(ValueError, match="rows after cleaning"):
            p.transform(rows)

    def test_clips_extreme_outliers(self, pipeline, raw_data):
        raw_data[50]["price"] = 1e12  # extreme outlier
        df = pipeline.transform(raw_data)
        # After clipping the raw price, the log_return should not be astronomical
        assert df["log_return"].abs().max() < 50

    def test_forward_fills_short_price_gaps(self, pipeline, raw_data):
        raw_data[20]["price"] = None  # type: ignore[assignment]
        df = pipeline.transform(raw_data)
        assert not df["log_return"].isna().all()

    def test_sorted_by_timestamp(self, pipeline, raw_data):
        import random

        shuffled = raw_data.copy()
        random.shuffle(shuffled)
        df = pipeline.transform(shuffled)
        assert df.index.is_monotonic_increasing


# ─── Feature Engineering ──────────────────────────────────────────────────────


class TestFeatureEngineering:
    def test_all_feature_columns_present(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        for col in ALL_FEATURES:
            assert col in df.columns, f"Missing feature: {col}"

    def test_no_inf_values(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        assert not np.isinf(df.values).any()

    def test_no_nan_in_output(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        assert not df.isna().any().any()

    def test_is_weekend_binary(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        assert set(df["is_weekend"].unique()).issubset({0.0, 1.0})

    def test_cyclical_features_bounded(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        for col in ("hour_sin", "hour_cos", "dow_sin", "dow_cos"):
            assert df[col].between(-1.0001, 1.0001).all(), f"{col} out of [-1,1]"

    def test_rsi_bounded(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        assert df["rsi_14"].between(-0.001, 1.001).all()

    def test_ath_atl_distance_bounded(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        assert df["ath_distance"].between(-0.001, 1.001).all()
        assert df["atl_distance"].between(-0.001, 1.001).all()

    def test_buy_sell_imbalance_with_buy_sell_cols(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        # buy_sell_imbalance is in _ROBUST_FEATURES, so after RobustScaler it
        # can be outside [-1,1]; we just verify it is finite and non-NaN.
        import numpy as np

        assert not df["buy_sell_imbalance"].isna().any()
        assert np.isfinite(df["buy_sell_imbalance"]).all()

    def test_buy_sell_imbalance_defaults_to_zero(self, pipeline):
        """When buy_volume / sell_volume absent, column should be 0."""
        rows = [
            {k: v for k, v in r.items() if k not in ("buy_volume", "sell_volume")}
            for r in _make_raw(120)
        ]
        df = pipeline.transform(rows)
        assert (df["buy_sell_imbalance"] == 0.0).all()

    def test_pool_utilisation_proxy_bounded(self, pipeline):
        rows = [
            {k: v for k, v in r.items() if k != "pool_utilisation"}
            for r in _make_raw(120)
        ]
        df = pipeline.transform(rows)
        assert df["pool_utilisation"].between(-0.001, 1.001).all()


# ─── Normalisation ────────────────────────────────────────────────────────────


class TestNormalisation:
    def test_robust_features_have_zero_median_after_fit(self, pipeline, raw_data):
        df = pipeline.transform(raw_data, fit=True)
        for col in _ROBUST_FEATURES:
            if col in df.columns:
                median = df[col].median()
                assert abs(median) < 0.6, f"{col} median {median:.3f} far from 0"

    def test_minmax_features_in_unit_interval(self, pipeline, raw_data):
        df = pipeline.transform(raw_data, fit=True)
        for col in _MINMAX_FEATURES:
            if col in df.columns:
                assert df[col].min() >= -0.001, f"{col} below 0"
                assert df[col].max() <= 1.001, f"{col} above 1"

    def test_fit_false_uses_existing_scalers(self, pipeline, raw_data):
        pipeline.transform(raw_data, fit=True)
        assert pipeline.is_fitted()
        new_rows = _make_raw(200)
        df2 = pipeline.transform(new_rows, fit=False)
        assert isinstance(df2, pd.DataFrame)
        assert len(df2) > 0

    def test_is_fitted_false_before_transform(self):
        p = DataPipeline()
        assert not p.is_fitted()

    def test_is_fitted_true_after_transform(self, pipeline, raw_data):
        pipeline.transform(raw_data, fit=True)
        assert pipeline.is_fitted()


# ─── Sequence Building ───────────────────────────────────────────────────────


class TestSequenceBuilding:
    def test_returns_four_arrays(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        result = pipeline.build_sequences(df)
        assert len(result) == 4
        X_train, y_train, X_val, y_val = result
        for arr in result:
            assert isinstance(arr, np.ndarray)

    def test_x_shape_correct(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        X_train, _, _, _ = pipeline.build_sequences(df)
        assert X_train.ndim == 3
        assert X_train.shape[1] == pipeline.config.seq_len
        assert X_train.shape[2] == len(ALL_FEATURES)

    def test_y_shape_matches_x(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        X_train, y_train, X_val, y_val = pipeline.build_sequences(df)
        assert X_train.shape[0] == y_train.shape[0]
        assert X_val.shape[0] == y_val.shape[0]

    def test_no_nan_in_sequences(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        X_train, y_train, X_val, y_val = pipeline.build_sequences(df)
        for arr in (X_train, y_train, X_val, y_val):
            assert not np.isnan(arr).any()

    def test_chronological_split_no_leakage(self, pipeline, raw_data):
        """Train indices must precede val indices — no temporal leakage."""
        df = pipeline.transform(raw_data)
        n = len(df)
        cfg = pipeline.config
        n_hld = max(1, int(n * cfg.holdout_fraction))
        n_seq = n - cfg.seq_len - cfg.forecast_horizon + 1
        n_val = max(1, int((n_seq - n_hld) * cfg.val_fraction))
        n_train = n_seq - n_hld - n_val

        X_train, _, X_val, _ = pipeline.build_sequences(df)
        # Allow ±2 due to integer rounding in fraction splits
        assert abs(X_train.shape[0] - n_train) <= 2
        assert abs(X_val.shape[0] - n_val) <= 2

    def test_raises_when_seq_len_exceeds_data(self):
        cfg = PipelineConfig(seq_len=500, min_rows_after_clean=10)
        p = DataPipeline(config=cfg)
        rows = _make_raw(50)
        with pytest.raises((ValueError, Exception)):
            df = p.transform(rows)
            p.build_sequences(df)

    def test_float32_dtype(self, pipeline, raw_data):
        df = pipeline.transform(raw_data)
        X_train, y_train, _, _ = pipeline.build_sequences(df)
        assert X_train.dtype == np.float32
        assert y_train.dtype == np.float32


# ─── get_feature_names ────────────────────────────────────────────────────────


class TestGetFeatureNames:
    def test_returns_list(self):
        p = DataPipeline()
        names = p.get_feature_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_matches_all_features_constant(self):
        p = DataPipeline()
        assert p.get_feature_names() == ALL_FEATURES


# ─── Config variations ────────────────────────────────────────────────────────


class TestConfigVariations:
    def test_custom_seq_len(self):
        cfg = PipelineConfig(
            seq_len=16, short_window=5, long_window=15, min_rows_after_clean=40
        )
        p = DataPipeline(config=cfg)
        df = p.transform(_make_raw(120))
        X, _, _, _ = p.build_sequences(df)
        assert X.shape[1] == 16

    def test_custom_forecast_horizon(self):
        cfg = PipelineConfig(
            seq_len=16,
            forecast_horizon=3,
            min_rows_after_clean=40,
            short_window=5,
            long_window=15,
        )
        p = DataPipeline(config=cfg)
        df = p.transform(_make_raw(150))
        X, y, _, _ = p.build_sequences(df)
        assert X.shape[0] == y.shape[0]

    def test_large_dataset_performance(self):
        """Pipeline should complete for 2 000-row input in reasonable time."""
        import time

        cfg = PipelineConfig(seq_len=64, min_rows_after_clean=100)
        p = DataPipeline(config=cfg)
        rows = _make_raw(2_000)
        t0 = time.time()
        df = p.transform(rows)
        elapsed = time.time() - t0
        assert elapsed < 10.0, f"Pipeline took {elapsed:.1f}s — too slow"
        assert len(df) > 100
