from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
import torch.nn as nn
from ml_models.config import (
    MAX_TRAIN_RECORDS,
    RISK_FACTOR_WEIGHTS,
    RISK_FACTORS,
    RISK_FEATURES,
    RISK_SEQ_LEN,
    risk_level,
)
from ml_models.core.artifacts import load_artifact, save_artifact
from ml_models.core.training import ModelTrainer, get_device, make_loader, set_seed
from ml_models.data.features import build_risk_features, overall_risk, risk_targets
from ml_models.networks.architectures import FinancialRiskLSTM
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def _risk_windows(features, targets, seq_len: int):
    arr = features.values.astype(np.float32)
    tgt = targets.values.astype(np.float32)
    limit = len(arr) - seq_len + 1
    X = np.stack([arr[i : i + seq_len] for i in range(limit)])
    y = tgt[seq_len - 1 :]
    return X, y


def _risk_step(model: nn.Module, xb: torch.Tensor, yb: torch.Tensor) -> torch.Tensor:
    out = model(xb)
    factors = torch.cat([out[name] for name in RISK_FACTORS], dim=1)
    weights = torch.tensor(RISK_FACTOR_WEIGHTS, device=xb.device, dtype=xb.dtype)
    overall_target = (yb * weights).sum(dim=1, keepdim=True)
    mse = nn.functional.mse_loss
    return mse(factors, yb) + mse(out["overall_risk"], overall_target)


def train_risk_model(
    asset_records: List[Any],
    out_dir: Path,
    params: Dict[str, Any],
    batch_size: int = 64,
    seed: int = 42,
) -> Dict[str, Any]:
    set_seed(seed)
    blocks_X: List[np.ndarray] = []
    blocks_y: List[np.ndarray] = []
    for records in asset_records:
        feats = build_risk_features(records, MAX_TRAIN_RECORDS)
        X, y = _risk_windows(feats, risk_targets(feats), RISK_SEQ_LEN)
        blocks_X.append(X)
        blocks_y.append(y)

    sizes = [len(x) for x in blocks_X]
    n_test_assets = max(1, len(blocks_X) // 5)
    train_blocks = list(range(len(blocks_X) - n_test_assets))
    test_blocks = list(range(len(blocks_X) - n_test_assets, len(blocks_X)))
    if not train_blocks:
        raise ValueError("At least two assets are required to train the risk model")

    def stack(idx, which):
        return np.concatenate([which[i] for i in idx])

    X_all = stack(train_blocks, blocks_X)
    y_all = stack(train_blocks, blocks_y)
    X_test = stack(test_blocks, blocks_X)
    y_test = stack(test_blocks, blocks_y)

    split = int(len(X_all) * 0.85)
    X_train, y_train = X_all[:split], y_all[:split]
    X_val, y_val = X_all[split:], y_all[split:]

    scaler = StandardScaler().fit(X_train.reshape(-1, X_train.shape[-1]))

    def scale(a: np.ndarray) -> np.ndarray:
        return scaler.transform(a.reshape(-1, a.shape[-1])).reshape(a.shape)

    model = FinancialRiskLSTM(
        input_size=len(RISK_FEATURES),
        hidden_size=params["hidden_size"],
        num_layers=params["num_layers"],
        dropout=params["dropout"],
    )
    trainer = ModelTrainer(model, learning_rate=params["lr"], step_fn=_risk_step)
    trainer.train(
        make_loader(scale(X_train), y_train, batch_size, True),
        make_loader(scale(X_val), y_val, batch_size),
        params["epochs"],
        params["patience"],
    )

    model.eval()
    with torch.no_grad():
        out = model(torch.from_numpy(scale(X_test)).float().to(trainer.device))
        pred = torch.cat([out[n] for n in RISK_FACTORS], dim=1).cpu().numpy()
    mae = np.mean(np.abs(pred - y_test), axis=0)
    baseline = np.mean(np.abs(y_test - y_train.mean(axis=0)), axis=0)
    metrics = {
        "test_mae_by_factor": dict(zip(RISK_FACTORS, mae.tolist())),
        "mean_baseline_mae_by_factor": dict(zip(RISK_FACTORS, baseline.tolist())),
        "test_mae": float(mae.mean()),
        "mean_baseline_mae": float(baseline.mean()),
        "held_out_assets": len(test_blocks),
        "test_sequences": int(len(y_test)),
    }
    logger.info("Risk metrics: %s", metrics)

    meta = {
        "model_type": "risk",
        "architecture": {
            "input_size": len(RISK_FEATURES),
            "hidden_size": params["hidden_size"],
            "num_layers": params["num_layers"],
            "dropout": params["dropout"],
        },
        "seq_len": RISK_SEQ_LEN,
        "features": list(RISK_FEATURES),
        "metrics": metrics,
        "training_sequences": int(sum(sizes)),
    }
    save_artifact(out_dir, meta, model.state_dict(), {"scaler": scaler})
    return meta


class RiskPredictor:
    model_type = "risk"

    def __init__(self, meta, model, scaler, device) -> None:
        self.meta = meta
        self.model = model
        self.scaler = scaler
        self.device = device

    @classmethod
    def load(cls, directory: Path) -> "RiskPredictor":
        meta, state, objects = load_artifact(directory)
        device = get_device()
        model = FinancialRiskLSTM(**meta["architecture"])
        model.load_state_dict(state)
        model.to(device).eval()
        return cls(meta, model, objects["scaler"], device)

    def predict(self, records: Any) -> Dict[str, Any]:
        feats = build_risk_features(records)
        seq_len = int(self.meta["seq_len"])
        window = feats.values[-seq_len:].astype(np.float32)
        scaled = self.scaler.transform(window).astype(np.float32)
        with torch.no_grad():
            out = self.model(torch.from_numpy(scaled[None]).to(self.device))
        factors = {n: float(out[n].item()) for n in RISK_FACTORS}
        overall = float(out["overall_risk"].item())
        rule_based = float(overall_risk(risk_targets(feats.iloc[-1:]).to_numpy())[0])
        top = max(factors, key=factors.get)
        return {
            "overall_risk": overall,
            "risk_level": risk_level(overall),
            "factors": factors,
            "factor_levels": {n: risk_level(v) for n, v in factors.items()},
            "primary_driver": top,
            "rule_based_overall": rule_based,
            "observations": int(len(feats)),
        }
