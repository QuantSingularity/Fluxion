from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from ml_models.config import MAX_TRAIN_RECORDS, TRANSACTION_FEATURES
from ml_models.core.artifacts import load_artifact, save_artifact
from ml_models.core.training import ModelTrainer, get_device, make_loader, set_seed
from ml_models.data.features import transaction_features, transaction_frame
from ml_models.data.synthetic import transaction_records
from ml_models.networks.architectures import AnomalyAutoencoder
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def _recon_errors(
    model: AnomalyAutoencoder, X: np.ndarray, device: torch.device
) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        xb = torch.from_numpy(X).float().to(device)
        recon, _ = model(xb)
        return ((xb - recon) ** 2).mean(dim=1).cpu().numpy()


def _cdf(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    ref = np.sort(reference)
    return np.searchsorted(ref, values, side="right") / max(len(ref), 1)


def train_anomaly_model(
    out_dir: Path,
    params: Dict[str, Any],
    records: Any = None,
    labels: Any = None,
    batch_size: int = 64,
    seed: int = 42,
) -> Dict[str, Any]:
    set_seed(seed)
    if records is None:
        records, labels = transaction_records(
            params["rows"], seed=seed, anomaly_fraction=params["contamination"]
        )
    frame = transaction_frame(records, MAX_TRAIN_RECORDS)
    X = transaction_features(frame)
    y = None if labels is None else np.asarray(labels).astype(int)

    n = len(X)
    order = np.random.default_rng(seed).permutation(n)
    X = X[order]
    if y is not None:
        y = y[order]
    n_test = max(1, int(n * 0.2))
    n_val = max(1, int(n * 0.15))
    X_test = X[:n_test]
    y_test = None if y is None else y[:n_test]
    X_val = X[n_test : n_test + n_val]
    X_train = X[n_test + n_val :]
    y_train = None if y is None else y[n_test + n_val :]

    fit_mask = np.ones(len(X_train), dtype=bool) if y_train is None else (y_train == 0)
    scaler = StandardScaler().fit(X_train[fit_mask])
    Xs_train = scaler.transform(X_train[fit_mask]).astype(np.float32)
    Xs_val = scaler.transform(X_val).astype(np.float32)

    model = AnomalyAutoencoder(
        input_size=len(TRANSACTION_FEATURES),
        encoding_dim=params["encoding_dim"],
        dropout=params["dropout"],
    )

    def step(m, xb, yb):
        recon, _ = m(xb)
        return torch.nn.functional.mse_loss(recon, xb)

    trainer = ModelTrainer(model, learning_rate=params["lr"], step_fn=step)
    trainer.train(
        make_loader(Xs_train, Xs_train, batch_size, True),
        make_loader(Xs_val, Xs_val, batch_size),
        params["epochs"],
        params["patience"],
    )

    forest = IsolationForest(
        n_estimators=200,
        contamination=params["contamination"],
        random_state=seed,
        n_jobs=1,
    ).fit(Xs_train)

    ref_ae = _recon_errors(model, Xs_train, trainer.device)
    ref_if = -forest.score_samples(Xs_train)
    combined_ref = 0.5 * _cdf(ref_ae, ref_ae) + 0.5 * _cdf(ref_if, ref_if)
    threshold = float(np.quantile(combined_ref, 1.0 - params["contamination"]))

    Xs_test = scaler.transform(X_test).astype(np.float32)
    t_ae = _recon_errors(model, Xs_test, trainer.device)
    t_if = -forest.score_samples(Xs_test)
    t_score = 0.5 * _cdf(ref_ae, t_ae) + 0.5 * _cdf(ref_if, t_if)
    flagged = t_score >= threshold

    metrics: Dict[str, Any] = {
        "flag_rate_test": float(flagged.mean()),
        "test_rows": int(len(Xs_test)),
        "threshold": threshold,
    }
    if y_test is not None and 0 < y_test.sum() < len(y_test):
        metrics["test_auc"] = float(roc_auc_score(y_test, t_score))
        metrics["test_precision"] = float(
            (flagged & (y_test == 1)).sum() / max(flagged.sum(), 1)
        )
        metrics["test_recall"] = float(
            (flagged & (y_test == 1)).sum() / max((y_test == 1).sum(), 1)
        )
    logger.info("Anomaly metrics: %s", metrics)

    meta = {
        "model_type": "anomaly",
        "architecture": {
            "input_size": len(TRANSACTION_FEATURES),
            "encoding_dim": params["encoding_dim"],
            "dropout": params["dropout"],
        },
        "features": list(TRANSACTION_FEATURES),
        "threshold": threshold,
        "contamination": params["contamination"],
        "metrics": metrics,
        "training_rows": int(len(Xs_train)),
    }
    save_artifact(
        out_dir,
        meta,
        model.state_dict(),
        {
            "scaler": scaler,
            "forest": forest,
            "ref_ae": np.sort(ref_ae),
            "ref_if": np.sort(ref_if),
        },
    )
    return meta


class AnomalyDetector:
    model_type = "anomaly"

    def __init__(self, meta, model, objects, device) -> None:
        self.meta = meta
        self.model = model
        self.scaler = objects["scaler"]
        self.forest = objects["forest"]
        self.ref_ae = np.asarray(objects["ref_ae"])
        self.ref_if = np.asarray(objects["ref_if"])
        self.device = device

    @classmethod
    def load(cls, directory: Path) -> "AnomalyDetector":
        meta, state, objects = load_artifact(directory)
        device = get_device()
        model = AnomalyAutoencoder(**meta["architecture"])
        model.load_state_dict(state)
        model.to(device).eval()
        return cls(meta, model, objects, device)

    def score(self, transactions: Any) -> np.ndarray:
        frame = transaction_frame(transactions)
        Xs = self.scaler.transform(transaction_features(frame)).astype(np.float32)
        ae = _recon_errors(self.model, Xs, self.device)
        iso = -self.forest.score_samples(Xs)
        return 0.5 * _cdf(self.ref_ae, ae) + 0.5 * _cdf(self.ref_if, iso)

    def predict(self, transactions: Any) -> List[Dict[str, Any]]:
        scores = self.score(transactions)
        threshold = float(self.meta["threshold"])
        return [
            {
                "anomaly_score": float(s),
                "is_anomaly": bool(s >= threshold),
                "threshold": threshold,
            }
            for s in scores
        ]
