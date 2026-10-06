from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
import torch.nn as nn
from ml_models.config import MAX_TRAIN_RECORDS, TRANSACTION_FEATURES, VIOLATION_TYPES
from ml_models.core.artifacts import load_artifact, save_artifact
from ml_models.core.training import ModelTrainer, get_device, make_loader, set_seed
from ml_models.data.features import transaction_features, transaction_frame
from ml_models.data.synthetic import compliance_labels, transaction_records
from ml_models.networks.architectures import ComplianceViolationDetector
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def train_compliance_model(
    out_dir: Path,
    params: Dict[str, Any],
    records: Any = None,
    labels: Any = None,
    batch_size: int = 64,
    seed: int = 42,
) -> Dict[str, Any]:
    set_seed(seed)
    if records is None:
        records, _ = transaction_records(
            params["rows"], seed=seed, anomaly_fraction=0.08
        )
    frame = transaction_frame(records, MAX_TRAIN_RECORDS)
    y = (
        compliance_labels(frame)
        if labels is None
        else np.asarray(labels, dtype=np.float32)
    )
    X = transaction_features(frame)

    n = len(X)
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    X, y = X[order], y[order]
    n_test = max(1, int(n * 0.15))
    n_val = max(1, int(n * 0.15))
    X_test, y_test = X[:n_test], y[:n_test]
    X_val, y_val = X[n_test : n_test + n_val], y[n_test : n_test + n_val]
    X_train, y_train = X[n_test + n_val :], y[n_test + n_val :]

    scaler = StandardScaler().fit(X_train)
    pos = y_train.sum(axis=0)
    neg = len(y_train) - pos
    pos_weight = np.clip(neg / np.maximum(pos, 1.0), 1.0, 25.0).astype(np.float32)
    pw = torch.tensor(pos_weight)

    model = ComplianceViolationDetector(
        input_size=len(TRANSACTION_FEATURES),
        hidden_size=params["hidden_size"],
        dropout=params["dropout"],
    )

    def step(m: nn.Module, xb: torch.Tensor, yb: torch.Tensor) -> torch.Tensor:
        return nn.functional.binary_cross_entropy_with_logits(
            m.logits(xb), yb, pos_weight=pw.to(xb.device)
        )

    trainer = ModelTrainer(model, learning_rate=params["lr"], step_fn=step)
    trainer.train(
        make_loader(scaler.transform(X_train), y_train, batch_size, True),
        make_loader(scaler.transform(X_val), y_val, batch_size),
        params["epochs"],
        params["patience"],
    )

    model.eval()
    with torch.no_grad():
        probs = (
            torch.sigmoid(
                model.logits(
                    torch.from_numpy(scaler.transform(X_test))
                    .float()
                    .to(trainer.device)
                )
            )
            .cpu()
            .numpy()
        )
    auc: Dict[str, Any] = {}
    thresholds: Dict[str, float] = {}
    for i, name in enumerate(VIOLATION_TYPES):
        col = y_test[:, i]
        auc[name] = (
            float(roc_auc_score(col, probs[:, i])) if 0 < col.sum() < len(col) else None
        )
        thresholds[name] = 0.5
    metrics = {"test_auc_by_type": auc, "test_rows": int(n_test)}
    logger.info("Compliance metrics: %s", metrics)

    meta = {
        "model_type": "compliance",
        "architecture": {
            "input_size": len(TRANSACTION_FEATURES),
            "hidden_size": params["hidden_size"],
            "dropout": params["dropout"],
        },
        "features": list(TRANSACTION_FEATURES),
        "thresholds": thresholds,
        "metrics": metrics,
        "training_rows": int(len(X_train)),
    }
    save_artifact(out_dir, meta, model.state_dict(), {"scaler": scaler})
    return meta


class ComplianceChecker:
    model_type = "compliance"

    def __init__(self, meta, model, scaler, device) -> None:
        self.meta = meta
        self.model = model
        self.scaler = scaler
        self.device = device

    @classmethod
    def load(cls, directory: Path) -> "ComplianceChecker":
        meta, state, objects = load_artifact(directory)
        device = get_device()
        model = ComplianceViolationDetector(**meta["architecture"])
        model.load_state_dict(state)
        model.to(device).eval()
        return cls(meta, model, objects["scaler"], device)

    def predict(self, transactions: Any) -> List[Dict[str, Any]]:
        frame = transaction_frame(transactions)
        X = self.scaler.transform(transaction_features(frame))
        with torch.no_grad():
            probs = (
                torch.sigmoid(
                    self.model.logits(torch.from_numpy(X).float().to(self.device))
                )
                .cpu()
                .numpy()
            )
        thresholds = self.meta["thresholds"]
        results = []
        for row in probs:
            by_type = {n: float(row[i]) for i, n in enumerate(VIOLATION_TYPES)}
            flagged = [n for n, p in by_type.items() if p >= thresholds[n]]
            results.append(
                {
                    "probabilities": by_type,
                    "flagged": flagged,
                    "max_probability": float(row.max()),
                    "requires_review": bool(flagged),
                }
            )
        return results
