import asyncio
import importlib
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from config.settings import settings
from services.market.market_data import (
    POOLS,
    SYNTHETICS,
    find_pool,
    find_synthetic,
    pool_history,
    synthetic_history,
)

logger = logging.getLogger(__name__)

DATA_SOURCE = "simulated_market_snapshot"

REMOTE_PATHS = {
    "liquidity": "/v1/liquidity/forecast",
    "supply_chain": "/v1/supply-chain/forecast",
    "risk": "/v1/risk/assess",
    "anomalies": "/v1/anomalies/detect",
    "compliance": "/v1/compliance/check",
    "screen": "/v1/transactions/screen",
}


class MLError(Exception):
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MLInputError(MLError):
    status_code = 422


class MLUnavailable(MLError):
    status_code = 503


class _LocalBackend:
    name = "local"

    def __init__(self) -> None:
        self.service: Any = None
        self.errors: Tuple[type, ...] = ()
        self.not_ready: Optional[type] = None

    @staticmethod
    def importable() -> bool:
        try:
            _ensure_path()
            importlib.import_module("ml_models.serving.service")
            return True
        except Exception:
            return False

    async def start(self) -> None:
        def build() -> None:
            _ensure_path()
            service_mod = importlib.import_module("ml_models.serving.service")
            features_mod = importlib.import_module("ml_models.data.features")
            self.errors = (features_mod.InputError,)
            self.not_ready = service_mod.ModelNotReady
            self.service = service_mod.ModelService(Path(settings.ml.ML_MODEL_PATH))

        await asyncio.to_thread(build)
        if settings.ml.ML_AUTO_BOOTSTRAP and not self.service.ready():
            threading.Thread(
                target=self._bootstrap, name="ml-bootstrap", daemon=True
            ).start()

    def _bootstrap(self) -> None:
        try:
            self.service.bootstrap(settings.ml.ML_BOOTSTRAP_PROFILE)
        except Exception:
            logger.exception("ML model bootstrap failed")

    async def stop(self) -> None:
        if self.service is not None:
            await asyncio.to_thread(self.service.shutdown)

    def _dispatch(self, op: str, payload: Dict[str, Any], rid: Optional[str]) -> Any:
        svc = self.service
        if svc is None:
            raise MLUnavailable("ML service is not initialised")
        try:
            if op == "liquidity":
                return svc.forecast_liquidity(
                    payload["records"], payload["horizon"], rid
                )
            if op == "supply_chain":
                return svc.forecast_supply_chain(
                    payload["records"], payload["horizon"], rid
                )
            if op == "risk":
                return svc.assess_risk(payload["records"], rid)
            if op == "anomalies":
                return svc.detect_anomalies(payload["transactions"], rid)
            if op == "compliance":
                return svc.check_compliance(payload["transactions"], rid)
            if op == "screen":
                return svc.screen_transactions(payload["transactions"], rid)
        except self.errors as exc:
            raise MLInputError(str(exc)) from exc
        except self.not_ready as exc:
            raise MLUnavailable(str(exc)) from exc
        except ValueError as exc:
            raise MLInputError(str(exc)) from exc
        raise MLError(f"Unknown operation {op}")

    async def call(self, op: str, payload: Dict[str, Any], rid: Optional[str]) -> Any:
        return await asyncio.to_thread(self._dispatch, op, payload, rid)

    async def status(self) -> Dict[str, Any]:
        if self.service is None:
            return {"mode": self.name, "ready": False, "error": "not initialised"}
        data = await asyncio.to_thread(self.service.status)
        data["mode"] = self.name
        return data

    async def train(self, models: Optional[List[str]], profile: str) -> Dict[str, Any]:
        if self.service is None:
            raise MLUnavailable("ML service is not initialised")
        if self.service.training_state()["running"]:
            raise MLError("Training already in progress")

        def job() -> None:
            try:
                self.service.train(models, profile)
            except Exception:
                logger.exception("ML training failed")

        threading.Thread(target=job, name="ml-train", daemon=True).start()
        return {"status": "started", "models": models, "profile": profile}


class _RemoteBackend:
    name = "remote"

    def __init__(self) -> None:
        self.client: Optional[httpx.AsyncClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _build_client(self) -> httpx.AsyncClient:
        headers = {}
        if settings.ml.ML_SERVICE_API_KEY:
            headers["X-API-Key"] = settings.ml.ML_SERVICE_API_KEY
        return httpx.AsyncClient(
            base_url=(settings.ml.ML_SERVICE_URL or "").rstrip("/"),
            timeout=settings.ml.ML_REQUEST_TIMEOUT,
            headers=headers,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        if self.client is None or self._loop is not loop:
            self.client = self._build_client()
            self._loop = loop
        return self.client

    async def start(self) -> None:
        await self._get_client()

    async def stop(self) -> None:
        client, self.client = self.client, None
        if client is not None and self._loop is asyncio.get_running_loop():
            await client.aclose()

    async def _request(
        self, method: str, path: str, body: Optional[Dict[str, Any]], rid: Optional[str]
    ) -> Any:
        client = await self._get_client()
        headers = {"X-Request-ID": rid} if rid else None
        try:
            response = await client.request(method, path, json=body, headers=headers)
        except (httpx.HTTPError, OSError) as exc:
            raise MLUnavailable(
                f"ML service unreachable: {type(exc).__name__}"
            ) from exc
        if response.status_code in (200, 202):
            return response.json()
        try:
            detail = response.json().get("error", response.text)
        except ValueError:
            detail = response.text
        if response.status_code in (400, 422):
            raise MLInputError(str(detail))
        if response.status_code == 409:
            raise MLError(str(detail))
        raise MLUnavailable(f"ML service error {response.status_code}: {detail}")

    async def call(self, op: str, payload: Dict[str, Any], rid: Optional[str]) -> Any:
        return await self._request("POST", REMOTE_PATHS[op], payload, rid)

    async def status(self) -> Dict[str, Any]:
        try:
            data = await self._request("GET", "/v1/models", None, None)
        except MLError as exc:
            return {"mode": self.name, "ready": False, "error": exc.message}
        data["mode"] = self.name
        return data

    async def train(self, models: Optional[List[str]], profile: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {"profile": profile}
        if models:
            body["models"] = models
        return await self._request("POST", "/v1/models/train", body, None)


class _DisabledBackend:
    name = "disabled"

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def call(self, op: str, payload: Dict[str, Any], rid: Optional[str]) -> Any:
        raise MLUnavailable("ML integration is disabled")

    async def status(self) -> Dict[str, Any]:
        return {"mode": self.name, "ready": False}

    async def train(self, models: Optional[List[str]], profile: str) -> Dict[str, Any]:
        raise MLUnavailable("ML integration is disabled")


def _ensure_path() -> None:
    root = Path(__file__).resolve().parents[3]
    if (root / "ml_models").is_dir() and str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _select_backend() -> Any:
    mode = settings.ml.ML_MODE
    url = settings.ml.ML_SERVICE_URL
    if mode == "disabled":
        return _DisabledBackend()
    if mode == "remote":
        if not url:
            raise RuntimeError("ML_MODE=remote requires ML_SERVICE_URL")
        return _RemoteBackend()
    if mode == "local":
        if not _LocalBackend.importable():
            raise RuntimeError("ML_MODE=local but ml_models could not be imported")
        return _LocalBackend()
    if url:
        return _RemoteBackend()
    if _LocalBackend.importable():
        return _LocalBackend()
    logger.warning(
        "ML integration disabled: no ML_SERVICE_URL and ml_models not importable"
    )
    return _DisabledBackend()


def _level(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.66:
        return "high"
    if score >= 0.33:
        return "medium"
    return "low"


class MLGateway:
    def __init__(self) -> None:
        self._backend: Any = None
        self._cache: Dict[Any, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    @property
    def mode(self) -> str:
        return self._backend.name if self._backend else "uninitialised"

    async def startup(self) -> None:
        async with self._lock:
            if self._backend is not None:
                return
            backend = _select_backend()
            await backend.start()
            self._backend = backend
            logger.info("ML gateway started in %s mode", backend.name)

    async def shutdown(self) -> None:
        async with self._lock:
            if self._backend is not None:
                await self._backend.stop()
                self._backend = None
            self._cache.clear()

    async def _ensure(self) -> Any:
        if self._backend is None:
            await self.startup()
        return self._backend

    def _cached(self, key: Any) -> Any:
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < settings.ml.ML_CACHE_TTL:
            return hit[1]
        return None

    def _store(self, key: Any, value: Any) -> Any:
        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[key] = (time.monotonic(), value)
        return value

    async def call(
        self, op: str, payload: Dict[str, Any], rid: Optional[str] = None
    ) -> Any:
        backend = await self._ensure()
        return await backend.call(op, payload, rid)

    async def status(self) -> Dict[str, Any]:
        backend = await self._ensure()
        return await backend.status()

    async def is_ready(self) -> bool:
        try:
            return bool((await self.status()).get("ready"))
        except MLError:
            return False

    async def train(self, models: Optional[List[str]], profile: str) -> Dict[str, Any]:
        backend = await self._ensure()
        self._cache.clear()
        return await backend.train(models, profile)

    def _history(
        self, entity_type: str, entity: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        points = settings.ml.ML_HISTORY_POINTS
        if entity_type == "pool":
            return pool_history(entity, points)
        return synthetic_history(entity, points)

    async def liquidity_forecast(
        self,
        pool_id: str,
        horizon: int,
        records: Optional[List[Dict[str, Any]]] = None,
        rid: Optional[str] = None,
    ) -> Dict[str, Any]:
        pool = find_pool(pool_id)
        if records is None and pool is None:
            raise MLInputError(f"Unknown pool '{pool_id}'")
        key = ("liquidity", pool_id, horizon)
        if records is None:
            cached = self._cached(key)
            if cached is not None:
                return cached
        data = records if records is not None else self._history("pool", pool)
        out = await self.call("liquidity", {"records": data, "horizon": horizon}, rid)
        result = {
            "pool_id": pool_id,
            "pool_name": pool["name"] if pool else None,
            "data_source": "supplied" if records is not None else DATA_SOURCE,
            "model_version": out["model_version"],
            **out["result"],
        }
        return result if records is not None else self._store(key, result)

    async def supply_chain_forecast(
        self, records: List[Dict[str, Any]], horizon: int, rid: Optional[str] = None
    ) -> Dict[str, Any]:
        out = await self.call(
            "supply_chain", {"records": records, "horizon": horizon}, rid
        )
        return {"model_version": out["model_version"], **out["result"]}

    async def entity_risk(
        self,
        entity_type: str,
        entity_id: str,
        records: Optional[List[Dict[str, Any]]] = None,
        rid: Optional[str] = None,
    ) -> Dict[str, Any]:
        entity = (
            find_pool(entity_id) if entity_type == "pool" else find_synthetic(entity_id)
        )
        if records is None and entity is None:
            raise MLInputError(f"Unknown {entity_type} '{entity_id}'")
        key = ("risk", entity_type, entity_id)
        if records is None:
            cached = self._cached(key)
            if cached is not None:
                return cached
        data = records if records is not None else self._history(entity_type, entity)
        out = await self.call("risk", {"records": data}, rid)
        result = {
            "entity_type": entity_type,
            "entity_id": entity["id"] if entity else entity_id,
            "name": entity["name"] if entity else None,
            "data_source": "supplied" if records is not None else DATA_SOURCE,
            "model_version": out["model_version"],
            **out["result"],
        }
        return result if records is not None else self._store(key, result)

    async def risk_overview(self, rid: Optional[str] = None) -> Dict[str, Any]:
        key = ("overview",)
        cached = self._cached(key)
        if cached is not None:
            return cached
        tasks = [self.entity_risk("pool", p["id"], rid=rid) for p in POOLS]
        tasks += [self.entity_risk("synthetic", s["id"], rid=rid) for s in SYNTHETICS]
        items = await asyncio.gather(*tasks)
        weights = [float(p["tvl"]) for p in POOLS] + [
            float(s["tvl"]) for s in SYNTHETICS
        ]
        total = sum(weights) or 1.0
        overall = sum(i["overall_risk"] * w for i, w in zip(items, weights)) / total
        factor_names = list(items[0]["factors"].keys())
        factors = {
            n: sum(i["factors"][n] * w for i, w in zip(items, weights)) / total
            for n in factor_names
        }
        result = {
            "overall_risk": overall,
            "risk_level": _level(overall),
            "factors": factors,
            "factor_levels": {n: _level(v) for n, v in factors.items()},
            "items": items,
            "data_source": DATA_SOURCE,
        }
        return self._store(key, result)

    async def screen_transactions(
        self, transactions: List[Dict[str, Any]], rid: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.call("screen", {"transactions": transactions}, rid)


_gateway: Optional[MLGateway] = None


def get_ml_gateway() -> MLGateway:
    global _gateway
    if _gateway is None:
        _gateway = MLGateway()
    return _gateway


async def reset_ml_gateway() -> None:
    global _gateway
    if _gateway is not None:
        await _gateway.shutdown()
    _gateway = None
