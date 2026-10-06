import asyncio
import threading
import time
from uuid import uuid4

import pytest
from app.main import app
from config.settings import settings
from fastapi.testclient import TestClient
from ml_models.config import ServiceSettings
from ml_models.data.synthetic import (
    market_records,
    supply_chain_frame,
    transaction_records,
)
from ml_models.serving.server import create_servers
from services.auth.jwt_service import JWTService
from services.ml import reset_ml_gateway


@pytest.fixture(scope="module")
def client(ml_models_ready):
    return TestClient(app)


def _headers(roles=None):
    token = JWTService().create_access_token(
        {"user_id": str(uuid4()), "email": "ml@example.com", "roles": roles or ["user"]}
    )
    return {"Authorization": f"Bearer {token}"}


class TestMarketRoutes:
    def test_risk_overview_public(self, client):
        res = client.get("/api/v1/ml/risk/overview")
        assert res.status_code == 200
        data = res.json()["data"]
        assert 0 <= data["overall_risk"] <= 1
        assert data["risk_level"] in {"low", "medium", "high", "critical"}
        assert len(data["items"]) == 5
        assert data["data_source"] == "simulated_market_snapshot"

    def test_pool_risk_and_unknown_pool(self, client):
        ok = client.get("/api/v1/ml/pools/pool-syneth-synusd/risk")
        assert ok.status_code == 200
        assert ok.json()["data"]["entity_id"] == "pool-syneth-synusd"
        assert client.get("/api/v1/ml/pools/nope/risk").status_code == 422

    def test_asset_risk_by_symbol(self, client):
        res = client.get("/api/v1/ml/assets/synBTC/risk")
        assert res.status_code == 200
        assert res.json()["data"]["entity_id"] == "syn-btc"

    def test_pool_forecast(self, client):
        res = client.get("/api/v1/ml/pools/pool-synbtc-synusd/forecast?horizon=4")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data["predicted_liquidity"]) == 4
        assert all(
            lo < p < hi
            for lo, p, hi in zip(
                data["lower_bound"], data["predicted_liquidity"], data["upper_bound"]
            )
        )

    def test_forecast_horizon_validation(self, client):
        assert (
            client.get(
                "/api/v1/ml/pools/pool-synbtc-synusd/forecast?horizon=0"
            ).status_code
            == 422
        )
        assert (
            client.get(
                "/api/v1/ml/pools/pool-synbtc-synusd/forecast?horizon=7"
            ).status_code
            == 422
        )

    def test_repeat_calls_are_stable(self, client):
        a = client.get("/api/v1/ml/pools/pool-syneth-synbtc/forecast?horizon=2").json()
        b = client.get("/api/v1/ml/pools/pool-syneth-synbtc/forecast?horizon=2").json()
        assert a["data"]["predicted_liquidity"] == b["data"]["predicted_liquidity"]


class TestAuthenticatedRoutes:
    def test_status_requires_auth(self, client):
        assert client.get("/api/v1/ml/status").status_code == 401
        res = client.get("/api/v1/ml/status", headers=_headers())
        assert res.status_code == 200
        assert res.json()["data"]["ready"] is True

    def test_custom_forecast_with_supplied_history(self, client):
        res = client.post(
            "/api/v1/ml/pools/custom/forecast",
            json={"horizon": 2, "records": market_records(300, 21)},
            headers=_headers(),
        )
        assert res.status_code == 200
        assert res.json()["data"]["data_source"] == "supplied"

    def test_custom_forecast_rejects_short_history(self, client):
        res = client.post(
            "/api/v1/ml/pools/custom/forecast",
            json={"horizon": 2, "records": market_records(40, 21)},
            headers=_headers(),
        )
        assert res.status_code == 422

    def test_custom_risk_requires_records(self, client):
        assert (
            client.post(
                "/api/v1/ml/risk/assess", json={}, headers=_headers()
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/ml/risk/assess", json={"records": market_records(120, 3)}
            ).status_code
            == 401
        )
        res = client.post(
            "/api/v1/ml/risk/assess",
            json={"records": market_records(120, 3)},
            headers=_headers(),
        )
        assert res.status_code == 200

    def test_supply_chain_forecast(self, client):
        res = client.post(
            "/api/v1/ml/supply-chain/forecast",
            json={
                "horizon": 3,
                "records": supply_chain_frame(60, 1).to_dict("records"),
            },
            headers=_headers(),
        )
        assert res.status_code == 200
        assert len(res.json()["data"]["predictions"]) == 3

    def test_screen_transactions(self, client):
        txs, _ = transaction_records(3, 4)
        res = client.post(
            "/api/v1/ml/transactions/screen",
            json={"transactions": txs},
            headers=_headers(),
        )
        assert res.status_code == 200
        assert len(res.json()["data"]["result"]) == 3
        bad = client.post(
            "/api/v1/ml/transactions/screen",
            json={"transactions": [{"amount": -1}]},
            headers=_headers(),
        )
        assert bad.status_code == 422

    def test_train_requires_admin(self, client):
        body = {"models": ["compliance"], "profile": "quick"}
        assert client.post("/api/v1/ml/models/train", json=body).status_code == 401
        assert (
            client.post(
                "/api/v1/ml/models/train", json=body, headers=_headers()
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/ml/models/train",
                json={"profile": "weird"},
                headers=_headers(["admin"]),
            ).status_code
            == 422
        )

    def test_admin_train_runs_and_bumps_version(self, client):
        admin = _headers(["admin"])
        before = client.get("/api/v1/ml/status", headers=admin).json()["data"]
        v_before = before["models"]["compliance"]["active_version"]
        res = client.post(
            "/api/v1/ml/models/train",
            json={"models": ["compliance"], "profile": "quick"},
            headers=admin,
        )
        assert res.status_code == 202
        deadline = time.time() + 60
        while time.time() < deadline:
            state = client.get("/api/v1/ml/status", headers=admin).json()["data"]
            if not state["training"]["running"]:
                break
            time.sleep(0.5)
        after = client.get("/api/v1/ml/status", headers=admin).json()["data"]
        assert int(after["models"]["compliance"]["active_version"]) > int(v_before)


class TestIntegratedFlows:
    def test_risk_endpoints_use_ml(self, client):
        res = client.get(f"/api/v1/risk/assessment/{uuid4()}")
        assert res.status_code == 200
        body = res.json()
        assert 0 <= body["overall_risk_score"] <= 1
        assert "risk_factors" in body
        alerts = client.get("/api/v1/risk/alerts")
        assert alerts.status_code == 200 and isinstance(alerts.json(), list)
        report = client.post("/api/v1/risk/report", json={})
        assert report.status_code == 200
        assert report.json()["recommendations"]

    def test_analytics_risk_includes_ml(self, client):
        res = client.get("/api/v1/analytics/risk", headers=_headers())
        data = res.json()["data"]
        assert data["ml_available"] is True
        assert "factors" in data["risk_metrics"]

    def test_transaction_creation_is_screened(self, client):
        res = client.post(
            "/api/v1/transactions/",
            json={"transaction_type": "transfer", "amount": 120.0},
            headers=_headers(),
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["screening"]["available"] is True
        assert data["status"] in {"pending", "pending_review"}

    def test_suspicious_transaction_flagged_for_review(self, client):
        res = client.post(
            "/api/v1/transactions/",
            json={
                "transaction_type": "transfer",
                "amount": 95000.0,
                "metadata": {
                    "avg_amount_30d": 150,
                    "tx_count_24h": 25,
                    "account_age_days": 1,
                    "kyc_score": 0.1,
                    "country_risk": 0.95,
                    "cross_border": 1,
                },
            },
            headers=_headers(),
        )
        data = res.json()["data"]
        assert data["status"] == "pending_review"
        assert data["screening"]["flags"]

    def test_detailed_health_reports_ml(self, client):
        res = client.get("/api/v1/health/detailed")
        assert res.json()["dependencies"]["ml"]["status"] == "healthy"


class TestUnavailableAndRemote:
    def test_disabled_mode_returns_503(self):
        previous = settings.ml.ML_MODE
        settings.ml.ML_MODE = "disabled"
        asyncio.run(reset_ml_gateway())
        try:
            c = TestClient(app)
            assert c.get("/api/v1/ml/risk/overview").status_code == 503
            assert c.get(f"/api/v1/risk/assessment/{uuid4()}").status_code == 503
            tx = c.post(
                "/api/v1/transactions/",
                json={"transaction_type": "transfer", "amount": 10.0},
                headers=_headers(),
            )
            assert tx.status_code == 200
            assert tx.json()["data"]["screening"]["available"] is False
            assert tx.json()["data"]["status"] == "pending"
        finally:
            settings.ml.ML_MODE = previous
            asyncio.run(reset_ml_gateway())

    def test_remote_mode_against_live_ml_service(self, ml_models_ready, tmp_path):
        from ml_models.serving.service import ModelService

        service = ModelService(tmp_path)
        service.bootstrap("quick")
        ml_settings = ServiceSettings(
            tmp_path, 18751, 18752, "warning", "k3y", False, "quick"
        )
        api, metrics, _ = create_servers(ml_settings, service, "127.0.0.1")
        for srv in (api, metrics):
            threading.Thread(target=srv.serve_forever, daemon=True).start()

        saved = (
            settings.ml.ML_MODE,
            settings.ml.ML_SERVICE_URL,
            settings.ml.ML_SERVICE_API_KEY,
        )
        settings.ml.ML_MODE = "remote"
        settings.ml.ML_SERVICE_URL = "http://127.0.0.1:18751"
        settings.ml.ML_SERVICE_API_KEY = "k3y"
        asyncio.run(reset_ml_gateway())
        try:
            c = TestClient(app)
            ok = c.get("/api/v1/ml/pools/pool-synbtc-synusd/forecast?horizon=2")
            assert ok.status_code == 200
            assert ok.json()["data"]["model_version"].startswith("liquidity_v")
            assert c.get("/api/v1/ml/risk/overview").status_code == 200
            bad = c.post(
                "/api/v1/ml/pools/custom/forecast",
                json={"horizon": 2, "records": market_records(40, 1)},
                headers=_headers(),
            )
            assert bad.status_code == 422

            settings.ml.ML_SERVICE_API_KEY = "wrong"
            asyncio.run(reset_ml_gateway())
            denied = TestClient(app).get("/api/v1/ml/pools/pool-synbtc-synusd/forecast")
            assert denied.status_code == 503

            api.shutdown()
            api.server_close()
            settings.ml.ML_SERVICE_API_KEY = "k3y"
            asyncio.run(reset_ml_gateway())
            down = TestClient(app).get("/api/v1/ml/risk/overview")
            assert down.status_code == 503
        finally:
            (
                settings.ml.ML_MODE,
                settings.ml.ML_SERVICE_URL,
                settings.ml.ML_SERVICE_API_KEY,
            ) = saved
            metrics.shutdown()
            metrics.server_close()
            asyncio.run(reset_ml_gateway())
