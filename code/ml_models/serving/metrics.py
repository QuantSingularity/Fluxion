from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler
from typing import Any, Dict, Tuple

from ml_models.serving.service import ModelService


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: Dict[Tuple[str, str, int], int] = {}
        self._latency_sum: Dict[str, float] = {}
        self._latency_count: Dict[str, int] = {}

    def observe(self, method: str, path: str, status: int, seconds: float) -> None:
        with self._lock:
            key = (method, path, status)
            self._requests[key] = self._requests.get(key, 0) + 1
            self._latency_sum[path] = self._latency_sum.get(path, 0.0) + seconds
            self._latency_count[path] = self._latency_count.get(path, 0) + 1

    def render(self, service: ModelService) -> str:
        lines = [
            "# TYPE ml_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status), count in sorted(self._requests.items()):
                lines.append(
                    f'ml_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )
            lines.append("# TYPE ml_http_request_seconds_sum counter")
            for path, total in sorted(self._latency_sum.items()):
                lines.append(
                    f'ml_http_request_seconds_sum{{path="{path}"}} {total:.6f}'
                )
            lines.append("# TYPE ml_http_request_seconds_count counter")
            for path, count in sorted(self._latency_count.items()):
                lines.append(f'ml_http_request_seconds_count{{path="{path}"}} {count}')
        lines.append("# TYPE ml_models_ready gauge")
        lines.append(f"ml_models_ready {1 if service.ready() else 0}")
        lines.append("# TYPE ml_model_inferences_total counter")
        lines.append("# TYPE ml_model_errors_total counter")
        for model_id, m in sorted(service.manager.get_model_metrics().items()):
            lines.append(
                f'ml_model_inferences_total{{model="{model_id}"}} {m.get("inference_count", 0)}'
            )
            lines.append(
                f'ml_model_errors_total{{model="{model_id}"}} {m.get("error_count", 0)}'
            )
        return "\n".join(lines) + "\n"


def make_metrics_handler(app: Any):
    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.split("?", 1)[0] != "/metrics":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = app.metrics.render(app.service).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return MetricsHandler
