import json
import threading
import urllib.error
import urllib.request

import pytest
from ml_models.config import ServiceSettings
from ml_models.data.synthetic import market_records, transaction_records
from ml_models.serving.server import create_servers


class TestHttpServer:
    @pytest.fixture(scope="class")
    def server(self, trained_service):
        settings = ServiceSettings(
            trained_service.model_dir, 18741, 18742, "warning", "key123", False, "quick"
        )
        api, metrics, app = create_servers(settings, trained_service, "127.0.0.1")
        for srv in (api, metrics):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield "http://127.0.0.1:18741", "http://127.0.0.1:18742"
        api.shutdown()
        metrics.shutdown()
        api.server_close()
        metrics.server_close()

    def _call(self, base, method, path, body=None, key="key123"):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        req = urllib.request.Request(
            base + path,
            data=None if body is None else json.dumps(body).encode(),
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_health_and_ready_open(self, server):
        assert self._call(server[0], "GET", "/health", key=None)[0] == 200
        assert self._call(server[0], "GET", "/ready", key=None)[0] == 200

    def test_auth_required(self, server):
        assert (
            self._call(
                server[0], "POST", "/v1/risk/assess", {"records": [1]}, key=None
            )[0]
            == 401
        )
        assert (
            self._call(
                server[0], "POST", "/v1/risk/assess", {"records": [1]}, key="bad"
            )[0]
            == 401
        )

    def test_validation_errors(self, server):
        assert self._call(server[0], "POST", "/v1/risk/assess", {})[0] == 422
        status, body = self._call(
            server[0],
            "POST",
            "/v1/liquidity/forecast",
            {"records": market_records(300, 1), "horizon": 50},
        )
        assert status == 422 and "horizon" in body["error"]
        assert (
            self._call(
                server[0], "POST", "/v1/risk/assess", {"records": market_records(10, 1)}
            )[0]
            == 422
        )
        assert self._call(server[0], "GET", "/nope")[0] == 404

    def test_forecast_and_screen(self, server):
        status, body = self._call(
            server[0],
            "POST",
            "/v1/liquidity/forecast",
            {"records": market_records(300, 1), "horizon": 2},
        )
        assert status == 200 and len(body["result"]["predicted_liquidity"]) == 2
        txs, _ = transaction_records(3, 2)
        status, body = self._call(
            server[0], "POST", "/v1/transactions/screen", {"transactions": txs}
        )
        assert status == 200 and len(body["result"]) == 3

    def test_metrics_endpoint(self, server):
        with urllib.request.urlopen(server[1] + "/metrics") as r:
            text = r.read().decode()
        assert "ml_http_requests_total" in text
        assert "ml_models_ready 1" in text

    def test_train_rejects_bad_profile(self, server):
        assert (
            self._call(server[0], "POST", "/v1/models/train", {"profile": "x"})[0]
            == 422
        )
