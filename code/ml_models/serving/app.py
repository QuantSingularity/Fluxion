from __future__ import annotations

import hmac
import logging
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from ml_models.config import (
    LIQUIDITY_HORIZON,
    MODEL_TYPES,
    PROFILES,
    SUPPLY_CHAIN_HORIZON,
    ServiceSettings,
)
from ml_models.serving.metrics import Metrics
from ml_models.serving.service import ModelService

logger = logging.getLogger("ml-service")

MAX_BODY_BYTES = 8 * 1024 * 1024


class HttpError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _require_list(body: Dict[str, Any], key: str) -> list:
    value = body.get(key)
    if not isinstance(value, list) or not value:
        raise HttpError(422, f"'{key}' must be a non-empty list")
    return value


def _horizon(body: Dict[str, Any], maximum: int) -> int:
    raw = body.get("horizon", 1)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise HttpError(422, "'horizon' must be an integer")
    if raw < 1 or raw > maximum:
        raise HttpError(422, f"'horizon' must be between 1 and {maximum}")
    return raw


class Application:
    def __init__(self, settings: ServiceSettings, service: ModelService) -> None:
        self.settings = settings
        self.service = service
        self.metrics = Metrics()
        self.routes: Dict[
            Tuple[str, str], Callable[[Dict[str, Any], Optional[str]], Tuple[int, Any]]
        ] = {
            ("POST", "/v1/liquidity/forecast"): self._liquidity,
            ("POST", "/v1/supply-chain/forecast"): self._supply_chain,
            ("POST", "/v1/risk/assess"): self._risk,
            ("POST", "/v1/anomalies/detect"): self._anomalies,
            ("POST", "/v1/compliance/check"): self._compliance,
            ("POST", "/v1/transactions/screen"): self._screen,
            ("POST", "/v1/models/train"): self._train,
            ("GET", "/v1/models"): self._models,
        }
        self.open_paths = {("GET", "/health"), ("GET", "/ready"), ("GET", "/")}

    def authorized(self, method: str, path: str, header: Optional[str]) -> bool:
        if (method, path) in self.open_paths or not self.settings.api_key:
            return True
        if not header:
            return False
        return hmac.compare_digest(
            header.encode("utf-8"), self.settings.api_key.encode("utf-8")
        )

    def _liquidity(self, body, rid):
        out = self.service.forecast_liquidity(
            _require_list(body, "records"), _horizon(body, LIQUIDITY_HORIZON), rid
        )
        return 200, out

    def _supply_chain(self, body, rid):
        out = self.service.forecast_supply_chain(
            _require_list(body, "records"), _horizon(body, SUPPLY_CHAIN_HORIZON), rid
        )
        return 200, out

    def _risk(self, body, rid):
        return 200, self.service.assess_risk(_require_list(body, "records"), rid)

    def _anomalies(self, body, rid):
        return 200, self.service.detect_anomalies(
            _require_list(body, "transactions"), rid
        )

    def _compliance(self, body, rid):
        return 200, self.service.check_compliance(
            _require_list(body, "transactions"), rid
        )

    def _screen(self, body, rid):
        return 200, self.service.screen_transactions(
            _require_list(body, "transactions"), rid
        )

    def _models(self, body, rid):
        return 200, self.service.status()

    def _train(self, body, rid):
        profile = body.get("profile", "full")
        models = body.get("models") or list(MODEL_TYPES)
        if profile not in PROFILES:
            raise HttpError(422, f"'profile' must be one of {sorted(PROFILES)}")
        if not isinstance(models, list) or any(m not in MODEL_TYPES for m in models):
            raise HttpError(422, f"'models' must be a subset of {list(MODEL_TYPES)}")
        if self.service.training_state()["running"]:
            raise HttpError(409, "Training already in progress")

        def job() -> None:
            try:
                self.service.train(models, profile)
            except Exception:
                logger.exception("Background training failed")

        threading.Thread(target=job, name="ml-train", daemon=True).start()
        return 202, {"status": "started", "models": models, "profile": profile}

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy", "service": "fluxion-ml"}

    def readiness(self) -> Tuple[int, Dict[str, Any]]:
        ready = self.service.ready()
        payload = {
            "ready": ready,
            "missing": self.service.missing(),
            "training": self.service.training_state()["running"],
        }
        return (200 if ready else 503), payload
