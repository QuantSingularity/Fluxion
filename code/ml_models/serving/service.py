from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from ml_models.anomaly.detector import AnomalyDetector, train_anomaly_model
from ml_models.config import MODEL_TYPES, PROFILES
from ml_models.core.registry import ModelVersionManager
from ml_models.data.features import InputError
from ml_models.data.synthetic import market_records, supply_chain_frame
from ml_models.forecasting.liquidity import LiquidityForecaster, train_liquidity_model
from ml_models.forecasting.supply_chain import (
    SupplyChainPredictor,
    train_supply_chain_model,
)
from ml_models.risk.compliance import ComplianceChecker, train_compliance_model
from ml_models.risk.risk_model import RiskPredictor, train_risk_model

logger = logging.getLogger(__name__)

LOADERS: Dict[str, Any] = {
    "liquidity": LiquidityForecaster,
    "supply_chain": SupplyChainPredictor,
    "risk": RiskPredictor,
    "anomaly": AnomalyDetector,
    "compliance": ComplianceChecker,
}


class ModelNotReady(RuntimeError):
    pass


def _risk_assets(rows: int, seed: int) -> List[Any]:
    assets = []
    for i in range(10):
        assets.append(
            market_records(
                rows,
                seed=seed + i,
                vol_scale=0.5 + 0.25 * i,
                collateral_mean=0.9 + 0.12 * i,
                verified=0.0 if i % 4 == 3 else 1.0,
                base_price=50.0 * (i + 1),
                base_liquidity=2e5 * (i + 1),
                base_volume=8e3 * (i + 1),
            )
        )
    return assets


def _split_assets(records: Any, min_rows: int) -> List[Any]:
    if isinstance(records, dict):
        return list(records.values())
    chunks = max(2, min(10, len(records) // max(min_rows, 1)))
    size = len(records) // chunks
    return [records[i * size : (i + 1) * size] for i in range(chunks)]


class ModelService:
    def __init__(self, model_dir: Any) -> None:
        self.model_dir = Path(model_dir)
        self.manager = ModelVersionManager(self.model_dir)
        self._cache: Dict[Any, Any] = {}
        self._cache_lock = threading.RLock()
        self._train_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._state: Dict[str, Any] = {"running": False, "last": None, "error": None}
        self._since_flush = 0

    def ready(self) -> bool:
        return all(self.manager.get_active_version(t) for t in MODEL_TYPES)

    def missing(self) -> List[str]:
        return [t for t in MODEL_TYPES if not self.manager.get_active_version(t)]

    def training_state(self) -> Dict[str, Any]:
        with self._state_lock:
            return dict(self._state)

    def status(self) -> Dict[str, Any]:
        models = {}
        for t in MODEL_TYPES:
            version = self.manager.get_active_version(t)
            entry: Dict[str, Any] = {"active_version": version}
            if version:
                info = self.manager.models[t][version]
                entry["registered_at"] = info["registered_at"]
                entry["metrics"] = info["metadata"].get("metrics", {})
                entry["data_source"] = info["metadata"].get("data_source")
                entry["usage"] = self.manager.get_model_metrics(info["model_id"])
            models[t] = entry
        return {
            "ready": self.ready(),
            "missing": self.missing(),
            "models": models,
            "training": self.training_state(),
        }

    def _load(self, model_type: str, version: str) -> Any:
        key = (model_type, version)
        with self._cache_lock:
            if key not in self._cache:
                path = self.manager.get_model_path(model_type, version)
                self._cache[key] = LOADERS[model_type].load(path)
            return self._cache[key]

    def _invoke(
        self,
        model_type: str,
        call: Callable[[Any], Any],
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        version = self.manager.select_model_for_request(model_type, request_id)
        if version is None:
            raise ModelNotReady(f"No active {model_type} model")
        model_id = f"{model_type}_v{version}"
        started = time.perf_counter()
        failed = True
        try:
            predictor = self._load(model_type, version)
            result = call(predictor)
            failed = False
        except InputError:
            failed = False
            raise
        finally:
            self.manager.record_inference(
                model_id, time.perf_counter() - started, error=failed
            )
            self._since_flush += 1
            if self._since_flush >= 100:
                self._since_flush = 0
                self.manager.flush()
        return {"model_version": model_id, "result": result}

    def forecast_liquidity(self, records: Any, horizon: int, request_id=None):
        return self._invoke(
            "liquidity", lambda p: p.predict(records, horizon), request_id
        )

    def forecast_supply_chain(self, records: Any, horizon: int, request_id=None):
        return self._invoke(
            "supply_chain", lambda p: p.predict(records, horizon), request_id
        )

    def assess_risk(self, records: Any, request_id=None):
        return self._invoke("risk", lambda p: p.predict(records), request_id)

    def detect_anomalies(self, transactions: Any, request_id=None):
        return self._invoke("anomaly", lambda p: p.predict(transactions), request_id)

    def check_compliance(self, transactions: Any, request_id=None):
        return self._invoke("compliance", lambda p: p.predict(transactions), request_id)

    def screen_transactions(self, transactions: Any, request_id=None) -> Dict[str, Any]:
        anomalies = self.detect_anomalies(transactions, request_id)
        compliance = self.check_compliance(transactions, request_id)
        combined = []
        for a, c in zip(anomalies["result"], compliance["result"]):
            flags = list(c["flagged"])
            if a["is_anomaly"]:
                flags.append("anomalous_pattern")
            combined.append(
                {
                    "anomaly": a,
                    "compliance": c,
                    "flags": flags,
                    "requires_review": bool(flags),
                }
            )
        return {
            "model_versions": {
                "anomaly": anomalies["model_version"],
                "compliance": compliance["model_version"],
            },
            "result": combined,
        }

    def train(
        self,
        types: Optional[Iterable[str]] = None,
        profile: str = "full",
        datasets: Optional[Dict[str, Any]] = None,
        seed: int = 42,
    ) -> Dict[str, Any]:
        if profile not in PROFILES:
            raise ValueError(f"Unknown profile '{profile}'")
        selected = list(types) if types else list(MODEL_TYPES)
        unknown = [t for t in selected if t not in MODEL_TYPES]
        if unknown:
            raise ValueError(f"Unknown model types: {', '.join(unknown)}")
        if not self._train_lock.acquire(blocking=False):
            raise RuntimeError("Training already in progress")
        with self._state_lock:
            self._state = {"running": True, "last": None, "error": None}
        summary: Dict[str, Any] = {}
        try:
            cfg = PROFILES[profile]
            datasets = datasets or {}
            for model_type in selected:
                summary[model_type] = self._train_one(
                    model_type, cfg, datasets.get(model_type), seed, cfg["batch_size"]
                )
            with self._state_lock:
                self._state = {"running": False, "last": summary, "error": None}
            return summary
        except Exception as exc:
            logger.exception("Training failed")
            with self._state_lock:
                self._state = {"running": False, "last": summary, "error": str(exc)}
            raise
        finally:
            self._train_lock.release()

    def _train_one(
        self, model_type: str, cfg: Dict[str, Any], data: Any, seed: int, batch: int
    ) -> Dict[str, Any]:
        params = cfg[model_type]
        version = self.manager.next_version(model_type)
        out_dir = self.model_dir / model_type / f"v{version}"
        source = "supplied" if data is not None else "synthetic"
        started = time.time()
        if model_type == "liquidity":
            records = data if data is not None else market_records(params["rows"], seed)
            meta = train_liquidity_model(records, out_dir, params, batch, seed)
        elif model_type == "supply_chain":
            records = (
                data
                if data is not None
                else supply_chain_frame(params["rows"], seed).to_dict("records")
            )
            meta = train_supply_chain_model(records, out_dir, params, batch, seed)
        elif model_type == "risk":
            if data is not None:
                assets = _split_assets(data, 80)
            else:
                assets = _risk_assets(max(params["rows"] // 10, 120), seed)
            meta = train_risk_model(assets, out_dir, params, batch, seed)
        elif model_type == "anomaly":
            records, labels = data if isinstance(data, tuple) else (data, None)
            meta = train_anomaly_model(out_dir, params, records, labels, batch, seed)
        else:
            records, labels = data if isinstance(data, tuple) else (data, None)
            meta = train_compliance_model(out_dir, params, records, labels, batch, seed)
        model_id = self.manager.register_model(
            model_type,
            out_dir,
            version,
            {
                "metrics": meta.get("metrics", {}),
                "data_source": source,
                "trained_at_epoch": started,
                "train_seconds": round(time.time() - started, 2),
            },
        )
        self.manager.activate_model(model_type, version)
        with self._cache_lock:
            self._cache = {k: v for k, v in self._cache.items() if k[0] != model_type}
        logger.info("Trained and activated %s", model_id)
        return {"model_id": model_id, "data_source": source, "metrics": meta["metrics"]}

    def bootstrap(self, profile: str = "full") -> Dict[str, Any]:
        missing = self.missing()
        if not missing:
            return {}
        logger.info("Bootstrapping missing models: %s", ", ".join(missing))
        return self.train(missing, profile)

    def shutdown(self) -> None:
        self.manager.flush()
