from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _empty_metrics() -> Dict[str, Any]:
    return {
        "inference_count": 0,
        "avg_inference_time": 0.0,
        "error_count": 0,
        "performance_metrics": {},
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelVersionManager:
    def __init__(self, model_dir: Any = "models") -> None:
        self.model_dir = Path(model_dir)
        self.models: Dict[str, Dict[str, Any]] = {}
        self.active_models: Dict[str, str] = {}
        self.model_metrics: Dict[str, Dict[str, Any]] = {}
        self.ab_test_config: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.reload()

    @property
    def registry_path(self) -> Path:
        return self.model_dir / "model_registry.json"

    def reload(self) -> None:
        with self._lock:
            if not self.registry_path.is_file():
                return
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("Could not read model registry: %s", exc)
                return
            self.models = data.get("models", {})
            self.active_models = data.get("active_models", {})
            self.model_metrics = data.get("model_metrics", {})
            self.ab_test_config = data.get("ab_test_config", {})

    def _save(self) -> None:
        payload = {
            "models": self.models,
            "active_models": self.active_models,
            "model_metrics": self.model_metrics,
            "ab_test_config": self.ab_test_config,
            "last_updated": _now(),
        }
        tmp = self.registry_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self.registry_path)

    def flush(self) -> None:
        with self._lock:
            self._save()

    def _relative(self, path: Any) -> str:
        p = Path(path)
        try:
            return str(p.resolve().relative_to(self.model_dir.resolve()))
        except ValueError:
            return str(p)

    def next_version(self, model_type: str) -> str:
        with self._lock:
            existing = [
                int(v) for v in self.models.get(model_type, {}) if str(v).isdigit()
            ]
            return str(max(existing, default=0) + 1)

    def register_model(
        self,
        model_type: str,
        model_path: Any,
        version: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        version = str(version)
        model_id = f"{model_type}_v{version}"
        with self._lock:
            self.models.setdefault(model_type, {})[version] = {
                "model_id": model_id,
                "model_path": self._relative(model_path),
                "registered_at": _now(),
                "metadata": metadata or {},
            }
            self.model_metrics.setdefault(model_id, _empty_metrics())
            self._save()
        return model_id

    def activate_model(self, model_type: str, version: Any) -> None:
        version = str(version)
        with self._lock:
            if version not in self.models.get(model_type, {}):
                raise ValueError(f"Model {model_type} version {version} not found")
            self.active_models[model_type] = version
            self._save()

    def get_active_version(self, model_type: str) -> Optional[str]:
        with self._lock:
            return self.active_models.get(model_type)

    def get_model_path(self, model_type: str, version: Any) -> Path:
        with self._lock:
            entry = self.models.get(model_type, {}).get(str(version))
            if entry is None:
                raise ValueError(f"Model {model_type} version {version} not found")
            path = Path(entry["model_path"])
        return path if path.is_absolute() else self.model_dir / path

    def get_active_model_path(self, model_type: str) -> Path:
        version = self.get_active_version(model_type)
        if version is None:
            raise ValueError(f"No active model for type {model_type}")
        return self.get_model_path(model_type, version)

    def configure_ab_test(
        self, model_type: str, versions: List[Any], traffic_split: List[float]
    ) -> None:
        if len(versions) != len(traffic_split):
            raise ValueError("versions and traffic_split must have equal length")
        if abs(sum(traffic_split) - 100) > 1e-6:
            raise ValueError("Traffic split must sum to 100")
        with self._lock:
            for version in versions:
                if str(version) not in self.models.get(model_type, {}):
                    raise ValueError(f"Model {model_type} version {version} not found")
            self.ab_test_config[model_type] = {
                "versions": [str(v) for v in versions],
                "traffic_split": list(traffic_split),
                "started_at": _now(),
                "active": True,
            }
            self._save()

    def select_model_for_request(
        self, model_type: str, request_id: Optional[str] = None
    ) -> Optional[str]:
        with self._lock:
            config = self.ab_test_config.get(model_type)
            if not config or not config.get("active"):
                return self.active_models.get(model_type)
            versions = config["versions"]
            splits = config["traffic_split"]
        if request_id:
            digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
            bucket = int(digest, 16) % 100
        else:
            bucket = random.random() * 100
        cumulative = 0.0
        for version, share in zip(versions, splits):
            cumulative += share
            if bucket < cumulative:
                return version
        return versions[-1]

    def record_inference(
        self, model_id: str, inference_time: float, error: bool = False
    ) -> None:
        with self._lock:
            metrics = self.model_metrics.setdefault(model_id, _empty_metrics())
            count = metrics["inference_count"]
            metrics["avg_inference_time"] = (
                metrics["avg_inference_time"] * count + inference_time
            ) / (count + 1)
            metrics["inference_count"] = count + 1
            if error:
                metrics["error_count"] += 1

    def update_performance_metrics(
        self, model_id: str, metrics: Dict[str, Any]
    ) -> None:
        with self._lock:
            entry = self.model_metrics.setdefault(model_id, _empty_metrics())
            entry.setdefault("performance_metrics", {}).update(metrics)
            self._save()

    def get_model_metrics(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if model_id:
                return dict(self.model_metrics.get(model_id, {}))
            return dict(self.model_metrics)

    def generate_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "generated_at": _now(),
                "models": self.models,
                "active_models": self.active_models,
                "metrics": self.model_metrics,
                "ab_tests": self.ab_test_config,
            }
