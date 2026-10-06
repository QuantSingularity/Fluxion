from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import torch
from ml_models.config import LIQUIDITY_HORIZON, LIQUIDITY_SEQ_LEN, MAX_TRAIN_RECORDS
from ml_models.core.artifacts import load_artifact, save_artifact
from ml_models.core.training import ModelTrainer, get_device, make_loader, set_seed
from ml_models.data.features import InputError, market_frame
from ml_models.data.pipeline import ALL_FEATURES, DataPipeline, PipelineConfig
from ml_models.forecasting.common import residual_bands, split_three
from ml_models.networks.architectures import LiquidityLSTM

logger = logging.getLogger(__name__)


def _liquidity_pipeline() -> DataPipeline:
    return DataPipeline(
        PipelineConfig(seq_len=LIQUIDITY_SEQ_LEN, forecast_horizon=LIQUIDITY_HORIZON)
    )


def _liquidity_windows(
    pipeline: DataPipeline, features: pd.DataFrame, log_liq: np.ndarray
):
    seq_len = pipeline.config.seq_len
    arr = features[ALL_FEATURES].values.astype(np.float32)
    n = len(arr)
    limit = n - seq_len - LIQUIDITY_HORIZON + 1
    if limit <= 0:
        raise ValueError("Not enough rows to build liquidity sequences")
    X = np.stack([arr[i : i + seq_len] for i in range(limit)])
    y = np.empty((limit, LIQUIDITY_HORIZON), dtype=np.float32)
    for i in range(limit):
        end = i + seq_len
        y[i] = log_liq[end : end + LIQUIDITY_HORIZON] - log_liq[end - 1]
    return X, y


def _aligned_log_liquidity(records: Any, features: pd.DataFrame) -> np.ndarray:
    base = market_frame(records, MAX_TRAIN_RECORDS)
    liq = base["liquidity"].reindex(features.index).ffill().bfill()
    return np.log(liq.clip(lower=1e-9).to_numpy(dtype=np.float64))


def train_liquidity_model(
    records: Any,
    out_dir: Path,
    params: Dict[str, Any],
    batch_size: int = 64,
    seed: int = 42,
) -> Dict[str, Any]:
    set_seed(seed)
    pipeline = _liquidity_pipeline()
    features = pipeline.transform(records, fit=True)
    log_liq = _aligned_log_liquidity(records, features)
    X, y = _liquidity_windows(pipeline, features, log_liq)

    n_train, n_val, n_test = split_three(len(X))
    sl_train = slice(0, n_train)
    sl_val = slice(n_train, n_train + n_val)
    sl_test = slice(n_train + n_val, None)

    y_scale = float(np.std(y[sl_train])) or 1.0
    model = LiquidityLSTM(
        input_size=len(ALL_FEATURES),
        hidden_size=params["hidden_size"],
        num_layers=params["num_layers"],
        dropout=params["dropout"],
        horizon=LIQUIDITY_HORIZON,
    )
    trainer = ModelTrainer(model, learning_rate=params["lr"])
    train_loader = make_loader(X[sl_train], y[sl_train] / y_scale, batch_size, True)
    val_loader = make_loader(X[sl_val], y[sl_val] / y_scale, batch_size)
    test_loader = make_loader(X[sl_test], y[sl_test] / y_scale, batch_size)
    trainer.train(train_loader, val_loader, params["epochs"], params["patience"])

    test_mse, preds, actual = trainer.evaluate(test_loader)
    preds = preds * y_scale
    actual = actual * y_scale
    baseline_mse = float(np.mean(actual**2))
    model_mse = float(np.mean((actual - preds) ** 2))
    bands = residual_bands(preds, actual)
    metrics = {
        "test_mse": model_mse,
        "zero_change_baseline_mse": baseline_mse,
        "skill_vs_baseline": 1.0 - model_mse / baseline_mse if baseline_mse else 0.0,
        "test_sequences": int(len(actual)),
    }
    logger.info("Liquidity metrics: %s", metrics)

    meta = {
        "model_type": "liquidity",
        "architecture": {
            "input_size": len(ALL_FEATURES),
            "hidden_size": params["hidden_size"],
            "num_layers": params["num_layers"],
            "dropout": params["dropout"],
            "horizon": LIQUIDITY_HORIZON,
        },
        "seq_len": LIQUIDITY_SEQ_LEN,
        "horizon": LIQUIDITY_HORIZON,
        "y_scale": y_scale,
        "bands": bands,
        "metrics": metrics,
        "training_rows": int(len(features)),
    }
    save_artifact(out_dir, meta, model.state_dict(), {"pipeline": pipeline})
    return meta


class LiquidityForecaster:
    model_type = "liquidity"

    def __init__(self, meta, model, pipeline, device) -> None:
        self.meta = meta
        self.model = model
        self.pipeline = pipeline
        self.device = device

    @classmethod
    def load(cls, directory: Path) -> "LiquidityForecaster":
        meta, state, objects = load_artifact(directory)
        device = get_device()
        model = LiquidityLSTM(**meta["architecture"])
        model.load_state_dict(state)
        model.to(device).eval()
        return cls(meta, model, objects["pipeline"], device)

    @property
    def min_records(self) -> int:
        return self.pipeline.config.min_rows_after_clean

    def predict(self, records: Any, horizon: int) -> Dict[str, Any]:
        max_h = int(self.meta["horizon"])
        if horizon < 1 or horizon > max_h:
            raise InputError(f"horizon must be between 1 and {max_h}")
        try:
            features = self.pipeline.transform(records, fit=False)
        except ValueError as exc:
            raise InputError(str(exc)) from exc
        window = self.pipeline.last_window(features)
        with torch.no_grad():
            out = self.model(torch.from_numpy(window).to(self.device))
        change = out.cpu().numpy()[0] * float(self.meta["y_scale"])
        last_liq = float(market_frame(records)["liquidity"].iloc[-1])
        lower = np.asarray(self.meta["bands"]["lower"])
        upper = np.asarray(self.meta["bands"]["upper"])
        idx = slice(0, horizon)
        point = last_liq * np.exp(change[idx])
        low = last_liq * np.exp(change[idx] + lower[idx])
        high = last_liq * np.exp(change[idx] + upper[idx])
        return {
            "current_liquidity": last_liq,
            "horizon": horizon,
            "predicted_liquidity": point.tolist(),
            "lower_bound": low.tolist(),
            "upper_bound": high.tolist(),
            "predicted_change_pct": ((point / last_liq - 1.0) * 100).tolist(),
            "confidence_level": 0.90,
        }
