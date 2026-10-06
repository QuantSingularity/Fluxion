from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import torch
from ml_models.config import (
    MAX_RECORDS,
    MAX_TRAIN_RECORDS,
    SUPPLY_CHAIN_FEATURES,
    SUPPLY_CHAIN_HORIZON,
    SUPPLY_CHAIN_SEQ_LEN,
    SUPPLY_CHAIN_TARGET,
)
from ml_models.core.artifacts import load_artifact, save_artifact
from ml_models.core.training import ModelTrainer, get_device, make_loader, set_seed
from ml_models.data.features import InputError, as_frame
from ml_models.forecasting.common import residual_bands, split_three
from ml_models.networks.architectures import SupplyChainForecaster
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def _supply_chain_matrix(records: Any, limit: int = MAX_RECORDS) -> pd.DataFrame:
    df = as_frame(records, SUPPLY_CHAIN_FEATURES, limit)
    frame = df[list(SUPPLY_CHAIN_FEATURES)].apply(pd.to_numeric, errors="coerce")
    frame = frame.replace([np.inf, -np.inf], np.nan).ffill(limit=3).bfill(limit=3)
    if frame.isna().any().any():
        raise InputError("Supply chain records contain missing or invalid values")
    return frame.reset_index(drop=True)


def train_supply_chain_model(
    records: Any,
    out_dir: Path,
    params: Dict[str, Any],
    batch_size: int = 64,
    seed: int = 42,
) -> Dict[str, Any]:
    set_seed(seed)
    frame = _supply_chain_matrix(records, MAX_TRAIN_RECORDS)
    n_rows = len(frame)
    seq_len, horizon = SUPPLY_CHAIN_SEQ_LEN, SUPPLY_CHAIN_HORIZON
    limit = n_rows - seq_len - horizon + 1
    if limit < 20:
        raise ValueError("Not enough supply chain rows to train")

    n_train, n_val, n_test = split_three(limit)
    fit_rows = n_train + seq_len
    scaler = StandardScaler().fit(frame.iloc[:fit_rows])
    scaled = scaler.transform(frame).astype(np.float32)
    target_idx = list(SUPPLY_CHAIN_FEATURES).index(SUPPLY_CHAIN_TARGET)

    X = np.stack([scaled[i : i + seq_len] for i in range(limit)])
    y = np.stack(
        [scaled[i + seq_len : i + seq_len + horizon, target_idx] for i in range(limit)]
    )

    sl_train = slice(0, n_train)
    sl_val = slice(n_train, n_train + n_val)
    sl_test = slice(n_train + n_val, None)

    model = SupplyChainForecaster(
        input_size=len(SUPPLY_CHAIN_FEATURES),
        hidden_size=params["hidden_size"],
        num_layers=params["num_layers"],
        dropout=params["dropout"],
        horizon=horizon,
    )
    trainer = ModelTrainer(model, learning_rate=params["lr"])
    trainer.train(
        make_loader(X[sl_train], y[sl_train], batch_size, True),
        make_loader(X[sl_val], y[sl_val], batch_size),
        params["epochs"],
        params["patience"],
    )
    _, preds, actual = trainer.evaluate(make_loader(X[sl_test], y[sl_test], batch_size))

    t_mean = float(scaler.mean_[target_idx])
    t_std = float(scaler.scale_[target_idx])
    preds_u = preds * t_std + t_mean
    actual_u = actual * t_std + t_mean
    naive = np.repeat(X[sl_test][:, -1, target_idx][:, None], horizon, axis=1)
    naive_u = naive * t_std + t_mean
    model_mae = float(np.mean(np.abs(actual_u - preds_u)))
    naive_mae = float(np.mean(np.abs(actual_u - naive_u)))
    metrics = {
        "test_mae": model_mae,
        "last_value_baseline_mae": naive_mae,
        "skill_vs_baseline": 1.0 - model_mae / naive_mae if naive_mae else 0.0,
        "test_sequences": int(len(actual_u)),
    }
    logger.info("Supply chain metrics: %s", metrics)

    meta = {
        "model_type": "supply_chain",
        "architecture": {
            "input_size": len(SUPPLY_CHAIN_FEATURES),
            "hidden_size": params["hidden_size"],
            "num_layers": params["num_layers"],
            "dropout": params["dropout"],
            "horizon": horizon,
        },
        "seq_len": seq_len,
        "horizon": horizon,
        "features": list(SUPPLY_CHAIN_FEATURES),
        "target": SUPPLY_CHAIN_TARGET,
        "target_mean": t_mean,
        "target_std": t_std,
        "bands": residual_bands(preds_u, actual_u),
        "metrics": metrics,
        "training_rows": int(n_rows),
    }
    save_artifact(out_dir, meta, model.state_dict(), {"scaler": scaler})
    return meta


class SupplyChainPredictor:
    model_type = "supply_chain"

    def __init__(self, meta, model, scaler, device) -> None:
        self.meta = meta
        self.model = model
        self.scaler = scaler
        self.device = device

    @classmethod
    def load(cls, directory: Path) -> "SupplyChainPredictor":
        meta, state, objects = load_artifact(directory)
        device = get_device()
        model = SupplyChainForecaster(**meta["architecture"])
        model.load_state_dict(state)
        model.to(device).eval()
        return cls(meta, model, objects["scaler"], device)

    @property
    def min_records(self) -> int:
        return int(self.meta["seq_len"])

    def predict(self, records: Any, horizon: int) -> Dict[str, Any]:
        max_h = int(self.meta["horizon"])
        if horizon < 1 or horizon > max_h:
            raise InputError(f"horizon must be between 1 and {max_h}")
        frame = _supply_chain_matrix(records)
        seq_len = int(self.meta["seq_len"])
        if len(frame) < seq_len:
            raise InputError(f"Need at least {seq_len} records, got {len(frame)}")
        scaled = self.scaler.transform(frame.iloc[-seq_len:]).astype(np.float32)
        with torch.no_grad():
            out = self.model(torch.from_numpy(scaled[None]).to(self.device))
        values = (
            out.cpu().numpy()[0] * self.meta["target_std"] + self.meta["target_mean"]
        )
        lower = np.asarray(self.meta["bands"]["lower"])
        upper = np.asarray(self.meta["bands"]["upper"])
        idx = slice(0, horizon)
        return {
            "target": self.meta["target"],
            "horizon": horizon,
            "current_value": float(frame[self.meta["target"]].iloc[-1]),
            "predictions": values[idx].tolist(),
            "lower_bound": (values[idx] + lower[idx]).tolist(),
            "upper_bound": (values[idx] + upper[idx]).tolist(),
            "confidence_level": 0.90,
        }
